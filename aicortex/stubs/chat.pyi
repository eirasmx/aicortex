from dataclasses import dataclass
from typing import Any, Iterator, Literal, Optional

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

    events: list[StreamEvent]

    def __iter__(self) -> Iterator[StreamEvent]:
        """Iterate over the stream events in order."""
        ...

    def add(self, event: StreamEvent) -> None:
        """Append a `StreamEvent` to the stream buffer."""
        ...

    def text(self) -> str:
        """Reconstruct the streamed text from token events only."""
        ...

