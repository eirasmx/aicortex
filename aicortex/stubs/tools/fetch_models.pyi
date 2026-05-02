from pathlib import Path
from typing import List, Optional

def fetch_url_models(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch model metadata from a single validated Ollama endpoint.

    Args:
        url: URL to the Ollama endpoint, including /api/tags.
        timeout: Request timeout in seconds.

    Returns:
        A dictionary containing source_url and models if successful.
    """
    ...

def read_urls(url_file: Path) -> List[str]:
    """Read endpoint URLs from a plain text file."""
    ...

def fetch_models(
    url_file: Path,
    output_file: Path,
    max_workers: int = 10,
    timeout: int = 10,
) -> List[dict]:
    """Fetch model JSON from all validated endpoints and save the consolidated result.

    Args:
        url_file: Path to the file containing validated endpoint URLs.
        output_file: Output JSON file path.
        max_workers: Number of concurrent fetches.
        timeout: Request timeout in seconds.

    Returns:
        List of fetched model data.
    """
    ...

fetch_models_from_urls = fetch_models