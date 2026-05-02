# 🔧 Tools

AI Cortex includes a four-step pipeline for discovering and refreshing the community model database. Each step is a standalone tool with a clean Python API and a `python -m` CLI interface.

```
Step 1: find_valid_endpoints  →  ping all known IPs, keep the live ones
Step 2: fetch_models          →  pull model lists from live endpoints
Step 3: resolve_models        →  merge with IP/perf metadata
Step 4: apply_valid_models    →  write updated family JSON files
```

## 📥 Imports

```python
# High-level imports (recommended)
from aicortex.tools import (
    find_valid_endpoints,
    fetch_models,
    resolve_models,
    apply_valid_models,
    run_server,
)

# Low-level imports (single-endpoint helpers)
from aicortex.tools.check_models import check_url
from aicortex.tools.fetch_models  import fetch_url_models
```

## Step 1 — `find_valid_endpoints`

Reads all `ip_port` values from the family JSON files and pings each one concurrently, returning only the endpoints that respond successfully.

### Python API

```python
from pathlib import Path
from aicortex.tools import find_valid_endpoints

valid_urls = find_valid_endpoints(
    json_dir=Path("aicortex/models"),
    max_workers=20,   # Concurrent ping threads (default: 20)
    timeout=5,        # Per-request timeout in seconds (default: 5)
)

print(f"Found {len(valid_urls)} live endpoints")
# ['http://5.149.249.212:11434/api/tags', 'http://...']

# Save for the next step
Path("valid.txt").write_text("\n".join(valid_urls))
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `json_dir` | `Path` | — | Directory containing family JSON files |
| `max_workers` | `int` | `20` | Number of concurrent check threads |
| `timeout` | `int` | `5` | Request timeout in seconds |

**Returns:** `List[str]` — validated endpoint URLs (including `/api/tags` path)

### CLI

```bash
python -m aicortex.tools.check_models aicortex/models
python -m aicortex.tools.check_models aicortex/models --output live.txt --timeout 3
```

### Low-level: `check_url`

Check a single endpoint:

```python
from aicortex.tools.check_models import check_url

result = check_url("127.0.0.1:11434", timeout=5)
# Returns the validated URL string, or None if unreachable

if result:
    print(f"✅ Live: {result}")
else:
    print("❌ Unreachable")
```

`check_url` accepts bare IPs (`127.0.0.1:11434`), URLs with or without `http://`, and normalizes them automatically.

## Step 2 — `fetch_models`

Reads the validated URL file produced in Step 1 and fetches the model list from each endpoint concurrently, saving the consolidated result as JSON.

### Python API

```python
from pathlib import Path
from aicortex.tools import fetch_models

results = fetch_models(
    url_file=Path("valid.txt"),          # From Step 1
    output_file=Path("fetched.json"),    # Output destination
    max_workers=10,                       # Concurrent fetch threads (default: 10)
    timeout=10,                           # Per-request timeout (default: 10)
)

print(f"Fetched data from {len(results)} endpoints")
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url_file` | `Path` | — | Text file with one endpoint URL per line |
| `output_file` | `Path` | — | Destination for the fetched JSON |
| `max_workers` | `int` | `10` | Number of concurrent fetch threads |
| `timeout` | `int` | `10` | Request timeout in seconds |

**Returns:** `List[dict]` — each entry has `source_url` and `models` keys

**Output format (`fetched.json`):**

```json
[
  {
    "source_url": "http://5.149.249.212:11434/api/tags",
    "models": [
      {
        "name":        "llama3.2:3b",
        "model":       "llama3.2:3b",
        "modified_at": "2026-03-22T00:41:35Z",
        "size":        2019393189,
        "digest":      "a80c4f17...",
        "details": {
          "family":             "llama",
          "parameter_size":     "3.2B",
          "quantization_level": "Q4_K_M",
          "format":             "gguf"
        }
      }
    ]
  }
]
```

### CLI

```bash
python -m aicortex.tools.fetch_models valid.txt
python -m aicortex.tools.fetch_models valid.txt --output fetched.json --timeout 15
```

### Low-level: `fetch_url_models`

Fetch from a single endpoint:

```python
from aicortex.tools.fetch_models import fetch_url_models

data = fetch_url_models("http://5.149.249.212:11434/api/tags", timeout=10)

if data:
    print(f"Source: {data['source_url']}")
    print(f"Models: {len(data['models'])}")
else:
    print("Fetch failed")
```

## Step 3 — `resolve_models`

Merges the raw fetched data with the richer IP and performance metadata stored in the existing family JSON files, producing a resolved payload in the package's native format.

### Python API

```python
from pathlib import Path
from aicortex.tools import resolve_models

result = resolve_models(
    fetched_file=Path("fetched.json"),   # From Step 2
    json_dir=Path("aicortex/models"),    # Existing JSONs for metadata lookup
    output_file=Path("resolved.json"),   # Output destination
)

count = len(result["props"]["pageProps"]["models"])
print(f"Resolved {count} model records")
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `fetched_file` | `Path` | Fetched models JSON from Step 2 |
| `json_dir` | `Path` | Directory with existing family JSONs (for IP/perf metadata) |
| `output_file` | `Path` | Destination for the resolved payload |

**Returns:** `dict` — the full resolved payload (`{"props": {"pageProps": {"models": [...]}}}`)

**What resolution adds:** Each model record is enriched with `ip_*` location fields and `perf_*` benchmark fields pulled from the matching `ip_port` entry in the existing JSON database. New servers without prior metadata will still be included, with only the fields available from the live fetch.

### CLI

```bash
python -m aicortex.tools.resolve_models fetched.json aicortex/models
python -m aicortex.tools.resolve_models fetched.json aicortex/models --output resolved.json
```

## Step 4 — `apply_valid_models`

Reads the resolved payload from Step 3, groups models by family, and writes one JSON file per family into the target directory. Optionally backs up existing files first.

### Python API

```python
from pathlib import Path
from aicortex.tools import apply_valid_models

created = apply_valid_models(
    resolved_file=Path("resolved.json"),  # From Step 3
    json_dir=Path("aicortex/models"),     # Target directory
    backup=True,                           # Back up existing JSONs first
)

print(f"Written {len(created)} family files:")
for path in created:
    print(f"  {path}")
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resolved_file` | `Path` | — | Resolved models JSON from Step 3 |
| `json_dir` | `Path` | — | Target directory for family JSON files |
| `backup` | `bool` | `False` | Move existing JSON files to `<json_dir>.backup/` before writing |

**Returns:** `List[Path]` — paths of the created family JSON files

**Family inference:** Models are grouped by the `family` field in their metadata. If the family is missing or `"unknown"`, the tool infers it from the model name (e.g. a model named `mistral-nemo:12b` is placed in `mistral.json`). Models that don't match any known family are written to `others.json`.

### CLI

```bash
python -m aicortex.tools.apply_valid_models resolved.json aicortex/models
python -m aicortex.tools.apply_valid_models resolved.json aicortex/models --backup
```

## 🖥️ `run_server`

Starts the OpenAI-compatible HTTP proxy. See [🖥️ Server Mode](server.md) for the full reference.

```python
from aicortex.tools import run_server

run_server(
    host="127.0.0.1",
    port=8000,
    default_model="llama3.2:3b",
    reload=True,
)
```

**Raises `ImportError`** if `aicortex-core[server]` is not installed.

## 🔁 Complete Pipeline Example

```python
from pathlib import Path
from aicortex.tools import (
    find_valid_endpoints,
    fetch_models,
    resolve_models,
    apply_valid_models,
)

json_dir  = Path("aicortex/models")
url_file  = Path("valid.txt")
fetched   = Path("fetched.json")
resolved  = Path("resolved.json")

# Step 1 — discover live endpoints
print("🔍 Checking endpoints...")
valid_urls = find_valid_endpoints(json_dir, max_workers=20, timeout=5)
url_file.write_text("\n".join(valid_urls))
print(f"   {len(valid_urls)} live endpoints")

# Step 2 — fetch current model lists
print("📥 Fetching models...")
results = fetch_models(url_file, fetched, max_workers=10, timeout=10)
print(f"   Data from {len(results)} endpoints")

# Step 3 — merge with metadata
print("🔗 Resolving metadata...")
result = resolve_models(fetched, json_dir, resolved)
count  = len(result["props"]["pageProps"]["models"])
print(f"   {count} model records resolved")

# Step 4 — write family files
print("💾 Applying to package...")
created = apply_valid_models(resolved, json_dir, backup=True)
print(f"   {len(created)} family files updated")

print("✅ Database refresh complete.")
```

## 🚨 Error Handling

```python
from pathlib import Path
from aicortex.tools import find_valid_endpoints

try:
    urls = find_valid_endpoints(Path("nonexistent/"))
except FileNotFoundError:
    print("Models directory not found")

# fetch_models returns an empty list if url_file is missing or empty
# resolve_models raises json.JSONDecodeError on malformed input
# apply_valid_models raises ValueError if the models list is not a list
```

## 📦 Dependencies

| Tool | Extra required |
|---|---|
| `find_valid_endpoints`, `check_url` | None — stdlib only |
| `fetch_models`, `fetch_url_models` | None — stdlib only |
| `resolve_models` | None — stdlib only |
| `apply_valid_models` | None — stdlib only |
| `run_server` | `aicortex-core[server]` (FastAPI + Uvicorn) |
