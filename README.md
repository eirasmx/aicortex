<p align="center">
  <h1 align="center">🧠 AI Cortex</h1>
  <p align="center"><strong>A Python toolkit for free access to cloud and local language models.<br>Zero API keys. Zero signup. Completely free.</strong></p>
  <p align="center">
    <a href="https://pypi.org/project/aicortex-core/"><img src="https://img.shields.io/pypi/v/aicortex-core" alt="PyPI Version"></a>
    <a href="https://pepy.tech/projects/aicortex-core"><img src="https://static.pepy.tech/badge/aicortex-core" alt="Downloads"></a>
    <a href="https://pypi.org/project/aicortex-core/"><img src="https://img.shields.io/pypi/pyversions/aicortex-core" alt="Python Versions"></a>
    <a href="https://www.gnu.org/licenses/lgpl-3.0"><img src="https://img.shields.io/badge/License-LGPL_v3-blue.svg" alt="License"></a>
    <a href="https://deepwiki.com/eirasmx/aicortex"><img src="https://img.shields.io/badge/DeepWiki-eirasmx%2Faicortex-blue" alt="DeepWiki"></a>
  </p>
</p>

---

AI Cortex gives you a single, clean Python interface to **hundreds of language models** — Llama, Mistral, Gemma, DeepSeek, Qwen, and more — running on community-hosted cloud servers or your own local Ollama instance. No accounts. No credit cards. No rate limits.

```python
from aicortex import chat

response = chat("Explain neural networks like I'm five.")
print(response)
```

---

## ✨ Why AI Cortex?

| Feature | What it means for you |
|---|---|
| 🆓 **100% Free** | No API keys, no billing, no subscriptions — ever |
| 🤖 **Any Model** | Llama, Mistral, Gemma, DeepSeek, Qwen, and more |
| 🌐 **Cloud or Local** | Community-hosted cloud endpoints or your own Ollama server |
| ⚡ **Streaming** | Real-time token streaming for responsive UIs |
| 🔌 **OpenAI-Compatible** | Drop-in replacement for OpenAI client apps |
| 🛡️ **Type-Safe** | Full type hints, stubs, and IDE autocomplete |
| 🔧 **Production Ready** | Automatic failover, multi-server routing, error handling |
| 📦 **Lightweight** | One dependency (`ollama`) for the core package |

---

## 🚀 Installation

```bash
# Core package
pip install aicortex-core

# With OpenAI-compatible server support
pip install aicortex-core[server]
```

---

## 💬 Chat

```python
from aicortex import chat

# Simple response
response = chat("What is the speed of light?")
print(response)

# Custom model and parameters
response = chat(
    "Write a Python function to reverse a string.",
    model="llama3.2:3b",
    temperature=0.2,
    max_tokens=200,
)
print(response)
```

## ⚡ Streaming

```python
from aicortex import chat

stream = chat("Write a haiku about AI.", stream=True)

for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)
```

## 🤖 Model Discovery

```python
from aicortex import families, models, get_model_info

# Available families
print(families())   # ['llama', 'mistral', 'gemma', 'deepseek', 'qwen']

# Models in a family
print(models("mistral"))

# Full metadata for a model
info = get_model_info("llama3.2:3b")
print(info['parameter_size'], info['quantization_level'])
```

## 🌐 Server Discovery

```python
from aicortex import list_model_servers, get_server_info, get_llm_params

# All servers hosting a model — cloud and local
servers = list_model_servers("llama3.2:3b")
for s in servers:
    print(f"{s['url']} — {s['location']['city']}, {s['location']['country']}")

# Ready-to-use params for LangChain's OllamaLLM
params = get_llm_params("mistral:7b")
# → {'model': 'mistral:7b', 'base_url': 'http://...'}
```

## 🖥️ OpenAI-Compatible Server

Run a local proxy that speaks OpenAI's API — drop-in compatible with any OpenAI client:

```python
from aicortex.tools import run_server

run_server(host="127.0.0.1", port=8000, default_model="llama3.2:3b")
```

```bash
# Use with curl
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:3b", "messages": [{"role": "user", "content": "Hello!"}]}'

# Use with the openai Python SDK — just change the base_url
from openai import OpenAI
client = OpenAI(api_key="none", base_url="http://localhost:8000/v1")
response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 🔧 Model Management Tools

Keep the bundled model database fresh with the four-step pipeline:

```python
from pathlib import Path
from aicortex.tools import (
    find_valid_endpoints,     # Step 1: ping all known IPs
    fetch_models,             # Step 2: pull model lists
    resolve_models,           # Step 3: merge with IP metadata
    apply_valid_models,       # Step 4: write into family JSONs
)

json_dir   = Path("aicortex/models")
valid_urls = find_valid_endpoints(json_dir)                              # Step 1
fetch_models(Path("valid.txt"), Path("fetched.json"))                   # Step 2
resolve_models(Path("fetched.json"), json_dir, Path("resolved.json"))   # Step 3
apply_valid_models(Path("resolved.json"), json_dir, backup=True)        # Step 4
```

---

## 📚 Full Documentation

→ **[aicortex.readthedocs.io](https://aicortex.readthedocs.io)**

- [Installation](docs/installation.md)
- [Quick Start](docs/quickstart.md)
- [Basic Usage](docs/usage.md)
- [Streaming](docs/streaming.md)
- [Model Management](docs/models.md)
- [Server Mode](docs/server.md)
- [Tools](docs/tools.md)

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Development Guide](docs/development.md).

## 📄 License

[GNU Lesser General Public License v3.0](LICENSE) — free for open-source and commercial use.
