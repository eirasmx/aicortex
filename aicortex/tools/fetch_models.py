"""Step 2 of the model refresh pipeline: model data retrieval.

This module queries each live Ollama endpoint (discovered in Step 1 by
:mod:`aicortex.tools.check_models`) and collects the full model list that
each server exposes via its ``/api/tags`` route.  Results are merged and
saved as a single JSON file for the next stage (:mod:`aicortex.tools.resolve_models`).

Typical usage::

    from pathlib import Path
    from aicortex.tools import fetch_models

    results = fetch_models(Path("valid.txt"), Path("fetched.json"))
    print(f"Fetched data from {len(results)} endpoints")

Command-line usage::

    python -m aicortex.tools.fetch_models valid.txt --output fetched.json
"""

from __future__ import annotations

import json
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.error import HTTPError, URLError


def fetch_url_models(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch the model list from a single validated Ollama endpoint.

    Issues a GET request to *url* (which should already include the
    ``/api/tags`` path) and parses the JSON response.  On success the
    function returns the ``models`` array wrapped with the source URL so
    downstream steps can reconstruct the server association.

    Args:
        url: Full URL to the Ollama ``/api/tags`` endpoint, e.g.
            ``"http://1.2.3.4:11434/api/tags"``.
        timeout: Maximum seconds to wait for the server to respond.
            Defaults to ``10``.

    Returns:
        A dict ``{"source_url": url, "models": [...]}`` on success, or
        ``None`` if the request fails for any reason (network error, timeout,
        bad JSON, non-200 status, etc.).

    Example::

        >>> from aicortex.tools.fetch_models import fetch_url_models
        >>> result = fetch_url_models("http://127.0.0.1:11434/api/tags")
        >>> print(result["models"][0]["name"])
        llama3.2:3b
    """
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.getcode() == 200:
                payload = json.loads(response.read().decode('utf-8'))
                return {'source_url': url, 'models': payload.get('models', [])}
    except (HTTPError, URLError, socket.timeout, ValueError):
        return None
    except Exception:
        return None
    return None


def read_urls(url_file: Path) -> List[str]:
    """Read endpoint URLs from a plain-text file (one URL per line).

    Blank lines and lines containing only whitespace are ignored.  This is
    the complement of the ``--output`` file written by
    :mod:`aicortex.tools.check_models`.

    Args:
        url_file: Path to a newline-delimited text file of endpoint URLs.

    Returns:
        A list of stripped URL strings.  Returns an empty list if the file
        does not exist.
    """
    if not url_file.exists():
        return []
    return [line.strip() for line in url_file.read_text(encoding='utf-8').splitlines() if line.strip()]


def fetch_models(
    url_file: Path,
    output_file: Path,
    max_workers: int = 10,
    timeout: int = 10,
) -> List[dict]:
    """Fetch model metadata from all endpoints listed in *url_file* and save results.

    Reads the URL list produced by :func:`aicortex.tools.check_models.find_valid_endpoints`,
    queries each endpoint concurrently via :func:`fetch_url_models`, and
    writes the aggregated results to *output_file* as a JSON array.

    Args:
        url_file: Path to the plain-text file containing one validated
            endpoint URL per line (typically ``"valid.txt"``).
        output_file: Destination path for the consolidated JSON output
            (typically ``"fetched.json"``).
        max_workers: Number of concurrent HTTP workers.  Defaults to ``10``.
        timeout: Per-request timeout forwarded to :func:`fetch_url_models`.
            Defaults to ``10`` seconds.

    Returns:
        The list of successful result dicts (each with ``source_url`` and
        ``models`` keys) that was also written to *output_file*.  Returns an
        empty list if *url_file* is missing or contains no URLs.

    Example::

        >>> from pathlib import Path
        >>> from aicortex.tools import fetch_models
        >>> results = fetch_models(Path("valid.txt"), Path("fetched.json"))
        >>> print(f"Got data from {len(results)} servers")
    """
    urls = read_urls(url_file)
    if not urls:
        return []

    results: List[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for response in executor.map(lambda url: fetch_url_models(url, timeout=timeout), urls):
            if response:
                results.append(response)

    output_file.write_text(json.dumps(results, indent=4, ensure_ascii=False), encoding='utf-8')
    return results


#: Alias for backwards compatibility.
fetch_models_from_urls = fetch_models


def main() -> None:
    """CLI entry point: fetch model data from a list of validated endpoints.

    Usage::

        python -m aicortex.tools.fetch_models valid.txt --output fetched.json --timeout 10
    """
    import argparse

    parser = argparse.ArgumentParser(description='Fetch Ollama models from a list of validated endpoints.')
    parser.add_argument('url_file', type=Path, help='Path to the file containing validated endpoint URLs.')
    parser.add_argument('--output', type=Path, default=Path('fetched_models.json'), help='Output JSON file path.')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds.')
    args = parser.parse_args()

    responses = fetch_models_from_urls(args.url_file, args.output, timeout=args.timeout)
    print(f'Saved model data from {len(responses)} endpoints to {args.output}')


if __name__ == '__main__':
    main()
