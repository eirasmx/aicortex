"""High-level chat interface for AI Cortex.

This module exposes three public objects:

- :func:`chat` — the primary entry point for sending prompts to any Ollama model.
- :class:`Stream` — a lightweight container that collects :class:`StreamEvent`
  objects and exposes a convenience :meth:`Stream.text` accessor.
- :class:`StreamEvent` — a typed dataclass representing a single event in the
  token stream.

Typical usage::

    from aicortex import chat

    # ── Non-streaming (returns a plain string) ──────────────────────────────
    response = chat("What is the speed of light?")
    print(response)

    # ── Streaming (returns a Stream object) ─────────────────────────────────
    stream = chat("Write a haiku about the sea.", stream=True)
    for event in stream:
        if event.type == "token":
            print(event.content, end="", flush=True)

    # Full text from a completed stream
    print(stream.text())
"""

from dataclasses import dataclass
from typing import Iterator, Literal, Any, Optional
from .api import _OllamaAPI

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
    """A single event emitted during a streaming generation.

    Every event has a ``type`` that identifies its role in the stream
    lifecycle.  Most fields are optional and only populated for the event
    types that need them.

    Lifecycle events (always emitted):

    - ``"start"`` — fired once before any tokens arrive.
    - ``"token"`` — fired for each generated token piece; ``content``
      holds the text fragment, ``index`` is its 0-based position.
    - ``"end"`` — fired once after the last token when generation succeeds.
    - ``"error"`` — fired when a server attempt fails; ``content`` contains
      the error message.

    Tool-calling events (emitted by models that support function calls):

    - ``"tool_call"`` — the model has decided to invoke a tool; populated
      fields are ``tool_name`` and ``tool_args``.
    - ``"tool_result"`` — the result of a tool call; ``tool_result`` holds
      the payload.

    Metadata events:

    - ``"meta"`` — optional diagnostic or provider-specific payload stored
      in ``meta``.

    Attributes:
        type: One of the ``EventType`` literals above.
        content: Text content for ``token`` and ``error`` events.
        index: 0-based token position within the stream (``token`` events only).
        tool_name: Name of the tool being invoked (``tool_call`` events only).
        tool_args: Arguments dict for the tool call (``tool_call`` events only).
        tool_result: Return value from a completed tool call
            (``tool_result`` events only).
        meta: Arbitrary key/value metadata from the provider
            (``meta`` events only).
        timestamp: Unix timestamp (seconds) recorded when the event was
            created; useful for latency measurements.

    Example::

        for event in chat("Hello!", stream=True):
            if event.type == "token":
                print(event.content, end="", flush=True)
            elif event.type == "error":
                print(f"\\nServer error: {event.content}")
    """

    type: EventType
    content: Optional[str] = None
    index: Optional[int] = None

    # Tool-calling fields
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Any = None

    # Metadata / diagnostics
    meta: Optional[dict] = None

    # Timing / tracing
    timestamp: Optional[float] = None


class Stream:
    """An ordered collection of :class:`StreamEvent` objects from a single generation.

    :class:`Stream` is returned by :func:`chat` when ``stream=True``.  The
    stream is **eagerly collected** — all events are buffered in memory before
    the object is returned, so iteration is always safe to repeat.

    Attributes:
        events: The underlying list of :class:`StreamEvent` objects in
            arrival order.

    Example::

        stream = chat("Summarise the Iliad in three sentences.", stream=True)

        # Iterate events
        for event in stream:
            if event.type == "token":
                print(event.content, end="", flush=True)

        # Or just get the full text in one go
        print(stream.text())
    """

    def __init__(self):
        """Initialise an empty stream container."""
        self.events: list[StreamEvent] = []

    def add(self, event: StreamEvent):
        """Append a single :class:`StreamEvent` to the internal buffer.

        This method is called internally by :func:`chat` and should not
        normally be needed by consumers.

        Args:
            event: The event to append.
        """
        self.events.append(event)

    def __iter__(self):
        """Iterate over all buffered events in arrival order.

        Returns:
            An iterator over :class:`StreamEvent` objects.
        """
        return iter(self.events)

    def text(self) -> str:
        """Concatenate all ``token`` event contents into a single string.

        Ignores ``start``, ``end``, ``error``, and other non-token events,
        so the result is the clean generated text with no artefacts.

        Returns:
            The complete generated text as a single string.

        Example::

            stream = chat("What is 2 + 2?", stream=True)
            print(stream.text())  # "4"
        """
        return "".join(
            e.content or ""
            for e in self.events
            if e.type == "token"
        )


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

    This is AI Cortex's primary entry point.  It handles server selection,
    automatic failover, and both blocking and streaming generation modes.

    Args:
        prompt: The input text to send to the model.
        model: Ollama model name to use.  Defaults to ``"gpt-oss:20b"``.
            Use :func:`aicortex.models` to browse available options.
        stream: When ``True``, collect token events and return a
            :class:`Stream` object.  When ``False`` (default), block until
            generation is complete and return the response as a plain string.
        temperature: Sampling temperature controlling output randomness.
            ``0.0`` is fully deterministic (greedy); higher values (up to
            ``~2.0``) increase diversity.  Defaults to ``0.7``.
        max_tokens: Maximum number of tokens to generate.  When ``None``
            (default) the server-side default is used.
        top_p: Nucleus sampling threshold.  Only tokens whose cumulative
            probability reaches *top_p* are considered.  Defaults to ``1.0``
            (disabled).
        stop: Optional list of strings that halt generation when encountered
            in the output.

    Returns:
        - A plain ``str`` when ``stream=False``.
        - A :class:`Stream` object when ``stream=True``.  Iterate it to
          access individual :class:`StreamEvent` objects, or call
          :meth:`Stream.text` for the full concatenated text.

    Raises:
        RuntimeError: If no servers are available for the requested model,
            or if all server attempts fail.

    Examples::

        # Non-streaming — simplest form
        answer = chat("What is the boiling point of water?")
        print(answer)

        # Custom model and deterministic output
        code = chat(
            "Write a Python function to reverse a string.",
            model="llama3.2:3b",
            temperature=0.0,
            max_tokens=200,
        )
        print(code)

        # Streaming — print tokens as they arrive
        stream = chat("Tell me a short bedtime story.", stream=True)
        for event in stream:
            if event.type == "token":
                print(event.content, end="", flush=True)
        print()  # newline after stream ends
    """
    kwargs: dict[str, Any] = {
        'temperature': temperature,
        'top_p': top_p,
    }
    if max_tokens is not None:
        kwargs['num_predict'] = max_tokens
    if stop is not None:
        kwargs['stop'] = stop

    if stream:
        stream_obj = Stream()
        for event in _client._stream_chat(prompt, model, **kwargs):
            stream_obj.add(event)
        return stream_obj
    else:
        return _client._chat(prompt, model, **kwargs)
