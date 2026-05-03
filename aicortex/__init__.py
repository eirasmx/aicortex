"""🧠 AI Cortex — The unified Python toolkit for accessing any LLM through Ollama.

Zero API keys. Zero signup. Completely free.

This package provides a clean, type-safe interface to hundreds of language models
(Llama, Mistral, Gemma, DeepSeek, Qwen, and more) served locally or remotely via
`Ollama <https://ollama.com>`_.

Quickstart::

    from aicortex import chat

    # One-liner: pick a model, get a response
    response = chat("Explain neural networks like I'm five.")
    print(response)

    # Streaming
    for event in chat("Write a haiku about AI.", stream=True):
        if event.type == "token":
            print(event.content, end="", flush=True)

Public API summary:

- :func:`chat` — Send a prompt; get a string or a :class:`~aicortex.chat.Stream`.
- :func:`families` — List available model families (``llama``, ``mistral``, …).
- :func:`models` — List model names, optionally filtered by family.
- :func:`get_model_info` — Full metadata dict for a specific model.
- :func:`list_model_servers` — All Ollama servers hosting a given model.
- :func:`get_server_info` — Info for one specific server / model combination.
- :func:`build_api_request` — Build a raw Ollama request payload.
- :func:`get_llm_params` — ``{"model": …, "base_url": …}`` ready for LangChain.
- :func:`get_random_llm_params` — Same as above but with a random model.
"""

from typing import Any, Dict, List, Optional
from . import tools
from .api import _OllamaAPI, best_server
from .cache import clear_server_cache
from .chat import Stream, StreamEvent, chat
from .session import Session

_client = _OllamaAPI()

__all__ = [
    'chat',
    'Stream',
    'StreamEvent',
    'Session',
    'best_server',
    'clear_server_cache',
    'families',
    'models',
    'get_model_info',
    'list_model_servers',
    'get_server_info',
    'build_api_request',
    'get_llm_params',
    'get_random_llm_params',
    'tools',
]

__version__ = "1.0.3"


def families() -> List[str]:
    """Return the names of all available model families.

    Family names are derived solely from the JSON filenames bundled with the
    package (e.g. ``llama.json`` → ``"llama"``).  The list grows automatically
    when new family files are added to the ``aicortex/models/`` directory.

    Returns:
        A list of lowercase family name strings, e.g.
        ``['deepseek', 'gemma', 'llama', 'mistral', 'qwen']``.

    Example::

        >>> from aicortex import families
        >>> print(families())
        ['deepseek', 'gemma', 'llama', 'mistral', 'qwen']
    """
    return _client.list_families()


def models(family: Optional[str] = None) -> List[str]:
    """Return available model names, optionally filtered by family.

    When *family* is ``None`` every model from every family is returned as a
    flat list.  When a family name is given only that family's models are
    returned (case-insensitive match).

    Args:
        family: Optional family name to filter by (e.g. ``"llama"``).
            Pass ``None`` (default) to return all models.

    Returns:
        A list of model name strings such as ``["llama3.2:3b", "llama3.1:8b"]``.
        Returns an empty list if the family is not found.

    Example::

        >>> from aicortex import models
        >>> print(models("mistral"))
        ['mistral:7b', 'mistral-nemo:12b', ...]

        >>> all_models = models()   # every model across all families
        >>> len(all_models)
        347
    """
    return _client.list_models(family)


def get_model_info(model: str) -> Dict[str, Any]:
    """Return the full metadata dictionary for a specific model.

    Metadata fields typically include ``parameter_size``, ``quantization_level``,
    ``format``, ``family``, ``ip_port``, geographic location fields
    (``ip_city_name_en``, ``ip_country_name_en``, …), and performance stats
    (``perf_tokens_per_second``).

    Note:
        The ``digest`` and ``perf_response_text`` fields are stripped at load
        time to keep the returned dict lightweight.

    Args:
        model: Exact model name as it appears in :func:`models`, e.g.
            ``"llama3.2:3b"``.

    Returns:
        A dictionary of model metadata.

    Raises:
        ValueError: If *model* is not found in the bundled model database.

    Example::

        >>> from aicortex import get_model_info
        >>> info = get_model_info("llama3.2:3b")
        >>> print(info['parameter_size'], info['quantization_level'])
        3B Q4_K_M
    """
    return _client.get_model_info(model)


def list_model_servers(model: str) -> List[Dict[str, Any]]:
    """Return all known Ollama servers that host a specific model.

    Each entry in the returned list contains the server URL, geographic
    location details, organisation name, and latest performance metrics.

    Args:
        model: Exact model name, e.g. ``"mistral:7b"``.

    Returns:
        A list of server dictionaries with the following structure::

            {
                "url":          "http://1.2.3.4:11434",
                "location": {
                    "city":      "Frankfurt",
                    "country":   "Germany",
                    "continent": "Europe"
                },
                "organization": "Hetzner Online GmbH",
                "performance": {
                    "tokens_per_second": 42.3,
                    "last_tested":       "2024-11-01T12:00:00Z"
                }
            }

        Returns an empty list if no servers are found for the model.

    Example::

        >>> from aicortex import list_model_servers
        >>> for s in list_model_servers("llama3.2:3b"):
        ...     print(s['url'], "—", s['location']['city'])
    """
    return _client.list_model_servers(model)


def get_server_info(model: str, server_url: Optional[str] = None) -> Dict[str, Any]:
    """Return information about a specific server hosting a model.

    When *server_url* is omitted the first available server is returned.
    Use :func:`list_model_servers` first if you want to browse all options.

    Args:
        model: Exact model name, e.g. ``"gemma3:12b"``.
        server_url: Optional full endpoint URL (must match an entry returned by
            :func:`list_model_servers`).  If ``None``, the first server is used.

    Returns:
        A single server dict (same schema as each element from
        :func:`list_model_servers`).

    Raises:
        ValueError: If no servers are found for *model*, or if *server_url* is
            specified but does not match any known server for that model.

    Example::

        >>> from aicortex import get_server_info
        >>> info = get_server_info("mistral:7b")
        >>> print(info['location']['country'])
        Germany
    """
    return _client.get_server_info(model, server_url)


def build_api_request(model: str, prompt: str, **kwargs: Any) -> Dict[str, Any]:
    """Build a raw Ollama API request payload for a given model and prompt.

    Useful when you need fine-grained control over the request or want to
    inspect the payload before sending it yourself.  The function validates
    that *model* exists in the database before constructing the payload.

    Args:
        model: Exact model name, e.g. ``"deepseek-r1:7b"``.
        prompt: The input text prompt.
        **kwargs: Optional generation parameters:

            - ``temperature`` (float, default ``0.7``) — sampling temperature.
            - ``top_p`` (float, default ``0.9``) — nucleus sampling threshold.
            - ``stop`` (list[str], default ``[]``) — stop sequences.
            - ``num_predict`` (int) — max tokens to generate.
            - ``messages`` (list) — chat-style message history.
            - ``system`` (str) — system prompt.
            - ``tools`` / ``tool_choice`` — tool-calling configuration.
            - ``session_id``, ``memory``, ``metadata`` — session state fields.
            - ``repeat_penalty``, ``seed``, ``tfs_z``, ``mirostat`` — advanced
              Ollama sampler options.

    Returns:
        A dictionary ready to be passed to ``ollama.Client.generate(**payload)``.

    Raises:
        ValueError: If *model* is not found in the bundled model database.

    Example::

        >>> from aicortex import build_api_request
        >>> payload = build_api_request("llama3.2:3b", "Hello!", temperature=0.5)
        >>> print(payload['options']['temperature'])
        0.5
    """
    return _client.build_api_request(model, prompt, **kwargs)


def get_llm_params(model: Optional[str] = None) -> Dict[str, str]:
    """Return ``model`` and ``base_url`` parameters ready for LangChain's ``OllamaLLM``.

    Selects a random available server for the given model (or a random model
    when *model* is ``None``).  The returned dict can be unpacked directly into
    ``OllamaLLM(**get_llm_params("mistral:7b"))``.

    Args:
        model: Exact model name to use.  Pass ``None`` to pick a random model
            from the full catalogue.

    Returns:
        A dict with exactly two keys::

            {"model": "mistral:7b", "base_url": "http://1.2.3.4:11434"}

    Raises:
        ValueError: If the specified *model* is not found.
        RuntimeError: If no models or no servers are available.

    Example::

        >>> from aicortex import get_llm_params
        >>> from langchain_community.llms import Ollama
        >>> llm = Ollama(**get_llm_params("mistral:7b"))
    """
    return _client.get_llm_params(model)


def get_random_llm_params() -> Dict[str, str]:
    """Return ``model`` and ``base_url`` for a randomly selected model and server.

    Convenience wrapper around :func:`get_llm_params` with no arguments.
    Useful for load-spreading, testing, or exploratory tasks where the exact
    model does not matter.

    Returns:
        A dict with exactly two keys::

            {"model": "<random-model>", "base_url": "http://<random-server>"}

    Raises:
        RuntimeError: If no models or no servers are available.

    Example::

        >>> from aicortex import get_random_llm_params
        >>> params = get_random_llm_params()
        >>> print(params['model'])
        qwen2.5:7b
    """
    return _client.get_random_llm_params()
