from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    'apply_valid_models',
    'find_valid_endpoints',
    'fetch_models',
    'fetch_models_from_urls',
    'resolve_models',
    'resolve_fetched_models',
    'run_server',
]


def apply_valid_models(
    resolved_file: Path,
    json_dir: Path,
    backup: bool = False,
) -> List[Path]:
    """Write valid resolved models into family JSON files.

    Args:
        resolved_file: Path to the resolved model JSON payload.
        json_dir: Directory where family JSON files should be written.
        backup: If True, back up existing JSON files to a .backup folder.

    Returns:
        List of created JSON file paths.
    """


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


def fetch_models(
    url_file: Path,
    output_file: Path,
    max_workers: int = 10,
    timeout: int = 10,
) -> List[dict]:
    """Fetch model JSON from all validated endpoints and save the consolidated result.

    Args:
        url_file: Path to file containing endpoint URLs.
        output_file: Path to save the fetched models JSON.
        max_workers: Number of concurrent fetches.
        timeout: Request timeout in seconds.

    Returns:
        List of fetched model data dictionaries.
    """


fetch_models_from_urls = fetch_models


def resolve_models(
    fetched_file: Path,
    json_dir: Path,
    output_file: Path,
) -> Dict[str, Any]:
    """Resolve fetched model records into the original Ollama JSON structure.

    Args:
        fetched_file: Path to the fetched_models.json file.
        json_dir: Directory containing original Ollama JSON files for metadata lookup.
        output_file: Path to save the resolved models.

    Returns:
        The resolved models payload dictionary.
    """


resolve_fetched_models = resolve_models


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    default_model: str = "gpt-oss:20b",
    reload: bool = True,
) -> None:
    """Run the AI Cortex OpenAI-compatible proxy server.

    Args:
        host: Host to bind the server to.
        port: Port to bind the server to.
        default_model: Default model to use when not specified.
        reload: Whether to enable auto-reload for development.

    Raises:
        ImportError: If required dependencies (fastapi, uvicorn, pydantic) are not installed.
    """