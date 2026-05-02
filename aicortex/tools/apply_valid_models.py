"""Step 4 of the model refresh pipeline: write models to family JSON files.

This is the final step of the update workflow.  It reads the fully-resolved
model list produced by :mod:`aicortex.tools.resolve_models` (Step 3), groups
models by family, and writes one ``<family>.json`` file per group into the
target directory.  The result replaces the bundled model database used by
:class:`aicortex.api._OllamaAPI` at import time.

Family inference follows a simple priority order: the model's ``family``
metadata field is used first; if it is absent or ``"unknown"``, the model
name is pattern-matched against known family keywords (``llama``, ``mistral``,
``gemma``, ``qwen``, ``deepseek``).  Models that match none of these fall into
an ``"others"`` family.

Typical usage::

    from pathlib import Path
    from aicortex.tools import apply_valid_models

    created = apply_valid_models(
        Path("resolved.json"),
        Path("aicortex/models"),
        backup=True,
    )
    print(f"Wrote {len(created)} family files")

Command-line usage::

    python -m aicortex.tools.apply_valid_models resolved.json aicortex/models --backup
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def infer_family(model: dict) -> str:
    """Determine the model family from a resolved model metadata dict.

    The inference logic works in two passes:

    1. **Metadata field** — uses ``model["family"]`` if present and not equal
       to ``"unknown"``.
    2. **Name pattern** — falls back to substring matching on the lowercased
       ``model_name`` / ``model`` field against the keywords ``mistral``,
       ``llama``, ``gemma``, ``qwen``, and ``deepseek``.  Unmatched models
       are assigned the family ``"others"``.

    A final normalisation step collapses variant prefixes such as ``"gemma2"``
    back to their canonical family names (``"gemma"``).

    Args:
        model: A resolved model metadata dict, as produced by
            :func:`aicortex.tools.resolve_models.resolve_models`.

    Returns:
        A lowercase family name string, e.g. ``"llama"``, ``"mistral"``, or
        ``"others"``.
    """
    family = model.get('family', '') or ''
    if not family or family == 'unknown':
        name = (model.get('model_name') or model.get('model') or '').lower()
        if 'mistral' in name:
            family = 'mistral'
        elif 'llama' in name:
            family = 'llama'
        elif 'gemma' in name:
            family = 'gemma'
        elif 'qwen' in name:
            family = 'qwen'
        elif 'deepseek' in name:
            family = 'deepseek'
        else:
            family = 'others'

    if family.startswith('qwen'):
        return 'qwen'
    if family.startswith('gemma'):
        return 'gemma'
    if family.startswith('llama'):
        return 'llama'
    if family.startswith('mistral'):
        return 'mistral'
    if family.startswith('deepseek'):
        return 'deepseek'
    return family


def group_models_by_family(models: Iterable[dict]) -> Dict[str, List[dict]]:
    """Partition a flat model list into a family-keyed dict.

    Calls :func:`infer_family` on each model and groups the results using a
    :class:`collections.defaultdict`.

    Args:
        models: An iterable of resolved model metadata dicts.

    Returns:
        A dict mapping each inferred family name to its list of model dicts.
    """
    grouped: Dict[str, List[dict]] = defaultdict(list)
    for model in models:
        family = infer_family(model)
        grouped[family].append(model)
    return grouped


def apply_valid_models(
    resolved_file: Path,
    json_dir: Path,
    backup: bool = False,
) -> List[Path]:
    """Write resolved models into per-family JSON files, replacing the bundled database.

    This is the final step of the four-stage model refresh pipeline.  The
    function reads the canonical payload produced by
    :func:`aicortex.tools.resolve_models.resolve_models`, groups models by
    family using :func:`group_models_by_family`, and writes one file per
    family into *json_dir*.  The output files use the same
    ``{"props": {"pageProps": {"models": [...]}}}`` structure as the originals
    so they are immediately compatible with :class:`aicortex.api._OllamaAPI`.

    Backup behaviour
    ~~~~~~~~~~~~~~~~
    When *backup* is ``True``, all existing ``*.json`` files in *json_dir*
    are moved to a sibling ``<json_dir>.backup/`` directory **before** any
    new files are written.  This makes it safe to roll back by renaming the
    directories.

    Args:
        resolved_file: Path to the resolved model JSON produced by Step 3
            (typically ``"resolved.json"``).
        json_dir: Target directory where family JSON files are written.
            Created automatically if it does not exist.
        backup: When ``True``, move existing JSON files to a ``.backup``
            directory before writing new ones.  Defaults to ``False``.

    Returns:
        An ordered list of :class:`pathlib.Path` objects for every family
        JSON file that was created.

    Raises:
        ValueError: If the resolved payload does not contain a valid
            ``models`` list.

    Example::

        >>> from pathlib import Path
        >>> from aicortex.tools import apply_valid_models
        >>> paths = apply_valid_models(Path("resolved.json"), Path("aicortex/models"), backup=True)
        >>> [p.name for p in paths]
        ['deepseek.json', 'gemma.json', 'llama.json', 'mistral.json', 'qwen.json']
    """
    resolved_file = Path(resolved_file)
    json_dir = Path(json_dir)
    output_paths: List[Path] = []

    payload = json.loads(resolved_file.read_text(encoding='utf-8'))
    models = payload.get('props', {}).get('pageProps', {}).get('models', [])
    if not isinstance(models, list):
        raise ValueError('Resolved payload does not contain a valid models list')

    if backup and json_dir.exists():
        backup_dir = json_dir.with_name(json_dir.name + '.backup')
        backup_dir.mkdir(parents=True, exist_ok=True)
        for existing_file in sorted(json_dir.glob('*.json')):
            existing_file.rename(backup_dir / existing_file.name)

    json_dir.mkdir(parents=True, exist_ok=True)

    grouped_models = group_models_by_family(models)
    for family, family_models in grouped_models.items():
        output_file = json_dir / f'{family}.json'
        output_payload = {'props': {'pageProps': {'models': family_models}}}
        output_file.write_text(json.dumps(output_payload, indent=4, ensure_ascii=False), encoding='utf-8')
        output_paths.append(output_file)

    return output_paths


def main() -> None:
    """CLI entry point: apply resolved model metadata to family JSON files.

    Usage::

        python -m aicortex.tools.apply_valid_models resolved.json aicortex/models [--backup]
    """
    import argparse

    parser = argparse.ArgumentParser(description='Apply resolved Ollama model metadata to family JSON files.')
    parser.add_argument('resolved_file', type=Path, help='Resolved models JSON file.')
    parser.add_argument('json_dir', type=Path, help='Target directory for family JSON files.')
    parser.add_argument('--backup', action='store_true', help='Move existing JSON files to a backup directory.')
    args = parser.parse_args()

    created = apply_valid_models(args.resolved_file, args.json_dir, backup=args.backup)
    print(f'Created {len(created)} model files in {args.json_dir}')


if __name__ == '__main__':
    main()
