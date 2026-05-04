# 📦 Installation

AI Cortex is published on [PyPI](https://pypi.org/project/aicortex-core/) and installs with a single command.
No account, no API key, no configuration file required.

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.8 or higher |
| Ollama | Required only for local model hosting — not needed for cloud access |

> **💡 No local setup needed.**
> AI Cortex ships with a bundled registry of community-hosted cloud endpoints,
> so you can start chatting immediately — no Ollama installation, no local server, no configuration.
> Running your own Ollama server is supported and recommended when you need privacy or lower latency.

## Basic Installation

Install the core package — one dependency (`ollama`), nothing else:

```bash
pip install aicortex-core
```

That's all you need for `chat()`, model discovery, and streaming.

## Installation with Extras

### 🖥️ Server Mode

To run the OpenAI-compatible REST API proxy, install the `server` extras:

```bash
pip install aicortex-core[server]
```

This additionally installs:

| Package | Purpose |
|---|---|
| `fastapi` | High-performance async web framework |
| `uvicorn` | ASGI server for running FastAPI |
| `pydantic` | Request/response data validation |

### 🛠️ Development

For contributing or running the test suite:

```bash
pip install aicortex-core[dev]
```

Or install directly from source with all extras:

```bash
git clone https://github.com/eirasmx/aicortex.git
cd aicortex
pip install -e ".[server,dev]"
```

## Installing Ollama (For Local Hosting)

Ollama is only required if you want to run models on your own machine. Cloud access works without it.

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:** Download the installer from [ollama.com](https://ollama.com/download).

Then pull a model to use locally:
```bash
ollama pull llama3.2:3b      # Fast, 3B parameter Llama model
ollama pull mistral:7b       # Mistral 7B — great all-rounder
ollama pull gemma2:9b        # Google Gemma 2 9B
ollama pull deepseek-r1:7b   # DeepSeek reasoning model
```

Start the server (it auto-starts on macOS/Linux after install):
```bash
ollama serve
```

## Verify Your Installation

Run this in Python to confirm everything is working:

```python
import aicortex

# Check the version
print(aicortex.__version__)   # e.g. 1.0.3

# List available model families
print(aicortex.families())    # ['llama', 'mistral', 'gemma', 'deepseek', 'qwen']

# Quick connectivity check
print(aicortex.models("llama")[:3])  # First 3 Llama models
```

For a live end-to-end test (requires an Ollama server):

```python
from aicortex import chat

response = chat("Say hello in one sentence.", model="llama3.2:3b")
print(response)
```

## Upgrading

```bash
pip install --upgrade aicortex-core
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'aicortex'`**
→ Make sure you installed into the correct Python environment. Try `python -m pip install aicortex-core`.

**`RuntimeError: No servers available for model '...'`**
→ No live server was found for that model. Either the community endpoints for that model are temporarily down, or you're trying to run locally without `ollama serve` running. Try a different model, or check that your local Ollama server is reachable.

**`ImportError: FastAPI server requires additional dependencies`**
→ You tried to call `run_server()` without the server extras. Run `pip install aicortex-core[server]`.

**`ValueError: Model '...' not found`**
→ The model name doesn't exist in the bundled metadata. Use `aicortex.models()` to see all available names, or update the model database with the [tools pipeline](tools.md).

## Next Steps

→ [Quick Start](quickstart.md) — get your first response in 5 minutes
→ [Basic Usage](usage.md) — explore all parameters and patterns
