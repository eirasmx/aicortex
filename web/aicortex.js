/**
 * aicortex.js  v0.0.2
 * JavaScript SDK for AI Cortex — free LLMs in the browser and Node.js.
 *
 * Zero API keys. Zero signup. Zero server setup. Completely free.
 * Models are served by the open-source community via Ollama.
 *
 * What's new in v0.0.1 (initial release):
 *  - Smart server routing: "fastest" | "nearest" | "balanced" | "random"
 *  - Best-server cache with configurable TTL (default 5 min)
 *  - Exponential backoff on retries (configurable base + jitter)
 *  - Pre-flight internet connectivity check (fast-fail)
 *  - TTL-based failed-server blacklist (skips downed servers automatically)
 *  - Full server metadata: url, tps, city, country, continent, org
 *  - search() — substring + family + param-size filters
 *  - JSON mode — response_format:"json" returns a parsed object
 *  - Async/await everywhere; stream() returns an async-iterable StreamReader
 *  - session() for multi-turn history (aligned with Python Session class)
 *  - registryInfo(), refreshRegistry(), bestServer(), llmParams() preserved
 *
 * Registry resolution order (first live source wins):
 *   1. Local folder  — Node.js only: ./models/<family>.json (or AICORTEX_MODELS_DIR)
 *   2. GitHub raw    — https://raw.githubusercontent.com/eirasmx/aicortex/master/...
 *
 * @example  ES module / npm
 *   import AICortex from 'aicortex-core';
 *   const ai = new AICortex();
 *   const reply = await ai.chat('Explain neural networks like I am five.');
 *   console.log(reply);
 *
 * @example  CDN — no install needed
 *   <script src="https://unpkg.com/aicortex/aicortex.js"></script>
 *   <script>
 *     const ai = new AICortex();
 *     ai.chat('Hello!').then(console.log);
 *   </script>
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.AICortex = factory();
  }
}(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this, function () {
  'use strict';

  // ─── Environment detection ────────────────────────────────────────────────────

  const _isNode = typeof process !== 'undefined' &&
                  process.versions != null &&
                  process.versions.node != null;

  // ─── Remote registry sources ──────────────────────────────────────────────────

  const _REMOTE_SOURCES = [
    fam => `https://raw.githubusercontent.com/eirasmx/aicortex/master/aicortex/models/${fam}.json`,
    fam => `https://unpkg.com/aicortex-core/models/${fam}.json`,
  ];

  const _FAMILY_INDEX_SOURCES = [
    () => 'https://raw.githubusercontent.com/eirasmx/aicortex/master/web/index.json',
  ];

  // ─── In-memory registry cache ─────────────────────────────────────────────────


  let _registry     = null;   // null until first fetch completes
  let _registryLive = false;  // true only after a successful network fetch
  let _registrySources = {};  // fam → 'local' | 'remote' | 'missing'
  let _registryReady = null;
  let _registryFetchedAt = 0;
  let _registryTTL = 60 * 60 * 1000; // 1 hour

  // ─── Persistent cache (localStorage / Node fs) ───────────────────────────────

  const _CACHE_KEY    = 'aicortex_registry';
  const _CACHE_TS_KEY = 'aicortex_registry_ts';

  function _persistRead() {
    try {
      if (_isNode) {
        const fs   = require('fs');
        const path = require('path');
        const dir  = _nodeModelsDir() || require('os').tmpdir();
        const file = path.join(dir, '.aicortex_registry_cache.json');
        if (!fs.existsSync(file)) return null;
        const { ts, data } = JSON.parse(fs.readFileSync(file, 'utf8'));
        return { ts: Number(ts), data };
      } else {
        const ts  = localStorage.getItem(_CACHE_TS_KEY);
        const raw = localStorage.getItem(_CACHE_KEY);
        if (!ts || !raw) return null;
        return { ts: Number(ts), data: JSON.parse(raw) };
      }
    } catch (_) { return null; }
  }

  function _persistWrite(entries) {
    try {
      const ts = Date.now();
      if (_isNode) {
        const fs   = require('fs');
        const path = require('path');
        const dir  = _nodeModelsDir() || require('os').tmpdir();
        const file = path.join(dir, '.aicortex_registry_cache.json');
        fs.writeFileSync(file, JSON.stringify({ ts, data: entries }), 'utf8');
      } else {
        localStorage.setItem(_CACHE_TS_KEY, String(ts));
        localStorage.setItem(_CACHE_KEY, JSON.stringify(entries));
      }
    } catch (_) {}
  }

  // ─── Node.js local models folder ─────────────────────────────────────────────

  function _nodeModelsDir() {
    if (!_isNode) return null;
    const path = require('path');
    const fs   = require('fs');
    const env  = process.env.AICORTEX_MODELS_DIR;
    if (env && fs.existsSync(env)) return env;
    const cwd = path.join(process.cwd(), 'models');
    if (fs.existsSync(cwd)) return cwd;
    return null;
  }

  function _nodeLocalFamily(family) {
    if (!_isNode) return null;
    try {
      const path = require('path');
      const fs   = require('fs');
      const dir  = _nodeModelsDir();
      if (!dir) return null;
      const file = path.join(dir, `${family}.json`);
      if (!fs.existsSync(file)) return null;
      return JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (_) { return null; }
  }

  /**
   * Browser-side local folder probe.
   * Tries ./models/<family>.json relative to the page before hitting remote sources.
   * Returns parsed JSON on success, null if the file is absent or unreachable.
   */
  async function _browserLocalFamily(family) {
    if (_isNode) return null;
    try {
      const ctrl  = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 3000);
      const res   = await fetch(`./models/${family}.json`, {
        signal: ctrl.signal,
        cache: 'no-store',
      });
      clearTimeout(timer);
      if (!res.ok) return null;
      return await res.json();
    } catch (_) { return null; }
  }

  // ─── JSON normalisation ───────────────────────────────────────────────────────

  /**
   * Convert one family's raw JSON into flat registry entries.
   * Supports both the new servers[] shape and the legacy ip_port shape.
   * Each entry: { url, model, family, tps, city, country, continent, org }
   */
  function _normaliseFamily(rawData, familyName) {
    let models = rawData;

    if (!Array.isArray(models)) {
      models = rawData?.props?.pageProps?.models ?? rawData?.models ?? [];
    }

    const entries = [];

    for (const m of models) {
      if (!m || typeof m !== 'object') continue;

      const modelName = m.name || m.model_name || m.model || m.id || '';
      if (!modelName) continue;

      // New shape: servers[]
      if (Array.isArray(m.servers)) {
        for (const srv of m.servers) {
          const url = srv.url || srv.base_url;
          if (!url) continue;
          entries.push({
            url:       url.replace(/\/$/, ''),
            model:     modelName,
            family:    familyName,
            tps:       Number(srv.performance?.tokens_per_second ?? srv.tps ?? 0),
            city:      srv.location?.city     || '',
            country:   srv.location?.country  || '',
            continent: srv.location?.continent || '',
            org:       srv.organization        || '',
            paramSize: m.parameter_size        || '',
          });
        }
      }
      // Legacy shape: ip_port
      else if (m.ip_port) {
        const url = m.ip_port.startsWith('http') ? m.ip_port : 'http://' + m.ip_port;
        entries.push({
          url:       url.replace(/\/$/, ''),
          model:     modelName,
          family:    familyName,  // keyed by filename, not m.family (which may differ e.g. gemma3 vs gemma)
          tps:       Number(m.perf_tokens_per_second ?? 0),
          city:      m.ip_city_name_en      || '',
          country:   m.ip_country_name_en   || '',
          continent: m.ip_continent_name_en || '',
          org:       m.ip_organization      || '',
          paramSize: m.parameter_size       || '',
        });
      }
    }

    return entries;
  }

  // ─── Remote fetch helpers ─────────────────────────────────────────────────────

  async function _fetchJson(url, timeoutMs = 8000) {
    try {
      const ctrl  = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), timeoutMs);
      const res   = await fetch(url, { signal: ctrl.signal });
      clearTimeout(timer);
      if (!res.ok) {
        console.warn(`[AICortex] fetch failed: ${url} → HTTP ${res.status}`);
        return null;
      }
      return await res.json();
    } catch (err) {
      console.warn(`[AICortex] fetch error: ${url} →`, err.message);
      return null;
    }
  }

  async function _fetchJsonMirrors(urlFns, ...args) {
    for (const fn of urlFns) {
      const data = await _fetchJson(fn(...args));
      if (data) return data;
    }
    return null;
  }

  // ─── Registry bootstrap ───────────────────────────────────────────────────────

  async function _buildLiveRegistry() {
    let families = null;
    const indexData = await _fetchJsonMirrors(_FAMILY_INDEX_SOURCES);
    if (Array.isArray(indexData)) families = indexData;
    if (!families || !families.length) {
      families = ['deepseek', 'gemma', 'llama', 'mistral', 'others', 'qwen'];
    }

    const allEntries = [];
    _registrySources = {}; // reset source map

    await Promise.all(families.map(async fam => {
      let raw  = null;
      let src  = null;

      raw = _nodeLocalFamily(fam);
      if (raw) { src = 'local'; }

      if (!raw) {
        raw = await _browserLocalFamily(fam);
        if (raw) { src = 'local'; }
      }

      if (!raw) {
        raw = await _fetchJsonMirrors(_REMOTE_SOURCES, fam);
        if (raw) { src = 'remote'; }
      }

      if (raw) {
        _registrySources[fam] = src;
        const entries = _normaliseFamily(raw, fam);
        // console.info(`[AICortex] ${fam}: ${entries.length} entries from ${src}`);
        allEntries.push(...entries);
      } else {
        _registrySources[fam] = 'missing';
        console.warn(`[AICortex] ${fam}: no source found (local + remote both failed)`);
      }
    }));

    if (!allEntries.length) return null;
    allEntries.sort((a, b) => (b.tps || 0) - (a.tps || 0));
    return allEntries;
  }

  function _ensureRegistry() {
    // If a fetch is already in flight, always join it rather than starting another
    if (_registryReady) return _registryReady;
    // If we already have a fresh live registry, no fetch needed
    if (_registryLive && (Date.now() - _registryFetchedAt) < _registryTTL) {
      return Promise.resolve();
    }

    _registryReady = (async () => {
      try {
        const cached = _persistRead();
        if (cached && (Date.now() - cached.ts) < _registryTTL &&
            Array.isArray(cached.data) && cached.data.length > 0) {
          _registry = cached.data;
          _registryFetchedAt = cached.ts;
          if ((Date.now() - cached.ts) > (_registryTTL * 0.5)) {
            _buildLiveRegistry().then(live => {
              if (live) {
                _registry = live;
                _registryFetchedAt = Date.now();
                _persistWrite(live);
              }
            }).catch(() => {});
          }
          return;
        }

        const live = await _buildLiveRegistry();
        if (live && live.length > 0) {
          _registry = live;
          _registryLive = true;
          _registryFetchedAt = Date.now();
          _persistWrite(live);
          return;
        }

        if (cached && Array.isArray(cached.data) && cached.data.length > 0) {
          _registry = cached.data;
          _registryFetchedAt = cached.ts;
          return;
        }

        _registry = [];
        _registryFetchedAt = Date.now();
      } catch (_) {
        if (!_registry) _registry = [];
      } finally {
        _registryReady = null;
      }
    })();

    return _registryReady;
  }

  function _getRegistry() {
    return _registry || [];
  }

  // Registry is loaded on first use or via refreshRegistry() — no auto-fire to avoid race with init()

  // ─── Connectivity check ───────────────────────────────────────────────────────

  /**
   * Lightweight connectivity probe — mirrors Python's _has_internet().
   * In browsers we can't open raw TCP sockets; we instead try to fetch a
   * tiny known-good resource with a short timeout.
   */
  async function _hasInternet() {
    if (_isNode) {
      return new Promise(resolve => {
        const net = require('net');
        const sock = new net.Socket();
        sock.setTimeout(3000);
        sock.connect(53, '8.8.8.8', () => { sock.destroy(); resolve(true); });
        sock.on('error',   () => { sock.destroy(); resolve(false); });
        sock.on('timeout', () => { sock.destroy(); resolve(false); });
      });
    }
    // Browser: use navigator.onLine as fast-fail, then try a real probe
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
    try {
      const ctrl  = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 3000);
      await fetch('https://www.google.com/generate_204', {
        method: 'HEAD',
        mode: 'no-cors',
        cache: 'no-store',
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      return true;
    } catch (_) { return false; }
  }

  // ─── Failed-server blacklist (TTL-based) ──────────────────────────────────────
  // Mirrors Python's _FAILED_SERVERS dict + _mark_server_failed / _is_server_failed

  const _failed      = new Map(); // url → expiry ms timestamp
  let   _FAIL_TTL    = 120_000;   // 2 minutes — same as Python

  function _markFailed(url) {
    _failed.set(url, Date.now() + _FAIL_TTL);
  }

  function _isFailed(url) {
    const exp = _failed.get(url);
    if (!exp) return false;
    if (Date.now() >= exp) { _failed.delete(url); return false; }
    return true;
  }

  // ─── Best-server cache ────────────────────────────────────────────────────────
  // Mirrors Python's _BEST_SERVER_CACHE with a 5-minute TTL

  const _bestServerCache    = new Map(); // `${model}:${strategy}` → { entry, expiry }
  const _BEST_SERVER_TTL    = 5 * 60 * 1000; // 5 minutes

  // ─── Server scoring & routing ─────────────────────────────────────────────────

  /**
   * Score a registry entry based on the selected routing strategy.
   * Mirrors Python's _sort_servers_by_performance + best_server().
   *
   *  "fastest"  — sort by tokens/second descending
   *  "nearest"  — sort by presence of geo metadata (simple heuristic)
   *  "balanced" — 60% speed + 40% proximity (mirrors Python)
   *  "random"   — shuffle
   */
  function _scoreEntry(entry, strategy) {
    if (_isFailed(entry.url)) return -Infinity;

    const speed = entry.tps || 0;

    if (strategy === 'fastest') return speed;

    // Proximity heuristic: having any location data = 1.0 score base
    const hasGeo = (entry.city || entry.country || entry.continent) ? 1.0 : 0.0;

    if (strategy === 'nearest') return hasGeo;

    if (strategy === 'balanced') return 0.6 * speed + 0.4 * hasGeo;

    // "random": use Math.random() so each call shuffles
    return Math.random();
  }

  /**
   * Return all registry entries for `model` (or all if null),
   * sorted by the given routing strategy.
   */
  function _rankServers(model, strategy = 'fastest') {
    const reg = _getRegistry();
    const candidates = model
      ? reg.filter(e => e.model === model)
      : [...reg];

    return candidates.sort((a, b) =>
      _scoreEntry(b, strategy) - _scoreEntry(a, strategy)
    );
  }

  /**
   * Return the single best entry for a model, with best-server caching.
   * Mirrors Python's best_server() function.
   */
  function _pickServer(model, strategy = 'fastest') {
    const cacheKey = `${model ?? '__any__'}:${strategy}`;
    const cached   = _bestServerCache.get(cacheKey);
    if (cached && Date.now() < cached.expiry && !_isFailed(cached.entry.url)) {
      return cached.entry;
    }

    const ranked = _rankServers(model, strategy);
    const entry  = ranked.find(e => !_isFailed(e.url)) ?? ranked[0] ?? null;

    if (entry) {
      _bestServerCache.set(cacheKey, { entry, expiry: Date.now() + _BEST_SERVER_TTL });
    }
    return entry;
  }

  // ─── Exponential backoff helper ───────────────────────────────────────────────

  function _backoffMs(attempt, base = 500) {
    // base * 2^attempt + jitter [0, 100ms] — mirrors Python's retry_backoff logic
    return base * Math.pow(2, attempt) + Math.random() * 100;
  }

  function _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ─── Errors ───────────────────────────────────────────────────────────────────

  class AICortexError extends Error {
    constructor(msg, opts = {}) {
      super(msg);
      this.name   = 'AICortexError';
      this.status = opts.status ?? null;
      this.code   = opts.code   ?? null;
    }
  }

  class AICortexConnectionError extends AICortexError {
    constructor(url, detail = '') {
      super(
        `Could not connect to Ollama server at "${url}".` +
        (detail ? ` (${detail})` : '') +
        ' aicortex will try the next available server automatically.'
      );
      this.name = 'AICortexConnectionError';
      this.url  = url;
    }
  }

  class AICortexModelNotFoundError extends AICortexError {
    constructor(model) {
      super(
        `No community servers found for model "${model}". ` +
        'Call ai.models() for the full list of available models.'
      );
      this.name  = 'AICortexModelNotFoundError';
      this.model = model;
    }
  }

  class AICortexNoInternetError extends AICortexError {
    constructor() {
      super(
        'No internet connection detected. ' +
        'Please check your network and try again.'
      );
      this.name = 'AICortexNoInternetError';
      this.code = 'NO_INTERNET';
    }
  }

  // ─── Session ──────────────────────────────────────────────────────────────────
  // Aligned with Python Session class: id, history, reset(), delete()

  const _SESSION_STORE = new Map(); // id → Array<{role, content}>

  class Session {
    constructor(id = null) {
      if (id === null) {
        // Auto-generate short id and register empty history — matches Python
        const generated = Math.random().toString(36).slice(2, 10);
        _SESSION_STORE.set(generated, []);
        this._id = generated;
      } else {
        if (!_SESSION_STORE.has(id)) {
          throw new Error(
            `No session with id '${id}' found. ` +
            `Create one with new Session() then resume with its id.`
          );
        }
        this._id = id;
      }
    }

    get id()      { return this._id; }
    get history() { return [...(_SESSION_STORE.get(this._id) || [])]; }
    get turns()   { return Math.floor(((_SESSION_STORE.get(this._id) || []).length) / 2); }

    /** Add a message to this session's history (internal use). */
    _push(role, content) {
      const hist = _SESSION_STORE.get(this._id);
      if (hist) hist.push({ role, content });
    }

    /** Clear history without removing the session id. */
    reset() { _SESSION_STORE.set(this._id, []); }

    /** Remove this session from the store entirely. */
    delete() { _SESSION_STORE.delete(this._id); }

    toString() { return `Session(id=${this._id}, turns=${this.turns})`; }
  }

  // ─── StreamReader ─────────────────────────────────────────────────────────────

  class StreamReader {
    constructor(fetchFn, sessionOpts = null) {
      this._fetchFn     = fetchFn;
      this._sessionOpts = sessionOpts; // { session, prompt } or null
      this.text         = '';
      this._events      = []; // mirrors Python _LazyStream.events
    }

    /** Collect the full response as a string. */
    async collect() {
      let result = '';
      for await (const token of this) result += token;
      return result;
    }

    [Symbol.asyncIterator]() {
      let buffer   = '';
      let response = null;
      let reader   = null;
      let done     = false;

      const fetchFn     = this._fetchFn;
      const self        = this;
      const sessionOpts = this._sessionOpts;
      let   flushed     = false;

      return {
        async next() {
          if (done) {
            if (!flushed && sessionOpts) {
              flushed = true;
              sessionOpts.session._push('user', sessionOpts.prompt);
              sessionOpts.session._push('assistant', self.text);
            }
            return { value: undefined, done: true };
          }

          if (!response) {
            response = await fetchFn();
            reader   = response.body.getReader();
          }

          while (true) {
            const nl = buffer.indexOf('\n');
            if (nl !== -1) {
              const line = buffer.slice(0, nl).trim();
              buffer = buffer.slice(nl + 1);
              if (!line) continue;
              try {
                const obj   = JSON.parse(line);
                const token = obj.message?.content ?? obj.response ?? '';
                if (token) {
                  self.text += token;
                  self._events.push({ type: 'token', content: token });
                  return { value: token, done: false };
                }
                if (obj.done) {
                  done = true;
                  if (!flushed && sessionOpts) {
                    flushed = true;
                    sessionOpts.session._push('user', sessionOpts.prompt);
                    sessionOpts.session._push('assistant', self.text);
                  }
                  return { value: undefined, done: true };
                }
              } catch (_) { continue; }
            }

            const { value, done: streamDone } = await reader.read();
            if (streamDone) {
              done = true;
              return { value: undefined, done: true };
            }
            buffer += new TextDecoder().decode(value);
          }
        },
      };
    }
  }

  // ─── AICortex ─────────────────────────────────────────────────────────────────

  /**
   * Main SDK class.
   *
   * @param {object}  [opts]
   * @param {string}  [opts.model]         Default model name.
   * @param {string}  [opts.ollamaUrl]     Pin to your own Ollama instance.
   * @param {number}  [opts.temperature]   Sampling temperature (0–2). Default 0.7.
   * @param {number}  [opts.topP]          Nucleus sampling. Default 0.9.
   * @param {number}  [opts.maxTokens]     Max tokens to generate. Default 1024.
   * @param {number}  [opts.timeout]       Request timeout ms. Default 30000.
   * @param {number}  [opts.retries]       Server retry attempts. Default 3.
   * @param {number}  [opts.retryBackoff]  Base ms for exponential backoff. Default 500.
   * @param {string}  [opts.routing]       "fastest"|"nearest"|"balanced"|"random". Default "fastest".
   */
  class AICortex {
    constructor(opts = {}) {
      this.defaultModel   = opts.model        ?? 'gpt-oss:20b';
      this.ollamaUrl      = opts.ollamaUrl    ? opts.ollamaUrl.replace(/\/$/, '') : null;
      this.temperature    = opts.temperature  ?? 0.7;
      this.topP           = opts.topP         ?? 0.9;
      this.maxTokens      = opts.maxTokens    ?? 1024;
      this.timeout        = opts.timeout      ?? 30_000;
      this.retries        = opts.retries      ?? 3;
      this.retryBackoff   = opts.retryBackoff ?? 500;
      this.routing        = opts.routing      ?? 'fastest';
    }

    // ── Internal helpers ───────────────────────────────────────────────────────

    _resolveServer(model, strategy) {
      if (this.ollamaUrl) {
        return { url: this.ollamaUrl, model: model ?? this.defaultModel ?? 'llama3.2:3b' };
      }
      const target = model ?? this.defaultModel ?? null;
      const entry  = _pickServer(target, strategy ?? this.routing);
      if (!entry) throw new AICortexModelNotFoundError(target ?? '(any)');
      return entry;
    }

    /**
     * Core fetch-with-retry loop.
     * Mirrors Python's _chat() / _stream_chat() retry logic with exponential backoff
     * and blacklisting.
     */
    async _fetchWithRetry(path, body, stream = false, routingStrategy = null) {
      // Ensure registry is loaded
      await _ensureRegistry();

      // ── Fast-fail: no point hitting servers without internet ────────────────
      const online = await _hasInternet();
      if (!online) throw new AICortexNoInternetError();

      const strategy = routingStrategy ?? this.routing;
      const target   = body.model ?? this.defaultModel ?? 'gpt-oss:20b';

      // Build ranked server list once for this request (mirrors Python's ranked[:max_retries])
      let ranked;
      if (this.ollamaUrl) {
        ranked = [{ url: this.ollamaUrl, model: target ?? 'llama3.2:3b' }];
      } else {
        ranked = _rankServers(target, strategy);
        if (!ranked.length) throw new AICortexModelNotFoundError(target ?? '(any)');
      }

      // Cap attempts to this.retries — mirrors Python's ranked[:max_retries]
      const candidates = ranked.slice(0, this.retries);
      const errors     = [];

      for (let attempt = 0; attempt < candidates.length; attempt++) {
        const server = candidates[attempt];
        const url    = server.url;

        if (_isFailed(url)) continue; // skip recently-failed — mirrors Python

        try {
          const ctrl  = new AbortController();
          const timer = setTimeout(() => ctrl.abort(), this.timeout);
          const reqBody = { ...body, model: server.model };

          const response = await fetch(`${url}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqBody),
            signal: ctrl.signal,
          });
          clearTimeout(timer);

          if (!response.ok) {
            _markFailed(url);
            errors.push(`${url} (HTTP ${response.status})`);
            if (attempt < candidates.length - 1) {
              await _sleep(_backoffMs(attempt, this.retryBackoff));
            }
            continue;
          }

          return response;
        } catch (err) {
          _markFailed(url);
          const detail = err.name === 'AbortError'
            ? `timed out after ${this.timeout}ms`
            : err.message;
          errors.push(`${url} (${err.name}: ${detail})`);

          if (attempt < candidates.length - 1) {
            await _sleep(_backoffMs(attempt, this.retryBackoff));
          }
        }
      }

      throw new AICortexError(
        `All server attempts failed for model "${target}".\n` +
        errors.map(e => `  • ${e}`).join('\n'),
        { code: 'ALL_FAILED' }
      );
    }

    _buildChatBody(prompt, opts, streaming) {
      const session = opts.session instanceof Session ? opts.session : null;

      // Build message list — mirrors Python's _build_kwargs / _SESSION_STORE
      let messages;
      if (session) {
        messages = [
          ...session.history,
          { role: 'user', content: prompt },
        ];
      } else {
        messages = [{ role: 'user', content: prompt }];
      }

      if (opts.system) {
        messages.unshift({ role: 'system', content: opts.system });
      }

      return {
        model: opts.model ?? this.defaultModel ?? 'gpt-oss:20b',
        messages,
        stream: streaming,
        options: {
          temperature: opts.temperature ?? this.temperature,
          top_p:       opts.topP        ?? this.topP,
          num_predict: opts.maxTokens   ?? this.maxTokens,
          ...(opts.stop ? { stop: opts.stop } : {}),
        },
      };
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    /**
     * Send a prompt and get back the full response text.
     *
     * @param {string} prompt
     * @param {object} [opts]
     * @param {string}  [opts.model]          Override model for this call.
     * @param {string}  [opts.routing]         "fastest"|"nearest"|"balanced"|"random"
     * @param {Session} [opts.session]         Multi-turn session for memory.
     * @param {string}  [opts.system]          System prompt.
     * @param {string}  [opts.response_format] "text" (default) or "json".
     * @param {number}  [opts.temperature]
     * @param {number}  [opts.topP]
     * @param {number}  [opts.maxTokens]
     * @param {Array}   [opts.stop]
     * @returns {Promise<string|object>}
     */
    async chat(prompt, opts = {}) {
      // JSON mode: inject system instruction — mirrors Python chat()
      let effectiveOpts = { ...opts };
      if (opts.response_format === 'json') {
        const jsonInstruction = 'Respond only with valid JSON. No prose, no markdown.';
        effectiveOpts.system = opts.system
          ? `${opts.system}\n${jsonInstruction}`
          : jsonInstruction;
      }

      const body     = this._buildChatBody(prompt, effectiveOpts, false);
      const strategy = opts.routing ?? this.routing;
      const res      = await this._fetchWithRetry('/api/chat', body, false, strategy);
      const data     = await res.json();
      const text     = data.message?.content ?? data.response ?? '';

      // Session history update — mirrors Python _sync_chat / _SESSION_STORE
      if (opts.session instanceof Session) {
        opts.session._push('user', prompt);
        opts.session._push('assistant', text);
      }

      // JSON mode: parse and return object
      if (opts.response_format === 'json') {
        try {
          // Strip optional markdown fences before parsing
          const clean = text.replace(/```json|```/gi, '').trim();
          return JSON.parse(clean);
        } catch (_) {
          throw new AICortexError(`Model returned non-JSON: ${text}`, { code: 'PARSE_ERROR' });
        }
      }

      return text;
    }

    /**
     * Stream a response token-by-token. Returns an async-iterable StreamReader.
     *
     * @param {string} prompt
     * @param {object} [opts]
     * @returns {StreamReader}
     */
    stream(prompt, opts = {}) {
      const body        = this._buildChatBody(prompt, opts, true);
      const strategy    = opts.routing ?? this.routing;
      const sessionOpts = (opts.session instanceof Session)
        ? { session: opts.session, prompt }
        : null;

      return new StreamReader(
        () => this._fetchWithRetry('/api/chat', body, true, strategy),
        sessionOpts,
      );
    }

    /**
     * Create a new multi-turn Session.
     * @returns {Session}
     */
    session() { return new Session(); }

    /**
     * Search models by substring, family, or parameter-size range.
     * Mirrors Python's search_models().
     *
     * @param {string}  query       Substring to match against model names (case-insensitive).
     * @param {object}  [opts]
     * @param {string}  [opts.family]    Restrict to a specific model family.
     * @param {string}  [opts.minParams] Min parameter size, e.g. "7b".
     * @param {string}  [opts.maxParams] Max parameter size, e.g. "70b".
     * @returns {Array<{model, family, tps, city, country, paramSize}>}
     */
    search(query, opts = {}) {
      const q    = query.toLowerCase();
      const reg  = _getRegistry();

      function parseBillions(s) {
        if (!s) return null;
        const n = parseFloat(String(s).replace(/b$/i, ''));
        return isNaN(n) ? null : n;
      }

      const minB = parseBillions(opts.minParams);
      const maxB = parseBillions(opts.maxParams);

      // De-duplicate by model name
      const seen    = new Set();
      const results = [];

      for (const entry of reg) {
        if (opts.family && entry.family.toLowerCase() !== opts.family.toLowerCase()) continue;
        if (!entry.model.toLowerCase().includes(q)) continue;

        const sizeB = parseBillions(entry.paramSize);
        if (minB !== null && sizeB !== null && sizeB < minB) continue;
        if (maxB !== null && sizeB !== null && sizeB > maxB) continue;

        if (!seen.has(entry.model)) {
          seen.add(entry.model);
          results.push(entry);
        }
      }

      // Sort by paramSize descending (largest/most capable first) — matches Python
      results.sort((a, b) => {
        const aB = parseBillions(a.paramSize) ?? -1;
        const bB = parseBillions(b.paramSize) ?? -1;
        return bB - aB;
      });

      return results;
    }

    /**
     * List available model names from the live registry, optionally filtered by family.
     * @param {string} [family]
     * @returns {string[]}
     */
    models(family) {
      const reg = _getRegistry();
      if (!family) return [...new Set(reg.map(e => e.model))].sort();
      const fam = family.toLowerCase();
      return [...new Set(
        reg.filter(e => e.family.toLowerCase() === fam).map(e => e.model)
      )].sort();
    }

    /**
     * List available model families.
     * @returns {string[]}
     */
    families() {
      const fams = new Set();
      for (const e of _getRegistry()) {
        const fam = e.family || e.model.split(/[\d.:]/)[0].replace(/-$/, '');
        if (fam && fam !== 'unknown') fams.add(fam);
      }
      return [...fams].sort();
    }

    /**
     * List all known community servers for a model, sorted by speed.
     * @param {string} [model]
     * @returns {Array<{url, model, tps, city, country, continent, org}>}
     */
    servers(model) {
      const entries = model
        ? _getRegistry().filter(e => e.model === model)
        : _getRegistry();
      return [...entries].sort((a, b) => (b.tps || 0) - (a.tps || 0));
    }

    /**
     * Get the best available server for a model using the given strategy.
     * Results are cached for 5 minutes — mirrors Python's best_server().
     *
     * @param {string} [model]
     * @param {"fastest"|"nearest"|"balanced"|"random"} [strategy]
     * @returns {{url, model, tps, city, country, continent, org} | null}
     */
    bestServer(model, strategy) {
      return _pickServer(
        model    ?? this.defaultModel ?? null,
        strategy ?? this.routing,
      );
    }

    /**
     * LangChain-compatible {model, base_url} params.
     * @param {string} [model]
     * @param {string} [strategy]
     * @returns {{model: string, base_url: string}}
     */
    llmParams(model, strategy) {
      const entry = _pickServer(
        model    ?? this.defaultModel ?? null,
        strategy ?? this.routing,
      );
      if (!entry) throw new AICortexModelNotFoundError(model ?? '(any)');
      return { model: entry.model, base_url: entry.url };
    }

    /**
     * Force a fresh registry fetch, ignoring cache TTL.
     * @returns {Promise<void>}
     */
    async refreshRegistry() {
      if (_registryReady) await _registryReady.catch(() => {});
      _registry = null;
      _registryLive = false;
      _registryFetchedAt = 0;
      _registrySources = {};
      _bestServerCache.clear();
      _persistWrite([]); // clear stale localStorage cache so _ensureRegistry always fetches live
      await _ensureRegistry();
    }

    /**
     * Clear the best-server selection cache so the next call re-evaluates.
     */
    clearServerCache() {
      _bestServerCache.clear();
    }

    /**
     * Return registry source metadata — useful for debugging.
     * @returns {{ source: string, entries: number, age_s: number, ttl_s: number }}
     */
    registryInfo() {
      const reg = _getRegistry();
      const age = _registryFetchedAt ? Math.round((Date.now() - _registryFetchedAt) / 1000) : null;
      const hasLocal  = Object.values(_registrySources).some(s => s === 'local');
      const hasRemote = Object.values(_registrySources).some(s => s === 'remote');
      const source = !_registryLive ? 'seed'
        : hasLocal && hasRemote ? 'mixed'
        : hasLocal  ? 'local'
        : hasRemote ? 'remote'
        : 'empty';
      return {
        source,
        sources:  { ..._registrySources },
        entries:  reg.length,
        age_s:    age,
        ttl_s:    Math.round(_registryTTL / 1000),
        live:     _registryLive,
      };
    }
  }

  // ─── Static config & exports ─────────────────────────────────────────────────

  AICortex.Session                    = Session;
  AICortex.StreamReader               = StreamReader;
  AICortex.AICortexError              = AICortexError;
  AICortex.AICortexConnectionError    = AICortexConnectionError;
  AICortex.AICortexModelNotFoundError = AICortexModelNotFoundError;
  AICortex.AICortexNoInternetError    = AICortexNoInternetError;

  AICortex.version = '0.0.2';

  Object.defineProperty(AICortex, 'registryTTL', {
    get: () => _registryTTL,
    set: (ms) => { _registryTTL = ms; },
    enumerable: true,
  });

  Object.defineProperty(AICortex, 'failTTL', {
    get: () => _FAIL_TTL,
    set: (ms) => { _FAIL_TTL = ms; },
    enumerable: true,
    configurable: true,
  });

  /** Module-level registry refresh (mirrors Python AICortex.refreshRegistry) */
  AICortex.refreshRegistry = async function () {
    if (_registryReady) await _registryReady.catch(() => {});
    _registry = null;
    _registryLive = false;
    _registryFetchedAt = 0;
    _registrySources = {};
    _bestServerCache.clear();
    _persistWrite([]); // clear stale localStorage cache
    await _ensureRegistry();
  };

  /** Module-level server cache clear */
  AICortex.clearServerCache = function () {
    _bestServerCache.clear();
  };

  return AICortex;
}));