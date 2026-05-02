# 📋 Changelog

All notable changes to AI Cortex are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
AI Cortex adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Version format:** `MAJOR.MINOR.PATCH`
> - **MAJOR** — breaking changes to the public API
> - **MINOR** — new features, backward-compatible
> - **PATCH** — bug fixes and minor improvements, backward-compatible

---

## [1.0.2] — 2026-05-02

### 🐛 Fixed

- Typo in `setup.py` project URL: `masteer` → `master` in the Changelog link

---

## [1.0.1] — 2026-05-02

### 📖 Changed

- Completed full documentation rewrite across all `docs/` pages — API reference,
  usage guide, streaming guide, models guide, server guide, tools guide,
  contributing guide, and development guide
- Added `docs/examples/` section with annotated examples for chat, streaming,
  server, and the tools pipeline
- Rewrote all Python docstrings in `aicortex/` source files
- Moved Sphinx config from `source/conf.py` to `docs/conf.py`; removed `source/` directory
- Rewrote `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`

---

## [1.0.0] — 2026-05-02

> 🎉 **Initial production release** — AI Cortex is live.

### ✨ Added

#### Core Chat API
- `chat(prompt, *, model, stream, **kwargs)` — unified interface for sending prompts to any Ollama-compatible model
- Sync mode returns a plain `str`; `stream=True` returns a `Stream` object
- Automatic server discovery and health-checking on every call
- Failover to next available server when the primary is unreachable

#### Streaming
- `Stream` — iterable container for streamed model responses
- `StreamEvent` — typed event dataclass with `type`, `content`, `index`, `model`, and `done` fields
- `EventType` enum: `START`, `TOKEN`, `END`, `ERROR`
- `Stream.text()` — convenience method to collect all token content into a single string

#### Model Discovery
- `families()` — list all available model families (llama, mistral, deepseek, qwen, gemma)
- `models(family)` — list all model identifiers within a family
- `get_model_info(model)` — return full metadata dict for a specific model
- `list_model_servers(model)` — return all known server URLs for a model
- `get_server_info(model, server_url)` — return health and capability info for a specific server

#### Request Building
- `build_api_request(model, prompt, **kwargs)` — construct a raw Ollama-compatible request dict
- `get_llm_params(model)` — return the recommended parameter set for a model
- `get_random_llm_params(model)` — return a randomized parameter set for creative variation

#### Bundled Model Families
- **Llama** — Meta's Llama 3.x family: 3B, 8B, 70B, 405B variants
- **Mistral** — Mistral AI models: 7B, Mixtral 8x7B, Mixtral 8x22B
- **Deepseek** — DeepSeek models: 1.3B, 6.7B, 33B, 67B
- **Qwen** — Alibaba Qwen models: 0.5B, 1.8B, 7B, 14B, 72B
- **Gemma** — Google Gemma models: 2B, 7B

#### Tool Pipeline
- `check_models` — validate server endpoints concurrently; produces a health report
- `fetch_models` — fetch current model lists from all live servers
- `resolve_models` — merge fetched data with existing metadata; deduplicate entries
- `apply_valid_models` — atomically write resolved metadata to `aicortex/models/*.json`

#### OpenAI-Compatible Server
- FastAPI-based proxy server exposing OpenAI-compatible REST endpoints
- `POST /v1/chat/completions` — drop-in replacement for OpenAI's chat completions
- `GET /v1/models` — list available models in OpenAI format
- `GET /health` — server health check endpoint
- Works with any existing OpenAI SDK or client library
- CLI entry point: `aicortex-server`

#### Type System
- Complete type stubs in `aicortex/stubs/` for all public symbols
- `@overload` declarations for `chat()` expressing the conditional return type
- `mypy --strict` passes with zero errors

#### Documentation
- Full Sphinx documentation at [aicortex.readthedocs.io](https://aicortex.readthedocs.io/)
- API reference, quickstart, usage guide, streaming guide, models guide, server guide, tools guide

### 🔧 Technical

- **Python support** — 3.8, 3.9, 3.10, 3.11, 3.12
- **Dependencies** — `ollama>=0.1.0`, `pydantic>=2.0.0`; server extras add `fastapi` and `uvicorn`
- **CI matrix** — all supported Python versions on Ubuntu, with flake8, black, mypy, pytest, and Codecov
- **Distribution** — source distribution and universal wheel published to PyPI as `aicortex-core`

---

## Pre-Release

*No pre-release versions. This is the first public release.*

---

## 📌 How to Read This Changelog

Each release section uses these headings:

| Heading | Meaning |
|---|---|
| `✨ Added` | New features |
| `🔄 Changed` | Changes to existing functionality |
| `⚠️ Deprecated` | Features that will be removed in a future release |
| `🗑️ Removed` | Features removed in this release |
| `🐛 Fixed` | Bug fixes |
| `🔒 Security` | Security-related fixes |

---

[1.0.2]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.2
[1.0.1]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.1
[1.0.0]: https://github.com/eirasmx/aicortex/releases/tag/v1.0.0
