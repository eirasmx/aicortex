# 🤝 Contributing to AI Cortex

Thank you for your interest in contributing! AI Cortex is open-source and we welcome contributions of all kinds.

## Quick Start

```bash
# Fork the repo, then:
git clone https://github.com/YOUR_USERNAME/aicortex.git
cd aicortex
python -m venv venv && source venv/bin/activate
pip install -e .[dev,server]
```

## Development Workflow

```bash
git checkout -b feature/your-feature    # create a branch
# ... make changes ...
black aicortex tests                    # format
mypy aicortex                           # type check
flake8 aicortex tests                   # lint
pytest --cov=aicortex                   # test
git commit -m "feat: your feature"      # commit (Conventional Commits)
git push origin feature/your-feature    # push
# open a Pull Request on GitHub
```

## Code Standards

- **Style** — PEP 8, enforced by Black (88 char line limit)
- **Types** — type hints on all function signatures, `mypy --strict` must pass
- **Docstrings** — Google-style docstrings on all public functions and classes
- **Tests** — new code requires tests; maintain 90%+ coverage
- **Commits** — use [Conventional Commits](https://conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `chore:`

## What Goes Where

| Type of change | Update |
|---|---|
| New public function | `__init__.py`, type stub, `docs/api.md`, tests |
| New model family | `aicortex/models/<family>.json`, `docs/models.md` |
| New tool | `aicortex/tools/`, `aicortex/tools/__init__.py`, `docs/tools.md` |
| Bug fix | The relevant module + regression test |
| Docs only | The relevant file in `docs/` |

## Full Contributor Guide

See **[docs/contributing.md](docs/contributing.md)** for the complete guide, including:
- Detailed environment setup
- PR checklist and template
- Issue reporting templates
- Code of conduct
- Recognition policy

## Questions?

Open a [Discussion](https://github.com/eirasmx/aicortex/discussions) or [Issue](https://github.com/eirasmx/aicortex/issues) on GitHub.
