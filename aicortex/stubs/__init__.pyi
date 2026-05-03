from typing import Any, Coroutine, Dict, List, Literal, Optional, Union
from .chat import Stream, StreamEvent
from .session import Session

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


def chat(
    prompt: str,
    *,
    model: str = "gpt-oss:20b",
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    top_p: float = 1.0,
    stop: list[str] | None = None,
    session: Session | str | None = None,
    system: str | None = None,
    response_format: Literal["text", "json"] = "text",
    schema: dict | None = None,
    routing: Literal["random", "fastest", "nearest"] = "random",
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_backoff: float = 0.5,
    persona: str | None = None,
) -> str | dict | Stream | Coroutine[Any, Any, str | dict | Stream]:
    """Send a prompt to an Ollama model and return the response.

    Returns ``str``, ``dict``, or :class:`Stream` in sync mode;
    returns a coroutine in async mode (when called inside a running event loop).
    """


def best_server(
    model: str,
    strategy: Literal["fastest", "nearest", "balanced"] = "fastest",
) -> Dict[str, Any]:
    """Return the highest-scoring server for *model* using *strategy*."""


def clear_server_cache() -> None:
    """Flush the bad-server, good-server, and best_server caches."""


def families() -> List[str]:
    """Return all available model families from the package metadata."""


def models(family: Optional[str] = None) -> List[str]:
    """Return available model names, optionally filtered by family."""


def get_model_info(model: str) -> Dict[str, Any]: ...

def list_model_servers(model: str) -> List[Dict[str, Any]]: ...

def get_server_info(
    model: str,
    server_url: Optional[str] = None,
) -> Dict[str, Any]: ...

def build_api_request(model: str, prompt: str, **kwargs: Any) -> Dict[str, Any]: ...

def get_llm_params(model: Optional[str] = None) -> Dict[str, str]: ...

def get_random_llm_params() -> Dict[str, str]: ...
