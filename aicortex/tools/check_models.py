"""Step 1 of the model refresh pipeline: endpoint validation.

This module pings every ``ip_port`` value found in the bundled model JSON
files and returns only the endpoints that respond with HTTP 200 from their
``/api/tags`` route.  The resulting URL list is the input for
:mod:`aicortex.tools.fetch_models` (Step 2).

Typical usage::

    from pathlib import Path
    from aicortex.tools import find_valid_endpoints

    valid_urls = find_valid_endpoints(Path("aicortex/models"))
    # → ['http://1.2.3.4:11434/api/tags', 'http://5.6.7.8:11434/api/tags', ...]

Command-line usage::

    python -m aicortex.tools.check_models aicortex/models --output valid.txt
"""

from __future__ import annotations

import json
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.error import HTTPError, URLError


def normalize_url(base_url: str) -> str:
    """Ensure a URL has an ``http://`` scheme and no trailing slash.

    Args:
        base_url: Raw host string, e.g. ``"1.2.3.4:11434"`` or
            ``"http://1.2.3.4:11434/"``.

    Returns:
        A normalised URL such as ``"http://1.2.3.4:11434"``.
    """
    if not base_url.startswith('http'):
        base_url = 'http://' + base_url
    return base_url.rstrip('/')


def check_url(base_url: str, timeout: int = 5) -> Optional[str]:
    """Probe a single Ollama endpoint and return its ``/api/tags`` URL if live.

    Issues a lightweight GET request to ``<base_url>/api/tags``.  A ``200 OK``
    response indicates that Ollama is running and accepting requests.

    Args:
        base_url: Host or IP address for the Ollama server, with or without
            an ``http://`` prefix, e.g. ``"127.0.0.1:11434"``.
        timeout: Maximum seconds to wait for a response.  Defaults to ``5``.

    Returns:
        The full validated endpoint URL (``"http://…/api/tags"``) if the
        server is reachable and healthy, otherwise ``None``.

    Example::

        >>> from aicortex.tools.check_models import check_url
        >>> print(check_url("127.0.0.1:11434"))
        http://127.0.0.1:11434/api/tags
    """
    test_url = normalize_url(base_url) + '/api/tags'

    try:
        request = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.getcode() == 200:
                return test_url
    except (HTTPError, URLError, socket.timeout, ValueError):
        return None
    except Exception:
        return None
    return None


def extract_ips_from_json_dir(json_dir: Path) -> List[str]:
    """Collect every unique ``ip_port`` value from bundled model JSON files.

    Recursively scans all ``*.json`` files under *json_dir*, parses the
    ``props.pageProps.models`` list, and extracts the ``ip_port`` field from
    each model entry.  Duplicates are removed and the result is sorted for
    deterministic output.

    Args:
        json_dir: Root directory containing Ollama model JSON files.

    Returns:
        A sorted list of unique ``ip_port`` strings, e.g.
        ``["1.2.3.4:11434", "5.6.7.8:11434"]``.  Returns an empty list if no
        files or no ``ip_port`` values are found.
    """
    urls: set[str] = set()

    for path in json_dir.rglob('*.json'):
        try:
            with path.open('r', encoding='utf-8') as f:
                payload = json.load(f)
        except Exception:
            continue

        models = payload.get('props', {}).get('pageProps', {}).get('models', [])
        for model in models:
            ip_port = model.get('ip_port')
            if ip_port:
                urls.add(ip_port)

    return sorted(urls)


def find_valid_endpoints(
    json_dir: Path,
    max_workers: int = 20,
    timeout: int = 5,
) -> List[str]:
    """Return all live Ollama endpoints discovered in the JSON model database.

    Combines :func:`extract_ips_from_json_dir` (to enumerate candidate IPs)
    with a concurrent :func:`check_url` sweep to filter out unreachable or
    offline servers.  Uses a thread pool so hundreds of IPs can be probed
    in a few seconds.

    Args:
        json_dir: Directory containing bundled model JSON files, typically
            ``aicortex/models/``.
        max_workers: Size of the thread pool used for concurrent probing.
            Defaults to ``20``.  Increase for large IP sets, decrease to
            reduce network saturation.
        timeout: Per-request timeout in seconds passed to :func:`check_url`.
            Defaults to ``5``.

    Returns:
        A list of validated endpoint URLs in the form
        ``"http://<ip>:<port>/api/tags"``.  Returns an empty list if no
        valid endpoints are found.

    Example::

        >>> from pathlib import Path
        >>> from aicortex.tools.check_models import find_valid_endpoints
        >>> valid = find_valid_endpoints(Path("aicortex/models"))
        >>> print(valid[:3])
        ['http://1.2.3.4:11434/api/tags', ...]
    """
    json_dir = Path(json_dir)
    ips = extract_ips_from_json_dir(json_dir)
    if not ips:
        return []

    valid_endpoints: List[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(lambda url: check_url(url, timeout=timeout), ips):
            if result:
                valid_endpoints.append(result)

    return valid_endpoints


def main() -> None:
    """CLI entry point: validate Ollama endpoints and save results to a file.

    Usage::

        python -m aicortex.tools.check_models <json_dir> [--output valid.txt] [--timeout 5]
    """
    import argparse

    parser = argparse.ArgumentParser(description='Validate Ollama endpoint URLs from JSON metadata.')
    parser.add_argument('json_dir', type=Path, help='Directory containing Ollama JSON files.')
    parser.add_argument('--output', type=Path, default=Path('valid_models.txt'), help='Path to save valid endpoints.')
    parser.add_argument('--timeout', type=int, default=5, help='Request timeout in seconds.')
    args = parser.parse_args()

    valid = find_valid_endpoints(args.json_dir, timeout=args.timeout)
    args.output.write_text('\n'.join(valid), encoding='utf-8')
    print(f'Saved {len(valid)} valid endpoints to {args.output}')


if __name__ == '__main__':
    main()
