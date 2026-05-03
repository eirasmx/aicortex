"""High-level chat interface for AI Cortex.

This module exposes three public objects:

- :func:`chat` — the primary entry point for sending prompts to any Ollama model.
- :class:`Stream` — a lightweight container that collects :class:`StreamEvent`
  objects and exposes a convenience :meth:`Stream.text` accessor.
- :class:`StreamEvent` — a typed dataclass representing a single event in the
  token stream.

New in 1.0.3:

- **Session support** — pass ``session=`` for multi-turn memory.
- **Async support** — ``chat()`` detects a running event loop and returns a
  coroutine automatically; no separate function needed.
- **JSON mode** — ``response_format="json"`` returns a parsed ``dict``.
- **System prompt** — ``system=`` forwarded directly to the model.
- **Smart routing** — ``routing="fastest"|"nearest"`` selects the best server.

Typical usage::

    from aicortex import chat, Session

    # Non-streaming
    response = chat("What is the speed of light?")
    print(response)

    # Streaming
    stream = chat("Write a haiku about the sea.", stream=True)
    for event in stream:
        if event.type == "token":
            print(event.content, end="", flush=True)

    # Multi-turn session
    session = Session()
    chat("My name is Alice.", session=session)
    print(chat("What is my name?", session=session))

    # Async (inside an event loop)
    response = await chat("Hello!", model="llama3.2:3b")

    # JSON mode
    data = chat("Return today's date as JSON.", response_format="json")
    print(data["date"])
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Literal, Optional, Union

from .api import _OllamaAPI
from .session import Session, _SESSION_STORE

_client = _OllamaAPI()

#: Union of all valid ``StreamEvent.type`` values.
EventType = Literal[
    "start",
    "token",
    "end",
    "tool_call",
    "tool_result",
    "error",
    "meta",
]


@dataclass
class StreamEvent:
    """A single event emitted during a streaming generation."""

    type: EventType
    content: Optional[str] = None
    index: Optional[int] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Any = None
    meta: Optional[dict] = None
    timestamp: Optional[float] = None


class _AsyncIteratorWrapper:
    """Wraps a sync iterator so it can be used with ``async for``."""

    def __init__(self, it: Iterator):
        self._it = it

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class Stream:
    """An ordered collection of :class:`StreamEvent` objects from a single generation."""

    def __init__(self):
        self.events: List[StreamEvent] = []

    def add(self, event: StreamEvent):
        self.events.append(event)

    def __iter__(self) -> Iterator[StreamEvent]:
        return iter(self.events)

    def __aiter__(self):
        return _AsyncIteratorWrapper(iter(self.events))

    def text(self) -> str:
        """Return all token content concatenated into a single string."""
        return "".join(
            e.content or ""
            for e in self.events
            if e.type == "token"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_session_id(session: Union[Session, str, None]) -> Optional[str]:
    if session is None:
        return None
    sid = session.id if isinstance(session, Session) else session
    if sid not in _SESSION_STORE:
        raise KeyError(
            f"No session with id '{sid}' found. "
            f"Create one with Session(id='{sid}')"
        )
    return sid


def _build_kwargs(
    temperature: float,
    top_p: float,
    max_tokens: Optional[int],
    stop: Optional[List[str]],
    system: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"temperature": temperature, "top_p": top_p}
    if max_tokens is not None:
        kwargs["num_predict"] = max_tokens
    if stop is not None:
        kwargs["stop"] = stop
    if system is not None:
        kwargs["system"] = system
    if session_id is not None:
        kwargs["messages"] = list(_SESSION_STORE[session_id])
    return kwargs


def _pick_server_url(model: str, routing: str) -> Optional[str]:
    if routing == "random":
        return None
    try:
        from .api import best_server as _best_server
        server = _best_server(model, strategy=routing)
        return server.get("url")
    except Exception:
        return None


def _sync_chat(
    prompt: str,
    model: str,
    stream: bool,
    session_id: Optional[str],
    response_format: str,
    routing: str,
    timeout: float,
    max_retries: int,
    retry_backoff: float,
    kwargs: Dict[str, Any],
) -> Union[str, dict, Stream]:
    preferred_url = _pick_server_url(model, routing)
    if preferred_url:
        kwargs["_preferred_server_url"] = preferred_url

    if stream:
        stream_obj = Stream()
        for event in _client._stream_chat(prompt, model, timeout=timeout, max_retries=max_retries, retry_backoff=retry_backoff, **kwargs):
            stream_obj.add(event)
        if session_id is not None:
            text = stream_obj.text()
            if text:
                _SESSION_STORE[session_id].append({"role": "user", "content": prompt})
                _SESSION_STORE[session_id].append({"role": "assistant", "content": text})
        return stream_obj

    raw = _client._chat(prompt, model, timeout=timeout, max_retries=max_retries, retry_backoff=retry_backoff, **kwargs)

    if session_id is not None:
        _SESSION_STORE[session_id].append({"role": "user", "content": prompt})
        _SESSION_STORE[session_id].append({"role": "assistant", "content": raw})

    if response_format == "json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError(f"Model returned non-JSON: {raw}")

    return raw


async def _async_chat(
    prompt: str,
    model: str,
    stream: bool,
    session_id: Optional[str],
    response_format: str,
    routing: str,
    timeout: float,
    max_retries: int,
    retry_backoff: float,
    kwargs: Dict[str, Any],
) -> Union[str, dict, Stream]:
    import functools
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        functools.partial(
            _sync_chat,
            prompt, model, stream, session_id, response_format, routing, timeout, max_retries, retry_backoff, kwargs,
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat(
    prompt: str,
    *,
    model: str = "gpt-oss:20b",
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
    stop: Optional[List[str]] = None,
    session: Union[Session, str, None] = None,
    system: Optional[str] = None,
    response_format: Literal["text", "json"] = "text",
    schema: Optional[dict] = None,
    routing: Literal["random", "fastest", "nearest"] = "random",
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_backoff: float = 0.5,
    persona: Optional[str] = None,
) -> Union[str, dict, Stream]:
    """Send a prompt to an Ollama model and return the response.

    Args:
        prompt: The input text to send to the model.
        model: Ollama model name.  Defaults to ``"gpt-oss:20b"``.
        stream: Return a :class:`Stream` when ``True``; plain ``str`` when ``False``.
        temperature: Sampling temperature (0.0 = deterministic).  Default 0.7.
        max_tokens: Max tokens to generate.  ``None`` uses server default.
        top_p: Nucleus sampling threshold.  Default 1.0 (disabled).
        stop: Strings that halt generation when encountered.
        session: :class:`Session` object or raw id string for multi-turn memory.
        system: System prompt for this call only (not stored in session history).
        response_format: ``"text"`` (default) or ``"json"`` (returns parsed dict).
        schema: JSON Schema dict to validate the parsed response (requires jsonschema).
        routing: Server selection — ``"random"`` (default), ``"fastest"``, ``"nearest"``.
        timeout: Seconds before abandoning a single server attempt. Default 30.0.
        max_retries: Max total server attempts (including first). Default 3.
        retry_backoff: Base seconds for exponential backoff. Default 0.5.
        persona: Reserved for Section 8.  Conflicts with ``system``.

    Returns:
        ``str``, ``dict``, or :class:`Stream` depending on arguments.

    Raises:
        ValueError: On invalid argument combinations.
        KeyError: If session id is not found in the store.
        RuntimeError: If all server attempts fail.
    """
    # Guard: system + persona conflict
    if system is not None and persona is not None:
        raise ValueError("Cannot pass both 'system' and 'persona' — use one or the other")

    # Guard: json + stream conflict
    if response_format == "json" and stream:
        raise ValueError("response_format='json' cannot be combined with stream=True")

    # Inject JSON instruction into system prompt
    effective_system = system
    if response_format == "json":
        json_instruction = "Respond only with valid JSON. No prose, no markdown."
        effective_system = f"{system}\n{json_instruction}" if system else json_instruction

    # Resolve session
    session_id = _resolve_session_id(session)

    # Build kwargs
    kwargs = _build_kwargs(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stop=stop,
        system=effective_system,
        session_id=session_id,
    )

    # Detect running event loop — return coroutine if inside one
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        return _async_chat(prompt, model, stream, session_id, response_format, routing, timeout, max_retries, retry_backoff, kwargs)

    result = _sync_chat(prompt, model, stream, session_id, response_format, routing, timeout, max_retries, retry_backoff, kwargs)

    # Schema validation
    if schema is not None and isinstance(result, dict):
        try:
            import jsonschema  # type: ignore
        except ImportError:
            raise ImportError(
                "The 'jsonschema' package is required for schema validation. "
                "Install it with: pip install jsonschema"
            )
        jsonschema.validate(result, schema)

    return result
