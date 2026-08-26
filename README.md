# Data-Juicer Sphinx Documentation Template

This is a unified documentation build template designed for the Data-Juicer ecosystem. Built on Sphinx and the bundled `data_juicer_theme` (a modern custom theme), it provides multi-version and multi-language documentation capabilities, ensuring consistent documentation appearance and user experience across all subprojects.

## Features

- **Unified Appearance**: All subprojects share the same documentation theme and styling.
- **Multi-Version Support**: Automatically builds documentation for multiple Git branches and tags, with incremental CI deployment (only the changed version is rebuilt; immutable tags are built once).
- **Multi-Language Support**: Supports both English and Chinese by default.
- **Ecosystem Interconnectivity**: Enables seamless navigation between different project documentations via header external links.
- **Markdown-Friendly**: Automatically discovers and integrates Markdown documents within the project.
- **AI Assistant**: Built-in "Ask Juicer" widget (floating input bar, select-to-ask, resizable side panel) with streaming responses, thinking-mode and tool-call display; activated automatically when `JUICER_API_URL` is configured.

## Project Structure

```
data-juicer-sphinx/
├── data_juicer_sphinx_theme/                    # Custom Sphinx theme package
│   ├── theme.conf / layout.html / search.html   # Theme definition and templates
│   └── static/                                  # Theme CSS/JS
├── docs/
│   └── sphinx_doc/                              # Sphinx documentation build directory
│       ├── build_versions.py                    # Multi-version build script (main entry point)
│       ├── make.bat / Makefile                  # Build scripts
│       ├── redirect.html                        # Redirect page
│       └── source/                              # Documentation source files
│           ├── conf.py                          # Sphinx configuration file
│           ├── custom_myst.py                   # Custom MyST extension
│           ├── external_links.yaml              # External project link configuration
│           ├── index.rst / index_ZH.rst               # Home page (customization recommended)
│           ├── api.rst                          # API documentation index (customization recommended)
│           └── _static/                         # Static assets
│               ├── images/                      # Logos and icons
│               ├── ask-ai-widget.js / .css      # Bundled Ask-AI widget and styles
│               └── ask-ai-modules/              # Widget modular sources + rollup build
├── guides/                                      # Usage guides
├── pyproject.toml                               # Project configuration (registers the theme)
├── README.md                                    
└── README_ZH.md                                 
```

## Quick Start

Build the simplest English Data-Juicer Sphinx documentation (without API docs):

```bash
git clone https://github.com/datajuicer/data-juicer-sphinx.git

uv pip install .

cd docs/sphinx_doc
export PROJECT="data-juicer-sphinx"
python build_versions.py -A -l en
```

## Documentation

Read the docs online: [datajuicer.github.io/data-juicer-sphinx](https://datajuicer.github.io/data-juicer-sphinx/en/main/index.html)

- [Enable the Template](guides/setup.md) — integrate, customize, and build locally
- [Deploy with GitHub Actions](guides/deployment.md) — incremental CI deployment
- [Writing Documentation](guides/writing.md) — content, media assets, and link mapping
- [FAQ](guides/faq.md)
- [How It Works](docs/how_it_works.md) — build internals and the incremental pipeline

## Contribution Guide

Contributions and improvements to this template are warmly welcomed! ❤