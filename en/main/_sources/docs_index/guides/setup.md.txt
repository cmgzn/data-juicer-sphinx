# Enable This Template for Your Project

## 1. Prerequisites

Ensure your project meets the following requirements:

- Uses Git for version control
- Python 3.11 or higher
- Has branches or tags that require documentation (e.g., `main`, `v1.5.0`, etc.)

## 2. Integrate into Your Project

### Method A: Direct Copy (for local testing)

```bash
# Clone the template repository
git clone https://github.com/datajuicer/data-juicer-sphinx.git

# Copy docs/sphinx_doc into your project
cp -r data-juicer-sphinx/docs/sphinx_doc your-project/docs/

# Please skip your custom files during copying to avoid overwriting them
```

### Method B: Use GitHub Actions (for automatic deployment)

See [Section 5](#5-github-actions-automatic-deployment)

## 3. Customization

### 3.1 Set Project Information

Configure via environment variables at build time:

```bash
export PROJECT="your-project-name"        # e.g., data-juicer-hub
export PACKAGE_DIR="your-project-src"     # Package directory for API docs
export HTML_TITLE="Your Project Title"    # e.g., Data Juicer Hub (optional)
export MIN_VERSION="v0.0.1"               # Build documentation starting from this version (optional)
```

Or set these in your GitHub Actions workflow (see Section 5).

### 3.2 Customize Key Files

Customize the following files according to your project's needs:

```
docs/sphinx_doc/source/
├── index.rst              # English homepage: project introduction + top navigation (DOCS/API)
├── index_ZH.rst           # Chinese homepage: project introduction + top navigation (DOCS/API)
├── docs_index/
│   ├── index.rst          # English documentation index
│   └── index_ZH.rst       # Chinese documentation index
└── api.rst                # API documentation index (if needed)
```

**Example: `index.rst`**
```rst
.. Project Introduction
.. Usually just include README.md directly
.. include:: README.md
   :parser: myst_parser.sphinx_

.. Top Navigation
.. It's recommended to keep only DOCS and API here to avoid cluttering the header navigation
.. toctree::
   :maxdepth: 2
   :caption: DOCS

   docs_index/index

.. toctree::
   :maxdepth: 2
   :caption: API

   api
```

### 3.3 Configure External Links

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
  
  your-new-project:          # Add your project here
    repo_name: your-repo-name
    display_name: Your Display Name

link_order:                  # Controls the display order of external links
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

## 4. Local Build and Testing

### 4.1 Install Dependencies

```bash
cd your-project
pip install .
```

Or using `uv` (recommended):
```bash
uv pip install .
```

### 4.2 Build Documentation

```bash
cd docs/sphinx_doc

# Basic build: only builds main branch, with API docs enabled
PROJECT="your-project" python build_versions.py

# Build all valid tags (>= v1.4.0)
PROJECT="your-project" python build_versions.py --tags

# Build specific tags
PROJECT="your-project" python build_versions.py --tags v1.5.0 v1.6.0

# Build specific branches
PROJECT="your-project" python build_versions.py --branches main dev

# Disable API documentation generation
PROJECT="your-project" python build_versions.py --no-api-doc

# Build English documentation only
PROJECT="your-project" python build_versions.py --languages en

# Full example: build main and dev branches + all tags, with API docs enabled
PROJECT="your-project" python build_versions.py \
    --branches main dev \
    --tags \
    --languages en zh_CN
```

### 4.3 View Build Results

```bash
# Start a local server
python -m http.server 8000 --directory build

# Visit http://localhost:8000/en/main/index.html
# or     http://localhost:8000/zh_CN/main/index_ZH.html
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
      HTML_TITLE: Your Project Title  # Optional: Custom title
      MIN_VERSION: v0.0.0             # Optional: Minimum version
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
      - name: Install dependencies with uv # Install project dependencies
        run: |
          uv pip install --system --upgrade pip
          uv pip install --system -e .[all]

      - name: Fetch Data-Juicer Sphinx Template # Pull template and overwrite docs/sphinx_doc, skip custom files
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
        if: ${{ github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/')) }}
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/sphinx_doc/build
          cname: your-domain.com  # Optional: Use custom domain
```

**Enable GitHub Pages**:
1. Go to your repository Settings → Pages
2. Set Source to the `gh-pages` branch
3. After saving, visit `https://your-domain.github.io/your-project/`