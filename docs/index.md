# 🧠 AI Cortex

**A Python toolkit for free access to cloud and local language models — zero API keys, zero signup, completely free.**

[![PyPI Version](https://img.shields.io/pypi/v/aicortex-core)](https://pypi.org/project/aicortex-core/)
[![Downloads](https://static.pepy.tech/badge/aicortex-core)](https://pepy.tech/projects/aicortex-core)
[![Python](https://img.shields.io/pypi/pyversions/aicortex-core)](https://pypi.org/project/aicortex-core/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

## What is AI Cortex?

AI Cortex gives you a single, clean Python interface to **hundreds of language models** — Llama, Mistral, Gemma, DeepSeek, Qwen, and more — running on community-hosted cloud servers or your own local Ollama instance. No accounts. No credit cards. No rate limits.

Whether you're building a chatbot, a code assistant, a research tool, or an AI-powered app, AI Cortex handles the model discovery, server routing, and API compatibility so you don't have to.

```python
from aicortex import chat

# That's it. One line of Python, any model, any server.
response = chat("Explain neural networks like I'm five.")
print(response)
```

## ✨ Why AI Cortex?

| Feature | What it means for you |
|---|---|
| 🆓 **100% Free** | No API keys, no billing, no subscriptions — ever |
| 🤖 **Any Model** | Llama, Mistral, Gemma, DeepSeek, Qwen, and more |
| 🌐 **Cloud or Local** | Community-hosted cloud endpoints or your own Ollama server |
| ⚡ **Streaming** | Real-time token streaming for responsive UIs |
| 🔌 **OpenAI-Compatible** | Drop-in replacement for `openai` client apps |
| 🛡️ **Type-Safe** | Full type hints, stubs, and IDE autocomplete |
| 🔧 **Production Ready** | Automatic failover, multi-server routing, error handling |
| 📦 **Lightweight** | One dependency (`ollama`) for the core package |

## 🚀 Get Started in 60 Seconds

```bash
pip install aicortex-core
```

```python
from aicortex import chat, models, families

# Chat with any model
print(chat("What is the speed of light?"))

# Discover what's available
print(families())   # ['llama', 'mistral', 'gemma', 'deepseek', 'qwen']
print(models("mistral"))  # ['mistral:7b', 'mistral:instruct', ...]
```

→ **[Full Quick Start Guide](quickstart.md)**

## 📚 Documentation

### Getting Started
- [Installation](installation.md) — install options, requirements, and verification
- [Quick Start](quickstart.md) — your first chat in 5 minutes
- [Basic Usage](usage.md) — parameters, patterns, and error handling

### Core Reference
- [Core API](api.md) — complete function and class reference
- [Streaming](streaming.md) — real-time token streaming guide
- [Model Management](models.md) — families, discovery, metadata

### Deployment
- [Server Mode](server.md) — OpenAI-compatible REST API server
- [Tools](tools.md) — endpoint validation, model fetch/resolve/apply pipeline

### Contributing
- [Contributing Guide](contributing.md) — how to submit issues and PRs
- [Development Setup](development.md) — local dev environment, tests, CI

## 🏗️ Architecture at a Glance

```
aicortex/
├── chat()          ← Your main entry point
├── api.py          ← Ollama client, model registry, server routing
├── chat.py         ← Stream / StreamEvent types
├── models/         ← Bundled model metadata (JSON per family)
└── tools/
    ├── check_models.py    ← Validate live Ollama endpoints
    ├── fetch_models.py    ← Pull model lists from valid endpoints
    ├── resolve_models.py  ← Merge fetched data with IP metadata
    ├── apply_valid_models.py  ← Write resolved models into family JSONs
    └── server.py          ← OpenAI-compatible FastAPI proxy
```

## 📄 License

AI Cortex is released under the [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.html).
You can use it freely in open-source and commercial projects.
