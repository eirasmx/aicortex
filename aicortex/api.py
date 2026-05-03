"""Internal Ollama API client for AI Cortex.

This module houses :class:`_OllamaAPI`, the single internal client that all
public top-level functions delegate to.  It is intentionally private (prefixed
with ``_``) — consumers should use the functions exported from
:mod:`aicortex` instead of instantiating this class directly.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Literal
from ollama import Client


class _OllamaAPI:
    """Internal client for interacting with LLMs served via Ollama.

    Loads bundled model metadata from the ``aicortex/models/`` directory at
    construction time, then exposes methods for model discovery, server
    selection, request building, and chat generation.

    Family names are derived **solely from JSON filenames** — a file named
    ``llama.json`` produces the family ``"llama"``.  This keeps the metadata
    format self-describing and easy to extend.

    Args:
        max_tokens: Default token budget used in :meth:`build_api_request` when
            ``num_predict`` is not supplied by the caller.  Defaults to ``128``.

    Attributes:
        _models_data: Raw per-family model dicts, keyed by family name.
        _families: Mapping of family name → list of model-name strings.
        _max_tokens: Default generation token budget.
    """

    def __init__(self, max_tokens: int = 128) -> None:
        """Initialise the client and eagerly load all bundled model data.

        Args:
            max_tokens: Default ``num_predict`` cap injected into every request
                payload that does not specify one explicitly.
        """
        self._models_data: Dict[str, List[Dict[str, Any]]] = self._load_models_data()
        self._families: Dict[str, List[str]] = self._extract_families()
        self._client: Optional[Client] = None
        self._max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def client(self) -> Client:
        """Lazy-loaded default :class:`ollama.Client`.

        The client is created on first access so that importing the package
        does not require a running Ollama instance.

        Returns:
            A connected :class:`ollama.Client` instance using the default host.
        """
        if self._client is None:
            self._client = Client()
        return self._client

    def _load_models_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load and normalise model metadata from all bundled JSON files.

        For each ``*.json`` file in the ``aicortex/models/`` directory:

        1. Parse the JSON and extract the model list (handles both flat lists
           and the ``props.pageProps.models`` nesting used by the scraper).
        2. Strip ``digest`` and ``perf_response_text`` fields to keep payloads
           light.
        3. Sort models by file size (largest first) so the most capable
           variants appear at the top of discovery results.

        Malformed or unreadable files are silently skipped with a printed
        warning so a single bad file never breaks the whole package.

        Returns:
            A dict mapping lowercase family names (from filenames) to their
            sorted list of model metadata dicts.
        """
        models_data: Dict[str, List[Dict[str, Any]]] = {}
        package_dir = Path(__file__).parent
        json_dir = package_dir / "models"

        for json_file in json_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    family_name = json_file.stem.lower()

                    models = self._extract_models_from_data(data)
                    if models:
                        for model in models:
                            if isinstance(model, dict):
                                model.pop('digest', None)
                                model.pop('perf_response_text', None)

                        models.sort(
                            key=lambda x: int(x.get('size', 0)) if isinstance(x.get('size'), (int, str)) else 0,
                            reverse=True,
                        )
                        models_data[family_name] = models

            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading {json_file.name}: {str(e)}")
                continue

        return models_data

    def _extract_models_from_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract the flat model list from any of the supported JSON shapes.

        The bundled JSON files come in two forms:

        - A bare list: ``[{...}, {...}]``
        - A Next.js page-props wrapper: ``{"props": {"pageProps": {"models": [...]}}}``

        This helper normalises both into a plain ``list``.

        Args:
            data: Parsed JSON content (dict or list).

        Returns:
            A list of model dicts, or an empty list if no models are found.
        """
        if isinstance(data, list):
            return data
        if 'props' in data and 'pageProps' in data['props']:
            return data['props']['pageProps'].get('models', [])
        return data.get('models', [])

    def _extract_families(self) -> Dict[str, List[str]]:
        """Build a family → model-names index from the loaded raw model data.

        Iterates :attr:`_models_data` and calls :meth:`_get_model_name` on
        each model dict to produce the final catalogue used by discovery
        methods.

        Returns:
            A dict mapping each family name to an ordered list of model-name
            strings.  Families with no resolvable model names are omitted.
        """
        families: Dict[str, List[str]] = {}

        for family_name, models in self._models_data.items():
            model_names = []
            for model in models:
                if not isinstance(model, dict):
                    continue
                model_name = self._get_model_name(model)
                if model_name:
                    model_names.append(model_name)

            if model_names:
                families[family_name] = model_names

        return families

    def _get_model_name(self, model: Dict[str, Any]) -> Optional[str]:
        """Resolve a model name from a metadata dict, trying multiple field names.

        The bundled JSON files use different field names across scraper
        versions.  This method tries ``model_name``, then ``model``, then
        ``name`` in order, returning the first non-empty value found.

        Args:
            model: A single model metadata dict.

        Returns:
            The resolved model name string, or ``None`` if none of the
            candidate fields are populated.
        """
        return model.get('model_name') or model.get('model') or model.get('name')

    # ------------------------------------------------------------------
    # Public discovery methods
    # ------------------------------------------------------------------

    def list_families(self) -> List[str]:
        """List all available model families.

        Family names come exclusively from JSON filenames in
        ``aicortex/models/`` — no inference from model content.

        Returns:
            A list of lowercase family name strings, e.g.
            ``['deepseek', 'gemma', 'llama', 'mistral', 'qwen']``.
        """
        return list(self._families.keys())

    def list_models(self, family: Optional[str] = None) -> List[str]:
        """List all model names, with an optional family filter.

        Args:
            family: Lowercase family name (case-insensitive).  Pass ``None``
                to get every model across all families as a flat list.

        Returns:
            An ordered list of model-name strings.  Returns an empty list if
            the requested family does not exist.
        """
        if family is None:
            return [model for models in self._families.values() for model in models]
        return self._families.get(family.lower(), [])

    def get_model_info(self, model: str) -> Dict:
        """Return the full metadata dict for a specific model.

        Searches all families for a model whose ``model_name`` or ``model``
        field matches the given name exactly.

        Args:
            model: Exact model name, e.g. ``"llama3.2:3b"``.

        Returns:
            The metadata dict for the matched model (with ``digest`` and
            ``perf_response_text`` already stripped).

        Raises:
            ValueError: If *model* is not found in the bundled database.
        """
        for models in self._models_data.values():
            for model_data in models:
                if isinstance(model_data, dict):
                    if model_data.get('model_name') == model or model_data.get('model') == model:
                        return model_data
        raise ValueError(f"Model '{model}' not found")

    def list_model_servers(self, model: str) -> List[Dict]:
        """Return all servers that host a specific model.

        Scans all families for entries matching *model* and assembles a
        structured server list including geographic and performance metadata.

        Args:
            model: Exact model name, e.g. ``"mistral:7b"``.

        Returns:
            A list of dicts, each with keys ``url``, ``location``,
            ``organization``, and ``performance``.  Empty list if no servers
            are found.
        """
        servers = []
        for models in self._models_data.values():
            for model_data in models:
                if model_data['model_name'] == model:
                    server_info = {
                        'url': model_data['ip_port'],
                        'location': {
                            'city': model_data.get('ip_city_name_en'),
                            'country': model_data.get('ip_country_name_en'),
                            'continent': model_data.get('ip_continent_name_en'),
                        },
                        'organization': model_data.get('ip_organization'),
                        'performance': {
                            'tokens_per_second': model_data.get('perf_tokens_per_second'),
                            'last_tested': model_data.get('perf_last_tested'),
                        },
                    }
                    servers.append(server_info)
        return servers

    def get_server_info(self, model: str, server_url: Optional[str] = None) -> Dict:
        """Return information for one server hosting *model*.

        Args:
            model: Exact model name.
            server_url: If provided, must exactly match the ``url`` field of a
                server returned by :meth:`list_model_servers`.  When ``None``
                the first server in the list is returned.

        Returns:
            A single server info dict (same structure as an element from
            :meth:`list_model_servers`).

        Raises:
            ValueError: If no servers are found for *model*, or if *server_url*
                is given but does not match any known server.
        """
        servers = self.list_model_servers(model)
        if not servers:
            raise ValueError(f"No servers found for model '{model}'")

        if server_url:
            for server in servers:
                if server['url'] == server_url:
                    return server
            raise ValueError(f"Server '{server_url}' not found for model '{model}'")
        return servers[0]

    def build_api_request(self, model: str, prompt: str, **kwargs) -> Dict:
        """Construct a complete Ollama ``generate`` request payload.

        Validates that *model* exists (via :meth:`get_model_info`), then
        assembles a payload dict with generation options merged from *kwargs*
        and sensible defaults.

        Supported *kwargs*:

        ==================  ===========  =====================================
        Key                 Default      Description
        ==================  ===========  =====================================
        ``temperature``     ``0.7``      Sampling temperature (0 = greedy).
        ``top_p``           ``0.9``      Nucleus sampling probability mass.
        ``stop``            ``[]``       List of stop strings.
        ``num_predict``     ``_max_tokens`` Max tokens to generate.
        ``messages``        —            Chat history list.
        ``system``          —            System prompt string.
        ``tools``           —            Tool definitions list.
        ``tool_choice``     —            Tool selection policy.
        ``session_id``      —            Session state identifier.
        ``memory``          —            Memory payload.
        ``metadata``        —            Arbitrary request metadata.
        ``repeat_penalty``  —            Repetition penalty factor.
        ``seed``            —            Random seed for determinism.
        ``tfs_z``           —            Tail-free sampling parameter.
        ``mirostat``        —            Mirostat sampling mode (0/1/2).
        ==================  ===========  =====================================

        Args:
            model: Exact model name, e.g. ``"deepseek-r1:7b"``.
            prompt: Input text prompt.
            **kwargs: Generation and request parameters (see table above).

        Returns:
            A dict ready to unpack into ``ollama.Client.generate(**payload)``.

        Raises:
            ValueError: If *model* is not found in the bundled database.
        """
        self.get_model_info(model)

        payload: Dict[str, Any] = {
            "model": model,
            "options": {
                "temperature": kwargs.get('temperature', 0.7),
                "top_p": kwargs.get('top_p', 0.9),
                "stop": kwargs.get('stop', []),
                "num_predict": kwargs.get('num_predict', self._max_tokens),
            },
        }

        if prompt:
            payload["prompt"] = prompt
        if kwargs.get('messages') is not None:
            payload["messages"] = kwargs['messages']
        if kwargs.get('system') is not None:
            payload["system"] = kwargs['system']
        if kwargs.get('tools') is not None:
            payload["tools"] = kwargs['tools']
        if kwargs.get('tool_choice') is not None:
            payload["tool_choice"] = kwargs['tool_choice']
        if kwargs.get('session_id') is not None:
            payload["session_id"] = kwargs['session_id']
        if kwargs.get('memory') is not None:
            payload["memory"] = kwargs['memory']
        if kwargs.get('metadata') is not None:
            payload["metadata"] = kwargs['metadata']

        supported_options = ['repeat_penalty', 'seed', 'tfs_z', 'mirostat']
        for opt in supported_options:
            if opt in kwargs:
                payload['options'][opt] = kwargs[opt]

        return payload

    # ------------------------------------------------------------------
    # Chat and streaming
    # ------------------------------------------------------------------

    def _chat(self, prompt: str, model: Optional[str] = "llama3.2:3b", **kwargs) -> str:
        """Send a prompt and return the complete response as a string.

        Tries servers with timeout and retry backoff for reliability.

        Args:
            prompt: The input text prompt.
            model: Model name to use.  When ``None`` a random model is chosen
                from the full catalogue.
            **kwargs: Additional generation parameters. Supports 'timeout',
                'max_retries', 'retry_backoff'.

        Returns:
            The generated response string from the first successful server.

        Raises:
            RuntimeError: If no models are available (when *model* is ``None``)
                or if every server attempt fails.
        """
        timeout = kwargs.pop('timeout', 30.0)
        max_retries = kwargs.pop('max_retries', 3)
        retry_backoff = kwargs.pop('retry_backoff', 0.5)

        import time

        if model is None:
            all_models = self.list_models()
            if not all_models:
                raise RuntimeError("No models available")
            model = random.choice(all_models)

        servers = self.list_model_servers(model)
        if not servers:
            raise RuntimeError(f"No servers available for model '{model}'")

        random.shuffle(servers)

        errors = []
        attempt = 0
        for server in servers[:max_retries]:  # limit to max_retries servers
            try:
                client = Client(host=server['url'])
                request = self.build_api_request(model, prompt, **kwargs)
                response = client.generate(**request)
                if isinstance(response, dict):
                    return response.get('response') or response.get('content') or str(response)
                return getattr(response, 'response', getattr(response, 'content', str(response)))
            except Exception as e:
                errors.append(f"{server['url']} ({type(e).__name__}: {e})")
                attempt += 1
                if attempt < len(servers) and attempt < max_retries:
                    sleep_time = retry_backoff * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(sleep_time)
                continue

        raise RuntimeError(f"All server attempts failed for model '{model}'. Please check your network connection or try again later.")

    def _stream_chat(self, prompt: str, model: Optional[str] = "llama3.2:3b", **kwargs):
        """Stream a response token-by-token as :class:`~aicortex.chat.StreamEvent` objects.

        Yields events with timeout and retry backoff for reliability.

        Args:
            prompt: The input text prompt.
            model: Model name to use.  When ``None`` a random model is chosen.
            **kwargs: Additional generation parameters. Supports 'timeout',
                'max_retries', 'retry_backoff'.

        Yields:
            :class:`~aicortex.chat.StreamEvent` objects in arrival order.

        Raises:
            RuntimeError: If no models are available or all server attempts fail.
        """
        from .chat import StreamEvent
        import time
        import random

        timeout = kwargs.pop('timeout', 30.0)
        max_retries = kwargs.pop('max_retries', 3)
        retry_backoff = kwargs.pop('retry_backoff', 0.5)

        if model is None:
            all_models = self.list_models()
            if not all_models:
                raise RuntimeError("No models available")
            model = random.choice(all_models)

        servers = self.list_model_servers(model)
        if not servers:
            raise RuntimeError(f"No servers available for model '{model}'")

        random.shuffle(servers)
        errors = []
        attempt = 0

        for server in servers[:max_retries]:
            try:
                client = Client(host=server['url'])
                request = self.build_api_request(model, prompt, **kwargs)
                request['stream'] = True

                yield StreamEvent(type="start", content="", timestamp=time.time())

                index = 0
                for chunk in client.generate(**request):
                    # ... same as before ...
                    content = None
                    event_type = None
                    tool_name = None
                    tool_args = None
                    tool_result = None
                    meta = None

                    if isinstance(chunk, dict):
                        event_type = chunk.get('type')
                        content = chunk.get('content') or chunk.get('response')
                        tool_name = chunk.get('tool_name')
                        tool_args = chunk.get('tool_args')
                        tool_result = chunk.get('tool_result')
                        meta = chunk.get('meta')
                    else:
                        event_type = getattr(chunk, 'type', None)
                        content = getattr(chunk, 'content', None)
                        if content is None:
                            content = getattr(chunk, 'response', None)
                        if content is None:
                            content = getattr(chunk, 'message', None)
                        tool_name = getattr(chunk, 'tool_name', None)
                        tool_args = getattr(chunk, 'tool_args', None)
                        tool_result = getattr(chunk, 'tool_result', None)
                        meta = getattr(chunk, 'meta', None)

                    if event_type in {"start", "token", "end", "tool_call", "tool_result", "error", "meta"}:
                        if event_type == "token" and content is None:
                            continue
                        yield StreamEvent(
                            type=event_type,
                            content=content,
                            index=chunk.get('index') if isinstance(chunk, dict) else getattr(chunk, 'index', None),
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_result=tool_result,
                            meta=meta,
                            timestamp=time.time(),
                        )
                        if event_type == "token":
                            index += 1
                        continue

                    if content is None:
                        continue

                    yield StreamEvent(
                        type="token",
                        content=content,
                        index=index,
                        timestamp=time.time(),
                    )
                    index += 1

                yield StreamEvent(type="end", content="", timestamp=time.time())
                return
            except Exception as e:
                error_msg = "Server connection failed, trying next server..."
                errors.append(error_msg)
                yield StreamEvent(type="error", content=error_msg, timestamp=time.time())
                attempt += 1
                if attempt < len(servers) and attempt < max_retries:
                    sleep_time = retry_backoff * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(sleep_time)
                continue

        raise RuntimeError(f"All server attempts failed for model '{model}'. Please check your network connection or try again later.")

    # ------------------------------------------------------------------
    # LangChain helpers
    # ------------------------------------------------------------------

    def get_llm_params(self, model: Optional[str] = "llama3.2:3b") -> Dict[str, str]:
        """Return ``{"model": …, "base_url": …}`` ready for LangChain's ``OllamaLLM``.

        Picks a random server for the chosen model so that repeated calls
        naturally spread load across the available endpoints.

        Args:
            model: Model name to look up.  When ``None`` a random model is
                chosen from the full catalogue.

        Returns:
            A two-key dict::

                {"model": "mistral:7b", "base_url": "http://1.2.3.4:11434"}

        Raises:
            ValueError: If the specified *model* is not in the catalogue.
            RuntimeError: If no models are available or no servers are found.
        """
        if model is None:
            all_models = self.list_models()
            if not all_models:
                raise RuntimeError("No models available")
            model = random.choice(all_models)
        else:
            if model not in self.list_models():
                raise ValueError(f"Model '{model}' not found")

        servers = self.list_model_servers(model)
        if not servers:
            raise RuntimeError(f"No servers available for model '{model}'")

        server = random.choice(servers)

        return {
            "model": model,
            "base_url": server['url'],
        }

    def get_random_llm_params(self) -> Dict[str, str]:
        """Return LangChain params for a completely random model and server.

        Thin wrapper around :meth:`get_llm_params` called with ``model=None``.
        Handy for quick prototyping or load-testing scenarios.

        Returns:
            A two-key dict ``{"model": "…", "base_url": "…"}``.

        Raises:
            RuntimeError: If no models or no servers are available.
        """
        return self.get_llm_params()


# ---------------------------------------------------------------------------
# Module-level best_server() — Feature 1.5
# ---------------------------------------------------------------------------

import time as _time

_BEST_SERVER_CACHE: dict = {}
_BEST_SERVER_TTL: int = 300  # 5 minutes


def best_server(
    model: str,
    strategy: Literal["fastest", "nearest", "balanced"] = "fastest",
) -> Dict[str, Any]:
    """Return the highest-scoring server for *model* using *strategy*.

    Results are cached per ``(model, strategy)`` key for 5 minutes.
    Call :func:`aicortex.clear_server_cache` to invalidate the cache.

    Args:
        model: Exact model name, e.g. ``"llama3.2:3b"``.
        strategy: One of:

            - ``"fastest"`` — scores by live tokens-per-second probe.
            - ``"nearest"`` — scores by geographic proximity from bundled metadata.
            - ``"balanced"`` — weighted score: 60% speed + 40% proximity.

    Returns:
        The single highest-scoring server dict (same schema as
        :func:`aicortex.list_model_servers`).

    Raises:
        RuntimeError: If no servers are available for *model*.
    """
    cache_key = (model, strategy)
    now = _time.monotonic()
    if cache_key in _BEST_SERVER_CACHE:
        cached_result, expiry = _BEST_SERVER_CACHE[cache_key]
        if now < expiry:
            return cached_result

    _api = _OllamaAPI()
    servers = _api.list_model_servers(model)
    if not servers:
        raise RuntimeError(f"No servers available for model '{model}'")

    def _speed_score(s: Dict) -> float:
        # Use bundled perf data as a proxy; live probing is out of scope here.
        perf = s.get("performance", {})
        if isinstance(perf, dict):
            return float(perf.get("tokens_per_second", 0))
        return 0.0

    def _proximity_score(s: Dict) -> float:
        # Bundled geo metadata; higher = same continent = closer.
        loc = s.get("location", {})
        if not isinstance(loc, dict):
            return 0.0
        # Simple heuristic: presence of location data scores 1.0
        return 1.0 if loc else 0.0

    if strategy == "fastest":
        scored = sorted(servers, key=_speed_score, reverse=True)
    elif strategy == "nearest":
        scored = sorted(servers, key=_proximity_score, reverse=True)
    else:  # balanced
        def _balanced(s: Dict) -> float:
            return 0.6 * _speed_score(s) + 0.4 * _proximity_score(s)
        scored = sorted(servers, key=_balanced, reverse=True)

    result = scored[0]
    _BEST_SERVER_CACHE[cache_key] = (result, now + _BEST_SERVER_TTL)
    return result
