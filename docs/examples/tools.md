# 🔧 Tools Examples

> **Annotated examples for the model management tool pipeline** — running each step
> individually, running the full pipeline end-to-end, automating with cron, and
> inspecting pipeline output at each stage.

See the [Tools Guide](../tools.md) for the full pipeline reference and all function signatures.

## Pipeline Overview

The four-tool pipeline keeps the bundled model metadata current by querying
live Ollama servers and writing the results back to `aicortex/models/*.json`.

```
check_models → fetch_models → resolve_models → apply_valid_models
     ↓               ↓               ↓                  ↓
  valid URLs    fetched data    resolved data      updated JSON files
```

Run the full pipeline whenever you add new Ollama servers, update to a new
Ollama version that ships new models, or want to refresh the bundled metadata
before a release.

## Running the Full Pipeline

### From the Command Line

Each tool is runnable as a module:

```bash
# Step 1 — check which servers are alive
python -m aicortex.tools.check_models

# Step 2 — fetch model lists from live servers
python -m aicortex.tools.fetch_models

# Step 3 — merge fetched data with existing metadata
python -m aicortex.tools.resolve_models

# Step 4 — write the resolved data to aicortex/models/*.json
python -m aicortex.tools.apply_valid_models
```

Or chain them in one line:

```bash
python -m aicortex.tools.check_models && \
python -m aicortex.tools.fetch_models && \
python -m aicortex.tools.resolve_models && \
python -m aicortex.tools.apply_valid_models
```

### From Python — Full Pipeline

```python
from pathlib import Path
from aicortex.tools import (
    find_valid_endpoints,
    fetch_models,
    resolve_models,
    apply_valid_models,
)

def refresh_model_database(models_dir: Path = Path("aicortex/models")) -> None:
    """Run the full model metadata refresh pipeline."""

    # Intermediate file paths
    urls_file     = Path("valid_endpoints.txt")
    fetched_file  = Path("fetched_models.json")
    resolved_file = Path("resolved_models.json")

    try:
        # Step 1 — discover live servers
        print("🔍 Checking endpoints...")
        valid_urls = find_valid_endpoints(models_dir)
        print(f"   {len(valid_urls)} live server(s) found")
        urls_file.write_text("\n".join(valid_urls))

        if not valid_urls:
            print("   No live servers — aborting. Is Ollama running?")
            return

        # Step 2 — fetch model lists
        print("📥 Fetching models...")
        fetch_models(urls_file, fetched_file)
        print("   Fetch complete")

        # Step 3 — merge with existing metadata
        print("🔀 Resolving metadata...")
        resolve_models(fetched_file, models_dir, resolved_file)
        print("   Resolve complete")

        # Step 4 — write updated JSON files
        print("💾 Applying to package...")
        created = apply_valid_models(resolved_file, models_dir, backup=True)
        print(f"   Updated {len(created)} model file(s): {[f.name for f in created]}")

        print("\n✅ Model database updated successfully.")

    finally:
        # Clean up intermediate files
        for path in (urls_file, fetched_file, resolved_file):
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    refresh_model_database()
```

## Step 1 — Checking Endpoints

`check_models` reads all server URLs from the bundled JSON files and probes
each one concurrently. It returns only the URLs that responded successfully.

```python
from pathlib import Path
from aicortex.tools import find_valid_endpoints

models_dir = Path("aicortex/models")
valid_urls = find_valid_endpoints(models_dir)

print(f"Live servers ({len(valid_urls)}):")
for url in valid_urls:
    print(f"  ✅ {url}")
```

**What "valid" means:** the server responded to the Ollama model list endpoint
within the configured timeout (default: 10 seconds) with a parseable response.

**Adding custom servers to check:**

The tool reads server URLs from the `servers[].url` field in each `aicortex/models/*.json`
file. To check a new server, add it to the relevant model's JSON:

```json
{
  "name": "llama3.2:3b",
  "servers": [
    {"url": "http://localhost:11434", "status": "unknown"},
    {"url": "http://my-server.internal:11434", "status": "unknown"}
  ]
}
```

## Step 2 — Fetching Models

`fetch_models` queries each live server for its current model list and saves
the raw response to a JSON file.

```python
from pathlib import Path
from aicortex.tools import fetch_models
import json

urls_file    = Path("valid_endpoints.txt")
fetched_file = Path("fetched_models.json")

fetch_models(urls_file, fetched_file)

# Inspect what was fetched
data = json.loads(fetched_file.read_text())
for server_url, model_list in data.items():
    print(f"{server_url}: {len(model_list)} model(s)")
    for model in model_list[:3]:  # show first 3
        print(f"  - {model['name']}")
```

## Step 3 — Resolving Models

`resolve_models` merges the freshly fetched data with the existing bundled
metadata, deduplicates entries, and assigns models to their correct families.

```python
from pathlib import Path
from aicortex.tools import resolve_models
import json

fetched_file  = Path("fetched_models.json")
models_dir    = Path("aicortex/models")
resolved_file = Path("resolved_models.json")

resolve_models(fetched_file, models_dir, resolved_file)

# Inspect the resolved output
resolved = json.loads(resolved_file.read_text())
for family, entries in resolved.items():
    print(f"{family}: {len(entries)} model(s)")
```

**Resolution rules:**
- Models are matched to a family by name prefix (`llama` → `llama.json`, etc.)
- Duplicate model names within a family are merged, keeping the richest metadata
- Models that appear on multiple servers get all server URLs in their entry
- Models with no matching family are placed in an `other` category

## Step 4 — Applying Model Files

`apply_valid_models` reads the resolved JSON and writes each family's data
to `aicortex/models/<family>.json`. The `backup=True` flag saves the previous
version as `<family>.json.bak` before overwriting.

```python
from pathlib import Path
from aicortex.tools import apply_valid_models

resolved_file = Path("resolved_models.json")
models_dir    = Path("aicortex/models")

created_files = apply_valid_models(resolved_file, models_dir, backup=True)

print(f"Updated {len(created_files)} file(s):")
for path in created_files:
    size = path.stat().st_size
    print(f"  {path.name}  ({size:,} bytes)")
```

**Rollback if something looks wrong:**

```bash
# Restore all backups
for f in aicortex/models/*.bak; do
    cp "$f" "${f%.bak}"
done
```

## Exploring Models After a Refresh

After the pipeline runs, use the public API to verify the updated metadata:

```python
from aicortex import families, models, get_model_info

# Check all families were written
print("Families:", families())

# List models in a specific family
print("Llama models:", models("llama"))

# Inspect a specific model
info = get_model_info("llama3.2:3b")
print(f"  Size: {info['size']}")
print(f"  Context: {info['context_length']} tokens")
print(f"  Servers: {[s['url'] for s in info['servers']]}")
```

## Automating with Cron

Run the pipeline nightly to keep metadata current without manual intervention:

```bash
# Edit crontab
crontab -e
```

```cron
# Refresh AI Cortex model metadata every night at 2 AM
0 2 * * * cd /path/to/aicortex && python -m aicortex.tools.check_models && \
  python -m aicortex.tools.fetch_models && \
  python -m aicortex.tools.resolve_models && \
  python -m aicortex.tools.apply_valid_models >> /var/log/aicortex-refresh.log 2>&1
```

Or use the Python pipeline function from earlier in a scheduled script:

```python
# refresh_job.py — run via cron or a task scheduler
import logging
from pathlib import Path
from your_pipeline_module import refresh_model_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

if __name__ == "__main__":
    logging.info("Starting model database refresh")
    refresh_model_database(Path("aicortex/models"))
    logging.info("Refresh complete")
```

## Pipeline in CI

Include a pipeline dry-run in your CI to catch regressions in tool code:

```yaml
# .github/workflows/ci.yml  (add to existing jobs)
- name: Test tool pipeline (dry run)
  run: |
    python -m aicortex.tools.check_models --dry-run
    python -m aicortex.tools.fetch_models --dry-run
    python -m aicortex.tools.resolve_models --dry-run
    # do not run apply_valid_models in CI — it modifies source files
```

> **`--dry-run` flag** — prints what each tool would do without writing any files
> or making persistent changes. Use this in CI to verify the tools are functional
> without side effects.

## See Also

- [Tools Guide](../tools.md) — full pipeline reference: all functions, parameters, and output formats
- [Models Guide](../models.md) — JSON schema and model family documentation
- [Development Guide](../development.md) — adding new tools and extending the pipeline
