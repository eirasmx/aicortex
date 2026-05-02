from pathlib import Path
from typing import Any, Dict, List

def load_ip_metadata(json_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load existing IP-level metadata from local Ollama model JSON files."""
    ...

def resolve_models(
    fetched_file: Path,
    json_dir: Path,
    output_file: Path,
) -> Dict[str, Any]:
    """Resolve fetched model records into the original Ollama JSON structure.

    Args:
        fetched_file: Path to the fetched_models.json file.
        json_dir: Directory containing original Ollama JSON files for metadata lookup.
        output_file: Output file path.

    Returns:
        The resolved models payload.
    """
    ...

resolve_fetched_models = resolve_models