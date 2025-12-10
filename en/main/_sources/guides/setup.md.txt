# Enable This Template for Your Project

## 1. Prerequisites

Ensure your project meets the following conditions:

- Uses Git for version control
- Python 3.11+
- Has branches or tags that need documentation (e.g., `main`, `v1.5.0`, etc.)

## 2. Integration into Your Project

### Method A: Direct Copy (for local testing)

```bash
# Clone the template repository
git clone https://github.com/datajuicer/data-juicer-sphinx.git

# Copy docs/sphinx_doc to your project
cp -r data-juicer-sphinx/docs/sphinx_doc your-project/docs/

# Skip your custom files during copying to avoid overwriting
```

### Method B: Using GitHub Actions (for automatic deployment)

See [Section 5](#5-github-actions-automatic-deployment)

## 3. Custom Configuration

### 3.1 Set Project Information

Set via environment variables during build:

```bash
export PROJECT="your-project-name"        # e.g.: data-juicer-hub
export REPO_OWNER="your-repo-owner"       # e.g.: datajuicer
export PACKAGE_DIR="your-project-src"     # Package directory for API doc generation (optional)
export HTML_TITLE="Your Project Title"    # e.g.: Data Juicer Hub (optional)
export MIN_TAG="v0.0.1"                   # Specify minimum version to build from (optional)
```

Or set in GitHub Actions workflow (see Section 5).

### 3.2 Customize Key Files

Customize the following files according to your project needs:

```
docs/sphinx_doc/source/
├── index.rst              # English homepage: project intro + header navigation (DOCS/API)
├── index_ZH.rst           # Chinese homepage: project intro + header navigation (DOCS/API)
├── docs_index.rst         # English docs index
├── docs_index_ZH.rst      # Chinese docs index
├── api.rst                # API documentation index
├── external_links.yaml    # External project links
└── extra_assets.yaml      # Additional resources
```

**Example: `index.rst`**
```rst
.. Project Introduction
.. Usually just include README.md directly
.. include:: README.md
   :parser: myst_parser.sphinx_

.. Header Navigation
.. Set multiple toctrees to display multiple navigation items in header
.. It's recommended to keep only DOCS and API to avoid cluttering the header
.. toctree::
   :maxdepth: 2
   :caption: DOCS

   docs_index

.. toctree::
   :maxdepth: 2
   :caption: API

   api
```

> Note: For usage of extra_assets.yaml, see [Test Document](../docs/test.md)

### 3.3 Configure External Project Links

Edit `docs/sphinx_doc/source/external_links.yaml`:

```yaml
url_template: "https://datajuicer.github.io/{project}/{language}/{version}/index.html"

projects:
  data-juicer:
    repo_name: data-juicer
    display_name: Data Juicer
  
  data-juicer-hub:
    repo_name: data-juicer-hub
    display_name: DJ Hub
  
  your-new-project:          # Add your project
    repo_name: your-repo-name
    display_name: Your Display Name

link_order:                  # Control external link display order
  - data-juicer
  - data-juicer-hub
  - your-new-project
```

### 3.4 Customize Logo and Icons

Replace the following file:

```
docs/sphinx_doc/source/_static/images/
└── icon.png     # Your project icon
```

## 4. Local Build and Test

### 4.1 Install Dependencies

```bash
cd your-project
pip install .
```

Or use `uv` (recommended):
```bash
uv pip install .
```

### 4.2 Build Documentation

```bash
cd docs/sphinx_doc

# Basic build: build main branch only, enable API documentation
PROJECT="your-project" python build_versions.py

# Build all valid tags (>= MIN_TAG)
PROJECT="your-project" python build_versions.py --tags

# Build specific tags
PROJECT="your-project" python build_versions.py --tags v1.5.0 v1.6.0

# Build specific branches
PROJECT="your-project" python build_versions.py --branches main dev

# Disable API documentation generation
PROJECT="your-project" python build_versions.py --no-api-doc

# Build English documentation only
PROJECT="your-project" python build_versions.py --languages en

# Complete example: build main and dev branches + all tags, enable API docs
PROJECT="your-project" python build_versions.py \
    --branches main dev \
    --tags \
    --languages en zh_CN
```

### 4.3 View Build Results

```bash
# Start local server
python -m http.server 8000 --directory build

# Visit http://localhost:8000/en/main/index.html
# Or     http://localhost:8000/zh_CN/main/index_ZH.html
```

## 5. GitHub Actions Automatic Deployment

Create `.github/workflows/docs.yml` in your project:

```yaml
name: Deploy Sphinx documentation to Pages

on:
  pull_request:
    types: [opened, synchronize]
    paths:
      - "docs/sphinx_doc/**/*"
  push:
    branches:
      - main
    tags:
      - "v*"
  workflow_dispatch:

jobs:
  pages:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11"]
    env:
      PROJECT: ${{ github.event.repository.name }}
      REPO_OWNER: ${{ github.repository_owner }}
      PACKAGE_DIR: "your-project-src"
      HTML_TITLE: Your Project Title  # Optional: custom title
      MIN_TAG: v0.0.0             # Optional: minimum version
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Fetch full history to support multi-version builds

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@master
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
      - name: Install dependencies with uv # Install your project dependencies
        run: |
          uv pip install --system --upgrade pip
          uv pip install --system -e .[all]

      - name: Fetch Data-Juicer Sphinx Template # Pull template to override docs/sphinx_doc, skip custom files
        run: |
          set -e
          echo "Cloning sphinx template..."
          git clone --depth=1 https://github.com/datajuicer/data-juicer-sphinx.git /tmp/template
          uv pip install --system -e /tmp/template
          if [ -d "docs/sphinx_doc/source" ]; then
            echo "Backing up custom files..."
            mkdir -p /tmp/custom_files
            cp -r docs/sphinx_doc/source /tmp/custom_files
          fi
          echo "Applying template..."
          rm -rf docs/sphinx_doc
          mkdir -p docs
          cp -r /tmp/template/docs/sphinx_doc docs/
          echo "Restoring custom files..."
          cp -rf /tmp/custom_files/source/* docs/sphinx_doc/source
          echo "Done!"
      - name: Get git tags
        run: |
          git fetch --all --tags
          git branch -a
          git tag
      - name: Build documentation
        run: |
          cd docs/sphinx_doc
          python build_versions.py --tags

      - name: Redirect index.html
        run: |
          REPOSITORY_OWNER="${GITHUB_REPOSITORY_OWNER}"
          cd docs/sphinx_doc
          cp ./redirect.html build/index.html
          sed -i "s/\[REPOSITORY_OWNER\]/${REPOSITORY_OWNER}/g" build/index.html
          sed -i "s/\[PROJECT\]/${PROJECT}/g" build/index.html
          cp build/index.html build/404.html
      - name: Upload Documentation
        uses: actions/upload-artifact@v4
        with:
          name: SphinxDoc
          path: "docs/sphinx_doc/build"

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/sphinx_doc/build
          cname: your-domain.com  # Optional: if using custom domain
```

**Enable GitHub Pages**:
1. Go to repository Settings → Pages
2. Select `gh-pages` branch as Source
3. Save and visit `https://your-domain.github.io/your-project/`
