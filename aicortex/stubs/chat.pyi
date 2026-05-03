from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, List, Literal, Optional, Union

from .session import Session  # type: ignore[attr-defined]

EventType = Literal[
    'start',
    'token',
    'end',
    'tool_call',
    'tool_result',
    'error',
    'meta',
]


@dataclass
class StreamEvent:
    """A typed event emitted while streaming model output."""
    type: EventType
    content: Optional[str]
    index: Optional[int]
    tool_name: Optional[str]
    tool_args: Optional[dict]
    tool_result: Any
    meta: Optional[dict]
    timestamp: Optional[float]

    def __repr__(self) -> str: ...


class Stream:
    """A stream container for ordered `StreamEvent` objects."""

    events: List[StreamEvent]

    def __iter__(self) -> Iterator[StreamEvent]: ...
    def __aiter__(self) -> AsyncIterator[StreamEvent]: ...
    def add(self, event: StreamEvent) -> None: ...
    def text(self) -> str: ...
