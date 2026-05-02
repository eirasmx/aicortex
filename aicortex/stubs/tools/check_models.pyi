from pathlib import Path
from typing import List, Optional

def normalize_url(base_url: str) -> str:
    """Normalize a URL by ensuring it starts with http."""
    ...

def check_url(base_url: str, timeout: int = 5) -> Optional[str]:
    """Check a single Ollama endpoint by requesting /api/tags.

    Args:
        base_url: Base host or IP address for the Ollama endpoint.
        timeout: Request timeout in seconds.

    Returns:
        The validated endpoint URL if valid, otherwise None.
    """
    ...

def extract_ips_from_json_dir(json_dir: Path) -> List[str]:
    """Read local model JSON files and extract unique ip_port values."""
    ...

def find_valid_endpoints(
    json_dir: Path,
    max_workers: int = 20,
    timeout: int = 5,
) -> List[str]:
    """Return all valid Ollama endpoints found in the JSON directory.

    Args:
        json_dir: Directory containing model JSON files.
        max_workers: Number of concurrent checks.
        timeout: Request timeout in seconds.

    Returns:
        List of valid endpoint URLs.
    """
    ...