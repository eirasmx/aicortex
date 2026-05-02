from typing import Any, Dict, List, Optional
from .chat import Stream, StreamEvent

__all__ = [
    'chat',
    'Stream',
    'StreamEvent',
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


def chat(
    prompt: str,
    *,
    model: str = "gpt-oss:20b",
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    top_p: float = 1.0,
    stop: list[str] | None = None,
) -> str | Stream:
    """Send a prompt to an Ollama model and return the response.

    This function supports both synchronous generation and streaming output.

    Args:
        prompt: The input text prompt for the model.
        model: The model name to use (defaults to 'gpt-oss:20b').
        stream: Whether to return streaming events.
        temperature: Sampling temperature.
        max_tokens: Maximum generated tokens.
        top_p: Nucleus sampling threshold.
        stop: Optional stop sequences.

    Returns:
        The text result when ``stream`` is False, or a ``Stream`` object when
        ``stream`` is True.
    """


def families() -> List[str]:
    """Return all available model families from the package metadata."""


def models(family: Optional[str] = None) -> List[str]:
    """Return available model names, optionally filtered by family."""


def get_model_info(model: str) -> Dict[str, Any]:
    ...


def list_model_servers(model: str) -> List[Dict[str, Any]]:
    ...


def get_server_info(model: str, server_url: Optional[str] = None) -> Dict[str, Any]:
    ...


def build_api_request(model: str, prompt: str, **kwargs: Any) -> Dict[str, Any]:
    ...


def get_llm_params(model: Optional[str] = None) -> Dict[str, str]:
    ...


def get_random_llm_params() -> Dict[str, str]:
    ...


tools: Any  # Module for utility functions
        memory: Whether to enable memory features.
        metadata: Additional request metadata.

    Returns:
        Response text, or a `Stream` when `stream=True`.

    Example:
        >>> from aicortex import chat
        >>> response = chat('Hello world', stream=False)
        >>> print(response)
    """
    ...


def families() -> List[str]:
    """Return all available model families from the local metadata.

    Example:
        >>> from aicortex import families
        >>> print(families())
    """
    ...


def models(family: Optional[str] = None) -> List[str]:
    """Return model names available in the package.

    If a family name is supplied, only models in that family are returned.

    Example:
        >>> from aicortex import models
        >>> print(models())
        >>> print(models('llama'))
    """
    ...


def get_model_info(model: str) -> Dict[str, Any]:
    """Return metadata for a specific model.

    Example:
        >>> from aicortex import get_model_info
        >>> info = get_model_info('llama3.2:3b')
        >>> print(info['description'])
    """
    ...


def list_model_servers(model: str) -> List[Dict[str, Any]]:
    """Return the list of servers hosting the given model.

    Example:
        >>> from aicortex import list_model_servers
        >>> servers = list_model_servers('llama3.2:3b')
        >>> print(servers[0]['url'])
    """
    ...


def get_server_info(model: str, server_url: Optional[str] = None) -> Dict[str, Any]:
    """Return metadata for a specific server hosting a model.

    Example:
        >>> from aicortex import get_server_info
        >>> info = get_server_info('llama3.2:3b')
        >>> print(info['location'])
    """
    ...


def build_api_request(model: str, prompt: str, **kwargs: Any) -> Dict[str, Any]:
    """Build the raw request payload for the Ollama backend.

    Example:
        >>> from aicortex import build_api_request
        >>> payload = build_api_request('llama3.2:3b', 'Hello')
        >>> print(payload['options']['temperature'])
    """
    ...


def get_llm_params(model: Optional[str] = None) -> Dict[str, str]:
    """Return a model and base URL for use with an Ollama-style LLM client.

    Example:
        >>> from aicortex import get_llm_params
        >>> params = get_llm_params('llama3.2:3b')
        >>> print(params['base_url'])
    """
    ...


def get_random_llm_params() -> Dict[str, str]:
    """Return a random model/server pair for OllamaLLM integration.

    Example:
        >>> from aicortex import get_random_llm_params
        >>> params = get_random_llm_params()
        >>> print(params['model'])
    """
    ...
