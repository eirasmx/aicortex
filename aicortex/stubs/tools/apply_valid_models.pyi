from pathlib import Path
from typing import Dict, Iterable, List

def infer_family(model: dict) -> str:
    """Infer the model family from model data."""
    ...

def group_models_by_family(models: Iterable[dict]) -> Dict[str, List[dict]]:
    """Group models by their inferred family."""
    ...

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
    ...