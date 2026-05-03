"""In-process server health and performance caches for AI Cortex.

Two dicts track server state across calls:

* :data:`_BAD_CACHE` — servers currently marked ``DEGRADED`` (cooldown period).
* :data:`_GOOD_CACHE` — servers with a known ``tokens_per_second`` score from a
  recent successful :func:`~aicortex.chat` call.

Neither cache is persisted — both reset on process restart, consistent with
:data:`~aicortex.session._SESSION_STORE`.

Use :func:`clear_server_cache` to flush all three caches at once (bad, good,
and the :func:`~aicortex.api.best_server` result cache).
"""

from __future__ import annotations

import os
import time
from typing import Dict

# ---------------------------------------------------------------------------
# Cache TTL
# ---------------------------------------------------------------------------

#: Bad-server cooldown in seconds.  Controlled by ``AICORTEX_CACHE_TTL`` env var.
CACHE_TTL: int = int(os.environ.get("AICORTEX_CACHE_TTL", "60"))

# ---------------------------------------------------------------------------
# Cache dicts
# ---------------------------------------------------------------------------

#: Maps server URL → monotonic expiry timestamp for DEGRADED servers.
_BAD_CACHE: Dict[str, float] = {}

#: Maps server URL → measured tokens_per_second from last successful call.
_GOOD_CACHE: Dict[str, float] = {}

#: Maps (model, strategy) → (result_dict, expiry_timestamp) for best_server().
_BEST_SERVER_CACHE: Dict[tuple, tuple] = {}

_BEST_SERVER_TTL: int = 300  # 5 minutes

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def mark_degraded(url: str) -> None:
    """Mark *url* as DEGRADED for :data:`CACHE_TTL` seconds.

    Also evicts *url* from :data:`_GOOD_CACHE` if present.
    """
    _BAD_CACHE[url] = time.monotonic() + CACHE_TTL
    _GOOD_CACHE.pop(url, None)


def mark_good(url: str, tps: float) -> None:
    """Record a successful call result for *url* with *tps* tokens-per-second."""
    _GOOD_CACHE[url] = tps
    _BAD_CACHE.pop(url, None)


def is_degraded(url: str) -> bool:
    """Return ``True`` if *url* is currently in the DEGRADED cooldown window."""
    expiry = _BAD_CACHE.get(url)
    if expiry is None:
        return False
    if time.monotonic() < expiry:
        return True
    # TTL expired — silently re-enter pool
    del _BAD_CACHE[url]
    return False


def sort_servers(servers: list) -> list:
    """Return *servers* sorted so proven-fast servers come first.

    Ordering:

    1. Servers in :data:`_GOOD_CACHE`, sorted by ``tps`` descending.
    2. Unknown servers (no entry in either cache), in original order.
    3. DEGRADED servers are excluded entirely.
    """
    good, unknown = [], []
    for s in servers:
        url = s.get("url", "")
        if is_degraded(url):
            continue
        if url in _GOOD_CACHE:
            good.append((s, _GOOD_CACHE[url]))
        else:
            unknown.append(s)
    good.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in good] + unknown


def clear_server_cache() -> None:
    """Flush :data:`_BAD_CACHE`, :data:`_GOOD_CACHE`, and the best_server cache.

    All three caches reset to empty dicts.  The next :func:`~aicortex.chat`
    call will start fresh with a fully shuffled server pool.
    """
    _BAD_CACHE.clear()
    _GOOD_CACHE.clear()
    _BEST_SERVER_CACHE.clear()
