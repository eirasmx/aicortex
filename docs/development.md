# 🔧 Development Guide

> **Advanced reference for AI Cortex contributors and maintainers.** This guide covers the internal architecture, testing strategy, CI/CD pipeline, and everything else you need to understand the codebase deeply and contribute effectively.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Internal API Design](#internal-api-design)
- [Streaming Architecture](#streaming-architecture)
- [Model Management](#model-management)
- [Tool System](#tool-system)
- [Type System](#type-system)
- [Testing Strategy](#testing-strategy)
- [Performance Optimization](#performance-optimization)
- [Error Handling](#error-handling)
- [Build and Distribution](#build-and-distribution)
- [CI/CD Pipeline](#cicd-pipeline)
- [Security Considerations](#security-considerations)
- [Future Enhancements](#future-enhancements)

## 🏗️ Architecture Overview

### Package Structure

```
aicortex/
├── __init__.py              # Public API: chat(), families(), models(), etc.
├── api.py                   # Internal _OllamaAPI wrapper class
├── chat.py                  # chat() function, Stream, StreamEvent
├── models/                  # Model metadata — one JSON file per family
│   ├── llama.json
│   ├── mistral.json
│   ├── deepseek.json
│   ├── qwen.json
│   └── gemma.json
├── tools/                   # Administrative utilities
│   ├── __init__.py
│   ├── check_models.py      # Step 1: validate server endpoints
│   ├── fetch_models.py      # Step 2: fetch current model lists
│   ├── resolve_models.py    # Step 3: merge and deduplicate metadata
│   ├── apply_valid_models.py # Step 4: write updated JSON files
│   └── server.py            # FastAPI OpenAI-compatible server
└── stubs/                   # Type stubs for IDE autocomplete
    ├── __init__.pyi
    ├── chat.pyi
    ├── tools.pyi
    └── tools/
        ├── __init__.pyi
        ├── server.pyi
        ├── check_models.pyi
        ├── fetch_models.pyi
        ├── resolve_models.pyi
        └── apply_valid_models.pyi
```

### Layer Responsibilities

| Layer | Module | Responsibility |
|---|---|---|
| **Public API** | `__init__.py` | Clean, stable surface — thin wrappers only |
| **Internal API** | `api.py` | All Ollama interactions; `_OllamaAPI` class |
| **Chat Interface** | `chat.py` | `chat()` dispatch, `Stream`, `StreamEvent` |
| **Model Metadata** | `models/*.json` | Offline-available model info and server lists |
| **Tools** | `tools/` | Administrative pipeline for keeping metadata current |
| **Server** | `tools/server.py` | FastAPI proxy that exposes an OpenAI-compatible REST API |
| **Type Stubs** | `stubs/` | IDE support — mirrors the public surface in `.pyi` |

### Design Principles

- **Single responsibility** — each module and class does one thing well
- **Layered access** — public callers never touch `_OllamaAPI` directly
- **Fail gracefully** — server errors cascade to failover, not crashes
- **Type safety everywhere** — `mypy --strict` must pass with zero errors
- **No state in modules** — all state lives in instances or is passed explicitly

## 🔌 Internal API Design

### `_OllamaAPI` Class

`api.py` contains the single internal class that owns all Ollama communication. Public functions in `__init__.py` create instances of this class and delegate to it; they never call `ollama` directly.

```python
class _OllamaAPI:
    """Internal wrapper around the Ollama Python client.

    Not part of the public API — subject to change without notice.
    All public functions should go through this class for Ollama access.
    """

    def __init__(self, base_url: str = "http://localhost:11434") -> None: ...

    # Chat
    def _chat(self, model: str, prompt: str, **kwargs: Any) -> dict[str, Any]: ...
    def _stream_chat(self, model: str, prompt: str, **kwargs: Any) -> Iterator[dict]: ...

    # Model discovery
    def list_families(self) -> list[str]: ...
    def list_models(self, family: str | None = None) -> list[str]: ...
    def get_model_info(self, model: str) -> dict[str, Any]: ...

    # Server discovery
    def list_model_servers(self, model: str) -> list[dict[str, Any]]: ...
    def get_server_info(self, model: str, server_url: str | None = None) -> dict[str, Any]: ...
    def build_api_request(self, model: str, prompt: str, **kwargs: Any) -> dict[str, Any]: ...
    def get_llm_params(self, model: str) -> dict[str, Any]: ...
    def get_random_llm_params(self, model: str) -> dict[str, Any]: ...
```

### Server Selection Strategy

When a function needs to talk to an Ollama server, `_OllamaAPI` follows this selection order:

1. **Explicit URL** — if the caller passes `server_url`, use it directly
2. **Metadata servers** — try servers listed in the model's JSON entry, in order
3. **Default localhost** — fall back to `http://localhost:11434` if all else fails

Each candidate is health-checked before use. A server is considered healthy if it responds to the model list endpoint within the configured timeout. Failed servers are skipped with a warning log; they do not raise exceptions unless all candidates are exhausted.

## 📡 Streaming Architecture

### Event System

Streaming is modeled as a sequence of typed events rather than a raw byte stream. This makes it easy to filter, transform, and compose stream consumers.

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class EventType(str, Enum):
    START = "start"     # Generation has begun
    TOKEN = "token"     # One text chunk has arrived
    END = "end"         # Generation completed successfully
    ERROR = "error"     # An error occurred during generation


@dataclass
class StreamEvent:
    type: EventType
    content: str | None = None   # Token text (only on TOKEN events)
    index: int | None = None     # Token position in the sequence
    model: str | None = None     # Which model generated this event
    done: bool = False           # True on the final event


@dataclass
class Stream:
    """Iterable container for a streamed model response."""
    events: list[StreamEvent] = field(default_factory=list)

    def __iter__(self) -> Iterator[StreamEvent]: ...
    def add(self, event: StreamEvent) -> None: ...
    def text(self) -> str:
        """Concatenate all TOKEN event content into a single string."""
        ...
```

### Event Flow Diagram

```
chat("...", stream=True)
        │
        ▼
  _OllamaAPI._stream_chat()
        │
        │  yields raw Ollama dicts
        ▼
  _build_stream_events()          ← converts raw → StreamEvent
        │
        │  yields StreamEvents:
        │    StreamEvent(type=START)
        │    StreamEvent(type=TOKEN, content="Hello")
        │    StreamEvent(type=TOKEN, content=" world")
        │    ...
        │    StreamEvent(type=END, done=True)
        ▼
  Stream object returned to caller
```

### Consuming a Stream

```python
# Option 1: iterate events
stream = chat("Tell me a story", stream=True)
for event in stream:
    if event.type == EventType.TOKEN:
        print(event.content, end="", flush=True)

# Option 2: collect full text after completion
text = stream.text()
```

## 📦 Model Management

### JSON Metadata Schema

Each model family has a JSON file in `aicortex/models/`. The schema:

```json
{
  "family": "llama",
  "models": [
    {
      "name": "llama3.2:3b",
      "family": "llama",
      "size": "2.0 GB",
      "parameters": "3B",
      "quantization": "Q4_K_M",
      "context_length": 131072,
      "description": "Compact, fast Llama 3.2 variant for everyday tasks.",
      "tags": ["chat", "fast", "lightweight"],
      "servers": [
        {
          "url": "http://localhost:11434",
          "status": "unknown"
        }
      ]
    }
  ]
}
```

### Model Loading

Model metadata is loaded from the bundled JSON files at import time. The files are included in the wheel via `package_data` in `setup.py`, so they are always available — no network required to get model info.

The `status` field in each server entry is not authoritative at load time; it reflects the last-known state from when the tools pipeline was run. Live health checks are done lazily at call time.

### Keeping Metadata Current

The four-tool pipeline in `aicortex/tools/` is the mechanism for refreshing model metadata:

```
check_models → fetch_models → resolve_models → apply_valid_models
```

Run it periodically (e.g., as a cron job or pre-release step) to keep the bundled JSON files accurate. See `docs/tools.md` for the full pipeline reference.

## 🔨 Tool System

### Tool Categories

| Tool | Module | Purpose |
|---|---|---|
| **check_models** | `tools/check_models.py` | Validate that server URLs are reachable and serving models |
| **fetch_models** | `tools/fetch_models.py` | Fetch the current model list from each live server |
| **resolve_models** | `tools/resolve_models.py` | Merge fetched data with existing metadata; deduplicate |
| **apply_valid_models** | `tools/apply_valid_models.py` | Write the resolved data back to `aicortex/models/*.json` |
| **server** | `tools/server.py` | Run the FastAPI OpenAI-compatible proxy |

### Tool Design Constraints

- **CLI-runnable** — every tool exposes a `main()` function and a `__main__` guard so it can be invoked directly: `python -m aicortex.tools.check_models`
- **Composable** — each tool's output is suitable input for the next step; they can be chained in shell pipelines or called programmatically
- **Error-resilient** — network failures for individual servers are logged and skipped; they do not abort the whole pipeline
- **Concurrent** — `check_models` and `fetch_models` use `asyncio` / `ThreadPoolExecutor` to probe multiple servers in parallel

## 🔷 Type System

### Stub Files

Every public symbol has a corresponding `.pyi` stub. Stubs live in `aicortex/stubs/` and are included in the wheel so IDEs get autocomplete without needing to read the implementation.

The stub for `chat()` uses `@overload` to express the conditional return type:

```python
# aicortex/stubs/chat.pyi
from typing import overload
from .models import Stream

@overload
def chat(prompt: str, *, stream: Literal[False] = ..., **kwargs: Any) -> str: ...

@overload
def chat(prompt: str, *, stream: Literal[True], **kwargs: Any) -> Stream: ...

def chat(prompt: str, *, stream: bool = False, **kwargs: Any) -> str | Stream: ...
```

### Type Checking

- `mypy aicortex` must exit 0 with strict mode enabled
- `--no-implicit-optional` and `--disallow-untyped-defs` are both on
- All `Any` uses must be justified with a `# type: ignore[...]` comment

Run:
```bash
mypy aicortex --strict
```

## 🧪 Testing Strategy

### Test Structure

```
tests/
├── __init__.py
├── conftest.py               # Fixtures: mock_ollama_client, sample_model_data
├── test_chat.py              # chat(), Stream, StreamEvent behavior
├── test_api.py               # _OllamaAPI methods and error paths
├── test_models.py            # JSON loading, model lookup, family listing
├── test_tools.py             # check → fetch → resolve → apply pipeline
├── test_server.py            # FastAPI endpoints, request/response shapes
└── fixtures/
    ├── mock_responses.json   # Canned Ollama API responses
    └── test_models.json      # Minimal model JSON for unit tests
```

### Test Categories

**Unit tests** — test one function or method in isolation, all external I/O mocked:

```python
def test_get_model_info_returns_correct_family(mock_ollama_client):
    info = get_model_info("llama3.2:3b")
    assert info["family"] == "llama"
```

**Integration tests** — test multi-step workflows, still mocked at the network boundary:

```python
def test_tool_pipeline_produces_valid_json(mock_server_responses):
    check_models.run()
    fetch_models.run()
    resolve_models.run()
    apply_valid_models.run()
    data = json.loads(Path("aicortex/models/llama.json").read_text())
    assert "models" in data
```

**Server tests** — test FastAPI endpoints using `httpx.AsyncClient` with the app mounted in-process (no real network):

```python
@pytest.mark.asyncio
async def test_chat_completions_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/v1/chat/completions", json={
            "model": "llama3.2:3b",
            "messages": [{"role": "user", "content": "Hello"}]
        })
    assert response.status_code == 200
    assert "choices" in response.json()
```

### Tox Environments

`tox.ini` defines these environments:

| Environment | Command | Purpose |
|---|---|---|
| `py38` – `py312` | `pytest + mypy + black + flake8` | Full suite on each Python version |
| `docs` | `sphinx-build -b html docs docs/_build/html` | Build and check docs |
| `build` | `python -m build && twine check dist/*` | Verify the package builds cleanly |

Run all environments:
```bash
tox
```

Run a single environment:
```bash
tox -e py311
tox -e docs
```

## ⚡ Performance Optimization

### Caching

- **Model metadata** — JSON files are read once at import time and held in module-level dicts; subsequent calls hit the in-memory cache
- **Server health** — health check results are cached for a configurable TTL (default: 60 seconds) to avoid re-checking on every call
- **Client instances** — `ollama.Client` instances are reused per base URL rather than created per call

### Concurrency

- `check_models` and `fetch_models` use `asyncio.gather()` to probe all servers concurrently — O(1) wall time regardless of server count
- `apply_valid_models` writes each family JSON file atomically (write to temp, then rename) to prevent partial writes
- Streaming events are yielded lazily — no buffering of the full response before returning to the caller

### Memory

- Model JSON files are loaded into `dict` objects, not `dataclass` instances, to minimize overhead for large model lists
- Streaming yields one event at a time; the full token sequence is only materialized if the caller calls `.text()`

## ❗ Error Handling

### Exception Hierarchy

```python
class AICortexError(Exception):
    """Base exception for all AI Cortex errors."""

class ModelNotFoundError(AICortexError):
    """Raised when the requested model is not available on any server."""

class ServerError(AICortexError):
    """Raised when all configured servers are unreachable."""

class ValidationError(AICortexError):
    """Raised when input parameters fail validation."""

class StreamError(AICortexError):
    """Raised when an error occurs during streaming."""
```

### Recovery Strategies

| Failure | Strategy |
|---|---|
| One server unreachable | Log warning, try next server in list |
| All servers unreachable | Raise `ServerError` |
| Model not in metadata | Raise `ModelNotFoundError` with suggestions |
| Stream interrupted mid-response | Emit `StreamEvent(type=ERROR)`, raise `StreamError` |
| Malformed model JSON | Log error, skip that family; do not crash the import |

## 📦 Build and Distribution

### Building

```bash
# Install build tools
pip install build twine

# Build source distribution and wheel
python -m build

# Verify the built package
twine check dist/*
```

This produces:
- `dist/aicortex_core-1.0.2.tar.gz` — source distribution
- `dist/aicortex_core-1.0.2-py3-none-any.whl` — universal wheel

### What's in the Wheel

- All `aicortex/` Python source files
- `aicortex/models/*.json` — bundled model metadata
- `aicortex/stubs/**/*.pyi` — type stubs for IDE support
- `README.md`, `LICENSE`

### Versioning

AI Cortex follows [Semantic Versioning](https://semver.org/):
- **MAJOR** — breaking changes to the public API
- **MINOR** — new features, backward-compatible
- **PATCH** — bug fixes, backward-compatible

The version is defined in `setup.py` and should be updated before every release.

## 🔁 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and pull request to `main` and `develop`.

### Jobs

**`test`** — matrix over Python 3.8, 3.9, 3.10, 3.11, 3.12:

```
1. Checkout code
2. Install: pip install -e .[dev,server]
3. Lint: flake8 aicortex tests
4. Format check: black --check aicortex tests
5. Type check: mypy aicortex
6. Test: pytest --cov=aicortex --cov-report=xml
7. Upload coverage to Codecov
```

**`build`** — runs after `test` passes:

```
1. Build package: python -m build
2. Store wheel and sdist as workflow artifacts
```

**`release`** — runs on push to `main` only, after `test` and `build`:

```
1. Build package
2. Publish to PyPI via pypa/gh-action-pypi-publish
   (requires PYPI_API_TOKEN secret in repo settings)
```

### Release Process

1. Update version in `setup.py`
2. Update `CHANGELOG.md` with release notes
3. Commit: `git commit -m "chore: release v1.1.0"`
4. Tag: `git tag v1.1.0 && git push --tags`
5. Merge to `main` — CI publishes to PyPI automatically

## 🔒 Security Considerations

### Input Validation

- All model identifiers are validated against the known model list before use
- Server URLs are validated as valid HTTP/HTTPS URLs before connection attempts
- Prompt strings are passed through as-is to Ollama — sanitization is the caller's responsibility

### Network

- HTTPS is supported and recommended for remote servers
- All HTTP requests have an explicit timeout (default: 30 seconds)
- No credentials or tokens are logged, even at debug level

### Dependencies

- Core dependencies are minimal: `ollama` and `pydantic` only
- Server extras (`fastapi`, `uvicorn`) are optional
- Dependencies are pinned with minimum versions in `setup.py`; no upper bounds to avoid false conflicts

### Known Limitations

- The server mode has no built-in authentication — do not expose it on a public network without a reverse proxy that adds auth
- Model outputs are not filtered — responsible for downstream content handling lies with the application
- HTTP (not HTTPS) is the default for localhost Ollama connections — this is intentional for zero-config local use

## 🚀 Future Enhancements

### Planned

| Feature | Description | Priority |
|---|---|---|
| Async API | Full `async`/`await` support for `chat()` | High |
| Plugin system | Extensible tool architecture for third-party additions | Medium |
| Metrics export | Prometheus-compatible metrics endpoint on the server | Medium |
| Configuration files | YAML/TOML config for server URLs, defaults, timeouts | Medium |
| Caching layer | Optional Redis backend for response caching | Low |
| Multi-modal | Image and audio input support (pending Ollama support) | Low |

### Architecture Notes for Future Contributors

- The `_OllamaAPI` class is intentionally not async to keep the public API simple. When async support is added, it should be a parallel `_AsyncOllamaAPI` class, not a modification of the existing one.
- The model metadata JSON format is considered stable. New fields may be added; existing fields must not be removed without a major version bump.
- The tool pipeline is designed to be run by maintainers, not end users. If a use case arises for user-facing model management, it should be a new public API function, not a thin wrapper around the tools.
