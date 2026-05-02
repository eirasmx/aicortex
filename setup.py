"""Setup script for AI Cortex."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aicortex-core",
    version="1.0.2",
    author="Erasmus A. Junior",
    author_email="eirasmx@duck.com",
    maintainer="Erasmus A. Junior",
    maintainer_email="eirasmx@duck.com",
    description=(
        "AI Cortex: An LLM API toolkit for any language model through Ollama servers. "
        "Access Gemma, Mistral, Deepseek, Qwen, Llama, and more - completely free, zero-signup, zero API keys. "
        "Unified chat API, real-time streaming, multi-server orchestration, and OpenAI-compatible endpoints."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eirasmx/aicortex",
    project_urls={
        "Documentation": "https://aicortex.readthedocs.io/",
        "Repository": "https://github.com/eirasmx/aicortex",
        "Issues": "https://github.com/eirasmx/aicortex/issues",
        "Changelog": "https://github.com/eirasmx/aicortex/blob/master/CHANGELOG.md",
    },
    license="LGPL-3.0-or-later",
    packages=find_packages(include=["aicortex*"]),
    package_data={
        "aicortex": ["models/*.json", "stubs/*.pyi", "stubs/**/*.pyi"],
    },
    python_requires=">=3.8",
    install_requires=[
        "ollama>=0.1.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "server": [
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.20.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
            "tox>=4.0.0",
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
        "all": [
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.20.0",
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
            "tox>=4.0.0",
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aicortex-server=aicortex.tools.server:run_server",
        ],
    },
    keywords=[
        "llm",
        "language-model",
        "ai",
        "chat",
        "api",
        "openai-compatible",
        "free",
        "no-signup",
        "local-models",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
    ],
    zip_safe=False,
    include_package_data=True,
)