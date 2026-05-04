# 🤖 Model Management

AI Cortex ships with a built-in registry of hundreds of models hosted on community cloud servers, organized by family. This page covers how to browse and query that catalog, how to read rich model metadata, and how to keep the registry fresh with the four-step discovery pipeline.

## 📦 Model Families

AI Cortex groups models into five families: **llama**, **mistral**, **gemma**, **deepseek**, and **qwen**. Each family maps to a JSON file bundled inside the package.

```python
from aicortex import families

print(families())
# ['llama', 'mistral', 'gemma', 'deepseek', 'qwen']
```

## 🔍 Listing Models

### All models across every family

```python
from aicortex import models

all_models = models()
print(f"Total available: {len(all_models)} models")
print(all_models[:5])
# ['llama3.2:3b', 'llama3.1:8b', 'mistral:7b', ...]
```

### Models in a specific family

```python
llama_models   = models("llama")
mistral_models = models("mistral")

print("Llama:",   llama_models)
print("Mistral:", mistral_models)
```

### Checking model availability

```python
from aicortex import models

available = models()

if "llama3.2:3b" in available:
    print("✅ Model is available")
else:
    print("❌ Not found — try one of:", available[:5])
```

## 📋 Model Metadata

Each model entry carries two categories of metadata: **identity fields** and **performance benchmark fields** collected when the model database was last refreshed.

### Getting full model info

```python
from aicortex import get_model_info

info = get_model_info("llama3.2:3b")

for key, value in info.items():
    print(f"  {key}: {value}")
```

### Identity fields

| Field | Description |
|---|---|
| `id` | Unique UUID for this model record |
| `model_name` | Human-readable model name (e.g. `llama3.2:3b`) |
| `model` | Ollama model tag (same as `model_name`) |
| `family` | Model family (`llama`, `mistral`, etc.) |
| `format` | Weight format (typically `gguf`) |
| `parameter_size` | Parameter count (e.g. `3.2B`, `7B`, `70B`) |
| `quantization_level` | Quantization used (e.g. `Q4_K_M`, `Q8_0`, `F16`) |
| `size` | Raw model size in bytes |
| `digest` | SHA256 digest of the model weights |
| `parent_model` | Base model this was fine-tuned from (if any) |
| `modified_at` | Timestamp the model was last modified on its server |
| `date_added` | Timestamp when this record was first added to the database |

### Server location fields

| Field | Description |
|---|---|
| `ip_port` | Full URL of the hosting Ollama server |
| `ip_city_name_en` | City of the server |
| `ip_country_name_en` | Country of the server |
| `ip_country_iso_code` | ISO country code |
| `ip_continent_code` | Continent code (e.g. `EU`, `NA`) |
| `ip_continent_name_en` | Full continent name |
| `ip_isp` | Internet service provider |
| `ip_organization` | Hosting organization |
| `ip_connection_type` | Connection type (e.g. `Corporate`, `Residential`) |
| `ip_autonomous_system_number` | ASN of the hosting network |
| `ip_autonomous_system_organization` | ASN owner name |

### Performance benchmark fields

These are recorded during the discovery pipeline's live test of each endpoint.

| Field | Description |
|---|---|
| `perf_status` | `"success"` or `"error"` |
| `perf_tokens` | Number of tokens generated in the benchmark run |
| `perf_time_seconds` | Total generation time in seconds |
| `perf_tokens_per_second` | Average throughput |
| `perf_max_token_speed` | Peak token generation speed |
| `perf_avg_token_speed` | Average token generation speed |
| `perf_first_token_time` | Time-to-first-token in seconds |
| `perf_model_size_bytes` | Model size reported by the server |
| `perf_last_tested` | Timestamp of the last benchmark run |
| `perf_error` | Error message if `perf_status` is `"error"` |

## 🌐 Server Discovery

Models are hosted on community Ollama servers. AI Cortex automatically selects a working server when you call `chat()`, but you can also inspect server availability directly.

### List all servers hosting a model

```python
from aicortex import list_model_servers

servers = list_model_servers("llama3.2:3b")

for s in servers:
    print(f"  {s['ip_port']}  —  {s['ip_city_name_en']}, {s['ip_country_name_en']}")
```

### Get server info for a specific model

```python
from aicortex import get_server_info

# Pick any working server for the given model
info = get_server_info("llama3.2:3b")
print(f"Server:   {info['ip_port']}")
print(f"Location: {info['ip_city_name_en']}, {info['ip_country_name_en']}")
print(f"Speed:    {info['perf_tokens_per_second']} tok/s")

# Or target a specific server URL
info = get_server_info("llama3.2:3b", "http://5.149.249.212:11434")
```

### LangChain-compatible params

`get_llm_params()` and `get_random_llm_params()` return a dict you can unpack directly into LangChain's `OllamaLLM`:

```python
from aicortex import get_llm_params, get_random_llm_params
from langchain_community.llms import OllamaLLM

# Pick a server for a specific model
params = get_llm_params("mistral:7b")
# → {'model': 'mistral:7b', 'base_url': 'http://...'}

llm = OllamaLLM(**params)

# Pick any random model from any available server
params = get_random_llm_params()
llm = OllamaLLM(**params)
```

## ⚙️ Model Selection in `chat()`

### Default model

The default model is `"gpt-oss:20b"`. You can override it per call:

```python
from aicortex import chat

# Uses default model
response = chat("What is 2 + 2?")

# Specify explicitly
response = chat("Write a sorting algorithm.", model="llama3.2:3b")
response = chat("Summarize this text.", model="mistral:7b")
```

### Choosing by performance

Use `get_model_info()` to compare benchmarks before picking a model:

```python
from aicortex import models, get_model_info

for name in models("llama"):
    try:
        info  = get_model_info(name)
        speed = info.get("perf_tokens_per_second", "?")
        size  = info.get("parameter_size", "?")
        print(f"  {name:<25} {size:<8} {speed} tok/s")
    except Exception:
        continue
```

### Forcing a specific server

```python
import os

os.environ["OLLAMA_HOST"] = "http://5.149.249.212:11434"

response = chat("Hello!", model="llama3.2:3b")
```

## 📐 Advanced Request Building

`build_api_request()` constructs the raw Ollama API payload — useful when you need full control or are integrating with a custom HTTP layer:

```python
from aicortex import build_api_request

payload = build_api_request(
    model="llama3.2:3b",
    prompt="Explain recursion.",
    temperature=0.3,
    max_tokens=300,
    top_p=0.9,
    stop=["\n\n", "END"],
)

print(payload)
```

## 🗂️ JSON Database Structure

The model database lives in `aicortex/models/`, one file per family:

```
aicortex/models/
├── llama.json
├── mistral.json
├── gemma.json
├── deepseek.json
└── qwen.json
```

Each file uses a nested envelope matching the Ollama registry format:

```json
{
  "props": {
    "pageProps": {
      "models": [
        {
          "id": "36a29c78-bb0a-49ef-a21a-e6a15b5b1dd1",
          "ip_port": "http://5.149.249.212:11434",
          "model_name": "llama3.2:3b",
          "model": "llama3.2:3b",
          "family": "llama",
          "format": "gguf",
          "parameter_size": "3.2B",
          "quantization_level": "Q4_K_M",
          "size": "2019393189",
          "digest": "a80c4f17...",
          "modified_at": "2026-03-22T00:41:35Z",
          "date_added": "2026-03-22T00:41:35Z",
          "ip_city_name_en": "Amsterdam",
          "ip_country_name_en": "The Netherlands",
          "ip_country_iso_code": "NL",
          "perf_status": "success",
          "perf_tokens_per_second": "13.01",
          "perf_first_token_time": "3.597",
          "perf_last_tested": "2025-04-19T08:24:12Z"
        }
      ]
    }
  }
}
```

## 🔄 Refreshing the Model Database

The bundled database is a static snapshot. Use the four-step pipeline to pull fresh data from live community servers.

### Full pipeline at a glance

```python
from pathlib import Path
from aicortex.tools import (
    find_valid_endpoints,   # Step 1 — ping known IPs
    fetch_models,           # Step 2 — pull model lists
    resolve_models,         # Step 3 — merge with IP metadata
    apply_valid_models,     # Step 4 — write family JSONs
)

json_dir = Path("aicortex/models")

# Step 1 — check which ip_port entries in the JSON files are actually alive
valid_urls = find_valid_endpoints(json_dir)
print(f"Live endpoints: {len(valid_urls)}")

url_file = Path("valid.txt")
url_file.write_text("\n".join(valid_urls))

# Step 2 — fetch the model list from each live endpoint
fetch_models(url_file, Path("fetched.json"))

# Step 3 — merge fetched data with existing IP/perf metadata
resolve_models(Path("fetched.json"), json_dir, Path("resolved.json"))

# Step 4 — group by family and write updated JSON files (with backup)
apply_valid_models(Path("resolved.json"), json_dir, backup=True)
```

For full documentation on each step, see [🔧 Tools](tools.md).

## ⚡ Performance & Selection Guide

### Parameter count vs. speed

| Size class | Range | Best for |
|---|---|---|
| Small | 1B – 3B | Fast Q&A, simple code, edge hardware |
| Medium | 7B – 13B | Best quality-to-speed balance |
| Large | 30B – 70B | Complex reasoning; needs capable server |

### Quantization guide

| Level | Quality | Size | Notes |
|---|---|---|---|
| `Q4_K_M` | Good | Small | Default on most community servers |
| `Q5_K_M` | Better | Moderate | Recommended if server allows |
| `Q8_0` | High | Large | Near-lossless compression |
| `F16` | Full precision | Very large | Maximum accuracy |

## 🛠️ Troubleshooting

### Model not found

```python
from aicortex import models

available = models()
query = "llama3"
suggestions = [m for m in available if query in m]
print(f"Did you mean: {suggestions}")
```

### Server connection failure

```python
from aicortex import get_server_info

try:
    info = get_server_info("llama3.2:3b")
    print(f"✅ Server OK: {info['ip_port']}")
except Exception as e:
    print(f"❌ No working server found: {e}")
    print("Try a different model or run the refresh pipeline.")
```

### Slow responses or stale data

The bundled JSON is a static snapshot. If you're hitting slow or unresponsive servers, run the refresh pipeline to rebuild the database from currently live endpoints.
