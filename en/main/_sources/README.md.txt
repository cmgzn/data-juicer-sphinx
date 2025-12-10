# Data-Juicer Sphinx Documentation Template

This is a unified documentation build template designed for the Data-Juicer ecosystem. Built on Sphinx and pydata-sphinx-theme, it provides multi-version and multi-language documentation capabilities, ensuring consistent documentation appearance and user experience across all subprojects.

## Features

- **Unified Appearance**: All subprojects share the same documentation theme and styling.
- **Multi-Version Support**: Automatically builds documentation for multiple Git branches and tags.
- **Multi-Language Support**: Supports both English and Chinese by default.
- **Ecosystem Interconnectivity**: Enables seamless navigation between different project documentations via header external links.
- **Markdown-Friendly**: Automatically discovers and integrates Markdown documents within the project.

## Project Structure

```
data-juicer-sphinx/
├── docs/
│   └── sphinx_doc/                              # Sphinx documentation build directory
│       ├── build_versions.py                    # Multi-version build script (main entry point)
│       ├── make.bat / Makefile                  # Build scripts
│       ├── redirect.html                        # Redirect page
│       └── source/                              # Documentation source files
│           ├── conf.py                          # Sphinx configuration file
│           ├── custom_myst.py                   # Custom MyST extension
│           ├── external_links.yaml              # External project link configuration
│           ├── index.rst / index_ZH.rst         # Home page (customization recommended)
│           ├── docs_index/                      # Documentation index directory
│           │   ├── index.rst / index_ZH.rst     # Documentation index page (customization recommended)
│           │   └── ...                          # Automatically copied Markdown files
│           ├── api.rst                          # API documentation index (customization recommended)
│           ├── _static/                         # Static assets
│           │   ├── custom.css                   # Custom styles
│           │   └── images/                      # Logos and icons
│           └── _templates/                      # Custom templates
│               └── version-language-switcher.html
├── guides/                                      # Usage guides
├── pyproject.toml                               # Project configuration
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

[Here](https://datajuicer.github.io/data-juicer-sphinx/en/main/index.html)

## Core Principles

### **Isolated Build Environment (Git Worktree)**
- Creates an independent Git worktree for each version (branch/tag) at `.worktrees/<version>`.
- Automatically cleans up after building (unless `KEEP_WORKTREES=True` is set in `docs/sphinx_doc/build_versions.py`) to avoid polluting the main working directory.

### **Documentation Content Aggregation**
- Automatically scans the entire worktree to collect all `.md` and `.rst` files (excluding directories like `outputs`, `sphinx_doc`, `.github`, etc.).
- Copies these files into a unified Sphinx source directory: `docs/sphinx_doc/source/docs_index/`.
- (Customized for Data-Juicer operator documentation) For subdirectories under `operators/`, automatically generates corresponding `index.rst` and `index_ZH.rst` files to facilitate categorized operator indexing.

## Frequently Asked Questions

### Q1: Build fails with "module not found" error

**A**: Ensure all dependencies are installed before building:
```bash
uv pip install .
```

### Q2: API documentation isn't generated

**A**: Check the following:
- Ensure you didn't use the `--no-api-doc` or `-A` flags
- Verify your project contains importable Python modules
- Confirm the `CODE_ROOT` environment variable is correctly set

### Q3: External links aren't displayed

**A**:
1. Verify that `external_links.yaml` is configured correctly
2. Ensure the `PROJECT` environment variable is properly set
3. Check the browser console for JavaScript errors

### Q4: Chinese documentation links don't exist

**A**: Ensure:
- Chinese documentation files end with `_ZH.md` or `_ZH.rst`
- `index_ZH.rst` exists and is correctly configured

### Q5: Page doesn't exist after switching versions

**A**: Documentation structures may differ between versions:
- Older versions might lack certain new pages
- Version switching attempts to access the same path; if unavailable, it redirects to the homepage

## Contribution Guide

Contributions and improvements to this template are warmly welcomed! ❤