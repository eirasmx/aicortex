"""Step 3 of the model refresh pipeline: metadata resolution.

This module merges the raw model data collected in Step 2
(:mod:`aicortex.tools.fetch_models`) with the rich IP-level metadata
(geographic location, organisation, performance stats) that is already stored
in the bundled JSON files.  The result is a fully-enriched model list in the
canonical ``props.pageProps.models`` structure expected by Step 4
(:mod:`aicortex.tools.apply_valid_models`).

Typical usage::

    from pathlib import Path
    from aicortex.tools import resolve_models

    result = resolve_models(
        Path("fetched.json"),
        Path("aicortex/models"),
        Path("resolved.json"),
    )
    count = len(result["props"]["pageProps"]["models"])
    print(f"Resolved {count} model records")

Command-line usage::

    python -m aicortex.tools.resolve_models fetched.json aicortex/models --output resolved.json
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List


def load_ip_metadata(json_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Build an index of per-IP metadata from the bundled model JSON files.

    Scans all ``*.json`` files under *json_dir*, extracts every model entry,
    and stores the first set of ``ip_*`` and ``perf_*`` fields seen for each
    unique ``ip_port`` value.  Subsequent entries for the same IP are ignored
    (first-write-wins), since the metadata fields are server-level rather than
    model-level.

    The ``ip_port`` values are normalised to include an ``http://`` scheme
    so they can be compared directly against URLs produced by
    :func:`aicortex.tools.fetch_models.fetch_url_models`.

    Args:
        json_dir: Root directory of the bundled model JSON files, typically
            ``aicortex/models/``.

    Returns:
        A dict mapping normalised server URLs (e.g.
        ``"http://1.2.3.4:11434"``) to their metadata dicts.  Each metadata
        dict contains only ``ip_*`` and ``perf_*`` keys.
    """
    metadata: Dict[str, Dict[str, Any]] = {}

    for path in json_dir.rglob('*.json'):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue

        models = payload.get('props', {}).get('pageProps', {}).get('models', [])
        for model in models:
            ip_port = model.get('ip_port', '')
            if not ip_port:
                continue
            if not ip_port.startswith('http'):
                ip_port = 'http://' + ip_port

            if ip_port not in metadata:
                metadata[ip_port] = {
                    key: value
                    for key, value in model.items()
                    if key.startswith('ip_') or key.startswith('perf_')
                }

    return metadata


def resolve_models(
    fetched_file: Path,
    json_dir: Path,
    output_file: Path,
) -> Dict[str, Any]:
    """Merge fetched model records with IP metadata and write the resolved output.

    For each model returned by every server in *fetched_file*, this function:

    1. Looks up the server's ``ip_port`` in the metadata index built from
       *json_dir* (geographic location, organisation, performance fields).
    2. Flattens the Ollama ``details`` sub-object (``parent_model``,
       ``format``, ``family``, ``parameter_size``, ``quantization_level``)
       into the top-level record.
    3. Assigns a fresh UUID as the record ``id``.
    4. Merges any remaining IP/perf metadata fields.
    5. Writes the complete resolved payload to *output_file* in the canonical
       ``{"props": {"pageProps": {"models": [...]}}}`` structure.

    Args:
        fetched_file: Path to the JSON file produced by
            :func:`aicortex.tools.fetch_models.fetch_models` (Step 2).
        json_dir: Directory containing the bundled model JSON files used as
            the metadata lookup source.
        output_file: Destination path for the resolved output JSON
            (e.g. ``"resolved.json"``).

    Returns:
        The full resolved payload dict (same content as *output_file*).

    Example::

        >>> from pathlib import Path
        >>> from aicortex.tools import resolve_models
        >>> out = resolve_models(Path("fetched.json"), Path("aicortex/models"), Path("resolved.json"))
        >>> models = out["props"]["pageProps"]["models"]
        >>> print(models[0]["parameter_size"])
        7B
    """
    fetched_data = json.loads(fetched_file.read_text(encoding='utf-8'))
    metadata = load_ip_metadata(json_dir)

    resolved_models: List[Dict[str, Any]] = []
    for record in fetched_data:
        source_url = record.get('source_url', '')
        base_ip_port = source_url.replace('/api/tags', '')
        if base_ip_port not in metadata:
            base_ip_port = base_ip_port.rstrip('/')

        meta = metadata.get(base_ip_port, {})
        for model_data in record.get('models', []):
            model_name = model_data.get('name') or model_data.get('model')
            resolved_models.append({
                'id': str(uuid.uuid4()),
                'ip_port': base_ip_port,
                'model_name': model_name,
                'model': model_data.get('model'),
                'modified_at': model_data.get('modified_at'),
                'size': str(model_data.get('size', '')),
                'digest': model_data.get('digest'),
                'parent_model': model_data.get('details', {}).get('parent_model', ''),
                'format': model_data.get('details', {}).get('format', ''),
                'family': model_data.get('details', {}).get('family', ''),
                'parameter_size': model_data.get('details', {}).get('parameter_size', ''),
                'quantization_level': model_data.get('details', {}).get('quantization_level', ''),
                'date_added': meta.get('date_added', model_data.get('modified_at')),
                **{k: v for k, v in meta.items() if k not in {
                    'date_added', 'ip_port', 'model_name', 'model', 'modified_at',
                    'size', 'digest', 'parent_model', 'format', 'family',
                    'parameter_size', 'quantization_level',
                }},
            })

    output_payload = {'props': {'pageProps': {'models': resolved_models}}}
    output_file.write_text(json.dumps(output_payload, indent=4, ensure_ascii=False), encoding='utf-8')
    return output_payload


#: Alias for backwards compatibility.
resolve_fetched_models = resolve_models


def main() -> None:
    """CLI entry point: resolve fetched model metadata into enriched JSON output.

    Usage::

        python -m aicortex.tools.resolve_models fetched.json aicortex/models --output resolved.json
    """
    import argparse

    parser = argparse.ArgumentParser(description='Resolve fetched Ollama model metadata into JSON output.')
    parser.add_argument('fetched_file', type=Path, help='Path to the fetched_models.json file.')
    parser.add_argument('json_dir', type=Path, help='Directory containing original Ollama JSON files for metadata lookup.')
    parser.add_argument('--output', type=Path, default=Path('resolved_valid_models.json'), help='Output file path.')
    args = parser.parse_args()

    result = resolve_fetched_models(args.fetched_file, args.json_dir, args.output)
    print(f"Resolved {len(result['props']['pageProps']['models'])} models into {args.output}")


if __name__ == '__main__':
    main()
