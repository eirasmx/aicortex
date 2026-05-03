"""Multi-turn session management for AI Cortex.

This module provides the :class:`Session` class and the in-process
``_SESSION_STORE`` dict that backs it.  Sessions are lightweight identity
tokens — they hold no model state, only the conversation history that
:func:`aicortex.chat` prepends to each request when a session is active.

Typical usage::

    from aicortex import chat, Session

    session = Session()
    chat("My name is Alice.", session=session)
    response = chat("What is my name?", session=session)
    print(response)  # → "Your name is Alice."

Sessions are in-process only.  History is lost on process restart.
"""

from __future__ import annotations

import uuid
from typing import List, Dict

# ---------------------------------------------------------------------------
# In-process store
# ---------------------------------------------------------------------------

#: Maps session id → list of {"role": str, "content": str} in order.
_SESSION_STORE: Dict[str, List[Dict[str, str]]] = {}


# ---------------------------------------------------------------------------
# Session class
# ---------------------------------------------------------------------------

class Session:
    """A lightweight multi-turn conversation identity token.

    A :class:`Session` wraps a string id and provides read-only access to the
    conversation history stored in the module-level :data:`_SESSION_STORE`.

    Lifecycle::

        session = Session()           # auto-id; empty history registered
        session = Session(id="abc")   # reuse existing session
        Session(id="missing")         # raises KeyError — id not found

    Args:
        id: Optional session identifier.  When ``None`` (default) a short
            UUID4 string is generated automatically and an empty history list
            is registered in :data:`_SESSION_STORE`.  When supplied, the id
            **must** already exist in the store — use this to resume a
            previous session within the same process.

    Raises:
        KeyError: If *id* is supplied but does not exist in :data:`_SESSION_STORE`.
    """

    def __init__(self, id: str | None = None) -> None:
        if id is None:
            # Auto-generate a short unique id and register empty history.
            generated = uuid.uuid4().hex[:8]
            _SESSION_STORE[generated] = []
            self._id = generated
        else:
            if id not in _SESSION_STORE:
                raise KeyError(
                    f"No session with id '{id}' found. "
                    f"Create one with Session(id='{id}')"
                )
            self._id = id

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """The session's unique identifier string.

        This property is read-only — assigning to it raises :exc:`AttributeError`.
        """
        return self._id

    @id.setter
    def id(self, value):  # type: ignore[override]
        raise AttributeError("Session.id is read-only")

    @property
    def history(self) -> List[Dict[str, str]]:
        """A copy of the conversation history for this session.

        Returns a **copy** (not a reference) of the internal list so that
        callers cannot accidentally mutate the store.

        Returns:
            List of ``{"role": str, "content": str}`` dicts in chronological order.
        """
        return list(_SESSION_STORE[self._id])

    @history.setter
    def history(self, value):  # type: ignore[override]
        raise AttributeError("Session.history is read-only")

    # ------------------------------------------------------------------
    # Mutating methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear the session history without removing the id from the store.

        After calling ``reset()`` the session id remains valid and the history
        list is empty.  Any subsequent :func:`~aicortex.chat` calls with this
        session will start fresh.
        """
        _SESSION_STORE[self._id] = []

    def delete(self) -> None:
        """Remove this session from the store entirely.

        The instance becomes invalid after this call — any further use of the
        session object will produce a :exc:`KeyError` because the id no longer
        exists in :data:`_SESSION_STORE`.
        """
        _SESSION_STORE.pop(self._id, None)

    def __repr__(self) -> str:
        turns = len(_SESSION_STORE.get(self._id, []))
        return f"Session(id={self._id!r}, turns={turns})"
