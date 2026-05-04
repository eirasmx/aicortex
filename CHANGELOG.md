# 📋 Changelog

All notable changes to AI Cortex are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
AI Cortex adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Version format:** `MAJOR.MINOR.PATCH`
> - **MAJOR** — breaking changes to the public API
> - **MINOR** — new features, backward-compatible
> - **PATCH** — bug fixes and minor improvements, backward-compatible

---

## [1.0.4] — 2026-05-04

### ✨ Changed

- **`max_tokens` default changed from `128` → `None`** — the old hard cap of 128 tokens silently truncated long responses.  `None` omits `num_predict` from the Ollama request entirely, letting the server apply its own default (typically unlimited or model-specific).  Callers who need a budget can still pass `max_tokens=<int>` explicitly.
- **`_OllamaAPI.__init__` signature updated** — `max_tokens` parameter type broadened to `Optional[int]` and default set to `None` to match the above change.  `build_api_request` now omits `num_predict` from the options dict when the resolved value is `None`.

### 🐛 Fixed

- **`timeout` now wired into the Ollama client** — `timeout` was accepted and popped from kwargs in both `_chat` and `_stream_chat` but never forwarded to `ollama.Client`, making it a no-op.  It is now passed as `Client(host=..., timeout=timeout)` so the declared 30-second default actually takes effect.
- **DeepWiki badge added to README** — links to `https://deepwiki.com/eirasmx/aicortex`.

---

## [1.0.3] — 2026-05-03

### ✨ Added

#### Session — Multi-turn Memory (`1.1`)
- `Session` class in `aicortex/session.py` with auto-generated or user-supplied session id
- `Session.id` — read-only property exposing the session identity string
- `Session.history` — read-only property returning a copy of the stored turn list
- `Session.reset()` — clears history while keeping the session id registered
- `Session.delete()` — removes the session from the in-process store entirely
- `session: Session | str | None = None` param on `chat()` — enables multi-turn conversation accumulation
- `Session` exported from `aicortex.__init__` and added to type stubs

#### Async Support (`1.2`)
- `chat()` is now dual-mode: detects a running event loop and returns a coroutine automatically
- Internal `_sync_chat()` and `_async_chat()` dispatch functions (private, not exported)
- `stream=True` in async mode yields `StreamEvent` objects via `async for`
- Session store writes are safe in both sync and async paths — shared `_SESSION_STORE` dict

#### Structured Output / JSON Mode (`1.3`)
- `response_format: Literal["text", "json"] = "text"` param on `chat()`
- `schema: dict | None = None` param on `chat()` — validates parsed JSON against a JSON Schema via `jsonschema`
- Returns `dict` instead of `str` when `response_format="json"` and `stream=False`
- Raises `ValueError` if `response_format="json"` and `stream=True` are combined

#### `system` Param on `chat()` (`1.4`)
- `system: str | None = None` as an explicit keyword argument on `chat()`; forwarded to `build_api_request()`
- Raises `ValueError` if both `system` and `persona` are passed simultaneously

#### Smart Routing (`1.5`)
- `routing: Literal["random", "fastest", "nearest"] = "random"` param on `chat()`
- `best_server(model, strategy)` top-level function — returns the highest-scoring server for a model
- Three strategies: `"fastest"` (live TPS probe), `"nearest"` (bundled geo metadata), `"balanced"` (60/40 weighted)
- `best_server()` results cached per `(model, strategy)` key with a 5-minute in-process TTL
- `best_server` exported from `aicortex.__init__` and added to type stubs

---

## [1.0.2] — 2026-05-02

### 🐛 Fixed

- Typo in `setup.py` project URL: `masteer` → `master` in the Changelog link

---

## [1.0.1] — 2026-05-02

### 📖 Changed

- Completed full documentation rewrite across all `docs/` pages — API reference,
  usage guide, streaming guide, models guide, server guide, tools guide,
  contributing guide, and development guide
- Added `docs/examples/` section with annotated examples for chat, streaming,
  server, and the tools pipeline
- Rewrote all Python docstrings in `aicortex/` source files
- Moved Sphinx config from `source/conf.py` to `docs/conf.py`; removed `source/` directory
- Rewrote `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`

---

## [1.0.0] — 2026-05-02

> 🎉 **Initial production release** — AI Cortex is live.

### ✨ Added

#### Core Chat API
- `chat(prompt, *, model, stream, **kwargs)` — unified interface for sending prompts to any Ollama-compatible model
- Sync mode returns a plain `str`; `stream=True` returns a `Stream` object
- Automatic server discovery and health-checking on every call
- Failover to next available server when the primary is unreachable

#### Streaming
- `Stream` — iterable container for streamed model responses
- `StreamEvent` — typed event dataclass with `type`, `content`, `index`, `model`, and `done` fields
- `EventType` enum: `START`, `TOKEN`, `END`, `ERROR`
- `Stream.text()` — convenience method to collect all token content into a single string

#### Model Discovery
- `families()` — list all available model families (llama, mistral, deepseek, qwen, gemma)
- `models(family)` — list all model identifiers within a family
- `get_model_info(model)` — return full metadata dict for a specific model
- `list_model_servers(model)` — return all known server URLs for a model
- `get_server_info(model, server_url)` — return health and capability info for a specific server

#### Request Building
- `build_api_request(model, prompt, **kwargs)` — construct a raw Ollama-compatible request dict
- `get_llm_params(model)` — return the recommended parameter set for a model
- `get_random_llm_params(model)` — return a randomized parameter set for creative variation

#### Bundled Model Families
- **Llama** — Meta's Llama 3.x family: 3B, 8B, 70B, 405B variants
- **Mistral** — Mistral AI models: 7B, Mixtral 8x7B, Mixtral 8x22B
- **Deepseek** — DeepSeek models: 1.3B, 6.7B, 33B, 67B
- **Qwen** — Alibaba Qwen models: 0.5B, 1.8B, 7B, 14B, 72B
- **Gemma** — Google Gemma models: 2B, 7B

#### Tool Pipeline
- `check_models` — validate server endpoints concurrently; produces a health report
- `fetch_models` — fetch current model lists from all live servers
- `resolve_models` — merge fetched data with existing metadata; deduplicate entries
- `apply_valid_models` — atomically write resolved metadata to `aicortex/models/*.json`

#### OpenAI-Compatible Server
- FastAPI-based proxy server exposing OpenAI-compatible REST endpoints
- `POST /v1/chat/completions` — drop-in replacement for OpenAI's chat completions
- `GET /v1/models` — list available models in OpenAI format
- `GET /health` — server health check endpoint
- Works with any existing OpenAI SDK or client library
- CLI entry point: `aicortex-server`

#### Type System
- Complete type stubs in `aicortex/stubs/` for all public symbols
- `@overload` declarations for `chat()` expressing the conditional return type
- `mypy --strict` passes with zero errors

#### Documentation
- Full Sphinx documentation at [aicortex.readthedocs.io](https://aicortex.readthedocs.io/)
- API reference, quickstart, usage guide, streaming guide, models guide, server guide, tools guide

### 🔧 Technical

- **Python support** — 3.8, 3.9, 3.10, 3.11, 3.12
- **Dependencies** — `ollama>=0.1.0`, `pydantic>=2.0.0`; server extras add `fastapi` and `uvicorn`
- **CI matrix** — all supported Python versions on Ubuntu, with flake8, black, mypy, pytest, and Codecov
- **Distribution** — source distribution and universal wheel published to PyPI as `aicortex-core`

---

## Pre-Release

*No pre-release versions. This is the first public release.*

---

## 📌 How to Read This Changelog

Each release section uses these headings:

| Heading | Meaning |
|---|---|
| `✨ Added` | New features |
| `🔄 Changed` | Changes to existing functionality |
| `⚠️ Deprecated` | Features that will be removed in a future release |
| `🗑️ Removed` | Features removed in this release |
| `🐛 Fixed` | Bug fixes |
| `🔒 Security` | Security-related fixes |

---

[1.0.3]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.3
[1.0.2]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.2
[1.0.1]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.1
[1.0.0]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.0
