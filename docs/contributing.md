# 🤝 Contributing to AI Cortex

> **AI Cortex is an open-source project and we welcome contributions of all kinds** — bug fixes, new features, documentation improvements, model additions, and more. This guide walks you through everything you need to get started.

## 📋 Table of Contents

- [Before You Start](#before-you-start)
- [Setting Up Your Environment](#setting-up-your-environment)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Adding Models & Features](#adding-models--features)
- [Community](#community)

## 🏁 Before You Start

### Find Something to Work On

Browse the [Issues](https://github.com/eirasmx/aicortex/issues) page and look for:

| Label | Meaning |
|---|---|
| `good first issue` | Great for newcomers — well-scoped with clear requirements |
| `help wanted` | Maintainers are actively seeking contributions here |
| `bug` | Something is broken and needs a fix |
| `enhancement` | New feature or improvement to existing behavior |
| `documentation` | Docs-only change, no code needed |

If you have an idea that isn't tracked yet, open an issue to discuss it before building — this avoids duplicate work and ensures alignment with project goals.

## 🛠️ Setting Up Your Environment

### Prerequisites

- **Python 3.8+** (3.11 recommended)
- **Git**
- **Ollama** — for running integration tests against a real server

### Clone and Install

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/aicortex.git
cd aicortex

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. Install in editable mode with all dev dependencies
pip install -e .[dev,server]

# 4. (Optional) Install pre-commit hooks for automatic quality checks
pip install pre-commit
pre-commit install
```

### Verify Your Setup

```bash
# Run the test suite — all tests should pass
pytest

# Check types
mypy aicortex

# Check formatting
black --check aicortex tests

# Run everything via tox
tox
```

If everything passes, you're ready to contribute.

## 🔄 Development Workflow

### 1. 🌿 Create a Branch

Branch names should be descriptive and follow this convention:

```bash
# New feature
git checkout -b feature/async-chat-support

# Bug fix (reference the issue number)
git checkout -b fix/123-streaming-timeout

# Documentation update
git checkout -b docs/update-quickstart
```

### 2. ✏️ Make Your Changes

Write your code following the [Code Standards](#code-standards) below. As you work:

- Keep commits small and focused — one logical change per commit
- Write tests alongside new code, not after
- Update documentation if your change affects public behavior

### 3. 🧪 Run Quality Checks

Before committing, run the full quality suite:

```bash
# Format code (auto-fixes in place)
black aicortex tests

# Static type checking
mypy aicortex

# Lint for common issues
flake8 aicortex tests

# Run tests with coverage
pytest --cov=aicortex --cov-report=term-missing
```

All checks must pass before submitting a PR.

### 4. 📝 Commit Your Changes

Use [Conventional Commits](https://conventionalcommits.org/) format:

```bash
git commit -m "feat: add async support for chat()"
git commit -m "fix: resolve streaming timeout on slow connections"
git commit -m "docs: add examples for tool pipeline usage"
git commit -m "test: add unit tests for resolve_models edge cases"
git commit -m "refactor: extract server discovery into helper"
git commit -m "chore: bump ollama dependency to 0.3.0"
```

**Prefix reference:**

| Prefix | Use for |
|---|---|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation only |
| `style:` | Formatting, no logic changes |
| `refactor:` | Code restructuring without behavior change |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance tasks, dependency updates |

### 5. 🚀 Push and Open a PR

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub against the `main` branch.

## 📐 Code Standards

### Python Style

- Follow **PEP 8** — enforced by `black` and `flake8`
- Maximum line length: **88 characters** (Black default)
- **Type hints required** for all function parameters and return values
- **Docstrings required** for all public functions, classes, and methods

### Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Functions & methods | `snake_case` | `get_model_info()` |
| Classes | `PascalCase` | `StreamEvent` |
| Constants | `UPPER_CASE` | `DEFAULT_HOST` |
| Private members | `_leading_underscore` | `_parse_response()` |
| Modules | `snake_case` | `fetch_models.py` |

### Import Order

```python
# 1. Standard library
import os
import json
from pathlib import Path
from typing import Iterator, List

# 2. Third-party
import ollama
from pydantic import BaseModel

# 3. Local imports
from .api import _OllamaAPI
from .chat import Stream, StreamEvent
```

### Docstring Format

Use **Google-style docstrings**:

```python
def chat(prompt: str, *, model: str = "llama3.2:3b", stream: bool = False) -> str:
    """Send a prompt to a model and return its response.

    A high-level convenience function that handles model selection,
    server discovery, and response parsing automatically.

    Args:
        prompt: The text prompt to send to the model.
        model: Model identifier in ``family:size`` format.
            Defaults to ``"llama3.2:3b"``.
        stream: If ``True``, returns a :class:`Stream` object instead
            of a plain string. Defaults to ``False``.

    Returns:
        The model's response as a plain string, or a :class:`Stream`
        object if ``stream=True``.

    Raises:
        ModelNotFoundError: If the specified model is not available
            on any configured server.
        ServerError: If all servers are unreachable.

    Example:
        >>> response = chat("What is machine learning?")
        >>> print(response)
        'Machine learning is a subset of artificial intelligence...'
    """
```

## 🧪 Testing

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and mock setup
├── test_chat.py             # chat() function tests
├── test_api.py              # _OllamaAPI class tests
├── test_models.py           # Model loading and metadata tests
├── test_tools.py            # Tool pipeline tests
├── test_server.py           # FastAPI server endpoint tests
└── fixtures/
    ├── mock_responses.json  # Pre-recorded API responses
    └── test_models.json     # Minimal model metadata for tests
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch
from aicortex import chat, families, models


class TestChat:
    """Tests for the chat() function."""

    def test_chat_returns_string(self, mock_ollama_client):
        """chat() should return a non-empty string for valid prompts."""
        response = chat("Hello")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_chat_with_explicit_model(self, mock_ollama_client):
        """chat() should accept a model parameter."""
        response = chat("Hello", model="mistral:7b")
        assert isinstance(response, str)

    def test_chat_raises_on_invalid_model(self, mock_ollama_client):
        """chat() should raise ModelNotFoundError for unknown models."""
        from aicortex.exceptions import ModelNotFoundError
        with pytest.raises(ModelNotFoundError):
            chat("Hello", model="nonexistent:model")
```

### Mocking Ollama

Tests must not require a live Ollama server. Use the shared fixture from `conftest.py`:

```python
@pytest.fixture
def mock_ollama_client():
    """Patch ollama.Client with a pre-configured mock."""
    with patch("ollama.Client") as mock_class:
        instance = Mock()
        instance.chat.return_value = {
            "message": {"content": "Mocked response"},
            "done": True,
        }
        instance.list.return_value = {
            "models": [{"name": "llama3.2:3b"}, {"name": "mistral:7b"}]
        }
        mock_class.return_value = instance
        yield instance
```

### Coverage Requirements

- Aim for **90%+ coverage** on all new code
- Check your coverage before submitting:

```bash
pytest --cov=aicortex --cov-report=term-missing --cov-fail-under=90
```

## 📖 Documentation

If your change affects user-facing behavior, update the relevant docs in `docs/`.

| Changed | Update |
|---|---|
| Public function signature or behavior | `docs/api.md` |
| Streaming behavior | `docs/streaming.md` |
| Installation or dependencies | `docs/installation.md` |
| Model metadata schema | `docs/models.md` |
| Tool pipeline | `docs/tools.md` |
| Server endpoints | `docs/server.md` |

Also update any relevant code examples in `examples/` to reflect the change.

### Building the Docs Locally

```bash
# Install Sphinx dependencies
pip install -e .[dev]

# Build HTML docs
tox -e docs

# Open in browser (macOS)
open docs/_build/html/index.html
```

## 📬 Pull Request Process

### PR Checklist

Before submitting, confirm:

- [ ] All tests pass: `pytest`
- [ ] Types check: `mypy aicortex`
- [ ] Code is formatted: `black --check aicortex tests`
- [ ] No new lint errors: `flake8 aicortex tests`
- [ ] New code has tests with adequate coverage
- [ ] Documentation updated for any public API changes
- [ ] Commit messages follow Conventional Commits format
- [ ] PR description clearly explains the change and its motivation

### PR Description Template

```
## Summary
Brief description of what this PR does and why.

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (existing functionality changes)
- [ ] Documentation update
- [ ] Refactor / internal improvement

## Testing
Describe how you tested the changes:
- Unit tests added/updated: yes/no
- Tested against live Ollama server: yes/no
- Coverage delta: +X%

## Related Issues
Closes #123
```

### Review Process

1. ✅ **Automated CI** — Tests, types, formatting, and linting run automatically
2. 👀 **Code review** — A maintainer reviews your changes within a few days
3. 💬 **Address feedback** — Respond to comments and push updates as needed
4. ✅ **Approval & merge** — Once approved, a maintainer merges the PR

## 🐛 Reporting Issues

### Bug Reports

When reporting a bug, include:

```
**Describe the bug**
A clear description of what is happening vs. what you expected.

**To Reproduce**
Minimal code to reproduce the issue:

    import aicortex
    response = aicortex.chat("Hello", model="llama3.2:3b")
    # -> Error: ...

**Environment**
- OS: macOS 14.3 / Ubuntu 22.04 / Windows 11
- Python: 3.11.2
- AI Cortex: 1.0.2
- Ollama: 0.3.1

**Full traceback**
Paste the complete error output here.
```

### Feature Requests

When requesting a feature:

```
**Problem**
What are you trying to do that you can't currently do?

**Proposed Solution**
What API or behavior would solve it?
    response = aicortex.chat("Hello", timeout=30)  # example

**Alternatives Considered**
What workarounds have you tried?
```

## ➕ Adding Models & Features

### Adding a New Model Family

1. Create a new JSON file in `aicortex/models/` — see `llama.json` for the schema
2. Follow the existing field structure: `name`, `family`, `size`, `parameters`, `servers`
3. Add at least one server entry to make the model immediately usable
4. Test model loading: `from aicortex import models; print(models("yourfamily"))`
5. Update `docs/models.md` with the new family

### Adding a New Tool

1. Create a new module in `aicortex/tools/`
2. Export it in `aicortex/tools/__init__.py`
3. Add type stubs in `aicortex/stubs/tools/` if it's part of the public API
4. Add CLI entry point in `setup.py` if the tool should be runnable from the command line
5. Write tests in `tests/test_tools.py`
6. Document it in `docs/tools.md`

### Adding a New Public Function

1. Implement in the appropriate module (`api.py`, `chat.py`, etc.)
2. Export from `aicortex/__init__.py`
3. Add type stub to `aicortex/stubs/__init__.pyi`
4. Write tests
5. Document in `docs/api.md` with full parameter table and example

## 🌍 Community

### Getting Help

- **Documentation** — Start at [aicortex.readthedocs.io](https://aicortex.readthedocs.io/)
- **Issues** — For bugs and feature requests: [github.com/eirasmx/aicortex/issues](https://github.com/eirasmx/aicortex/issues)
- **Discussions** — For questions and ideas: [github.com/eirasmx/aicortex/discussions](https://github.com/eirasmx/aicortex/discussions)

### Code of Conduct

We are committed to a welcoming, inclusive community. In all interactions:

- Be respectful and patient — people are here to learn and help
- Give constructive, specific feedback rather than vague criticism
- Assume good intent unless clearly demonstrated otherwise
- Help newcomers get oriented rather than dismissing their questions

### Recognition

All contributors are recognized in release notes and the GitHub contributor graph. Significant contributions may be highlighted in the `CHANGELOG.md`.

Thank you for helping make AI Cortex better. Every contribution — no matter how small — is valued. 🚀
