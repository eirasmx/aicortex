# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# ─────────────────────────────────────────────────────────────────────────────
# Project Information
# ─────────────────────────────────────────────────────────────────────────────

project = "AI Cortex"
copyright = "2025, Erasmus A. Junior — GNU LGPLv3"
author = "Erasmus A. Junior"
release = "1.0.3"
version = "1.0"

# ─────────────────────────────────────────────────────────────────────────────
# General Configuration
# ─────────────────────────────────────────────────────────────────────────────

extensions = [
    # Render Markdown files as Sphinx pages
    "myst_parser",
    # Auto-generate API reference from docstrings
    "sphinx.ext.autodoc",
    # Generate summary tables for modules/classes
    "sphinx.ext.autosummary",
    # Link to Python stdlib and other Sphinx projects
    "sphinx.ext.intersphinx",
    # "View source" links on every page
    "sphinx.ext.viewcode",
    # NumPy / Google-style docstring support
    "sphinx.ext.napoleon",
    # $math$ rendering
    "sphinx.ext.mathjax",
    # Copy button on code blocks
    "sphinx_copybutton",
]

# MyST (Markdown) options
myst_enable_extensions = [
    "colon_fence",       # ::: directives
    "deflist",           # Definition lists
    "fieldlist",         # Field lists
    "html_admonition",   # <div class="admonition"> blocks
    "html_image",        # <img> tags
    "tasklist",          # - [ ] checkboxes
    "dollarmath",        # $math$ inline
]
myst_heading_anchors = 4

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
}
autosummary_generate = True

# Napoleon (docstring style)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_attr_annotations = True

# Intersphinx — link to external docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Source suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ─────────────────────────────────────────────────────────────────────────────
# HTML Output — sphinx-book-theme
# ─────────────────────────────────────────────────────────────────────────────

html_theme = "sphinx_book_theme"

html_theme_options = {
    "repository_url": "https://github.com/eirasmx/aicortex",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "repository_branch": "main",
    "path_to_docs": "docs",
    "home_page_in_toc": True,
    "show_navbar_depth": 2,
    "show_toc_level": 2,
    "logo": {
        "text": (
            '<div id="sidebar_mini">'
            '<a href="https://pepy.tech/projects/aicortex-core" style="margin-right:8px;">'
            '<img src="https://static.pepy.tech/badge/aicortex-core" alt="Downloads"></a>'
            '<a href="https://pypi.org/project/aicortex-core/">'
            '<img src="https://img.shields.io/pypi/v/aicortex-core" alt="PyPI Version"></a>'
            "</div>"
        ),
    },
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/eirasmx/aicortex",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/aicortex-core/",
            "icon": "fa-brands fa-python",
        },
    ],
    "extra_footer": (
        "<p>Built with ❤️ by Erasmus A. Junior &mdash; "
        "Licensed under <a href='https://www.gnu.org/licenses/lgpl-3.0.html'>GNU LGPLv3</a></p>"
    ),
}

html_title = "AI Cortex"
html_short_title = "AICortex"
html_favicon = "_static/favicon.ico"  # add your own favicon
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# Copy button settings — strip shell prompts and output lines
copybutton_prompt_text = r">>> |\.\.\. |\$ |> "
copybutton_prompt_is_regexp = True

# ─────────────────────────────────────────────────────────────────────────────
# Pygments (code highlighting)
# ─────────────────────────────────────────────────────────────────────────────

pygments_style = "monokai"
pygments_dark_style = "monokai"
