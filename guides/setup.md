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

See [Deploy with GitHub Actions](deployment.md) — the recommended approach.

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

Or set in GitHub Actions workflow (see [Deploy with GitHub Actions](deployment.md)).

### 3.2 Customize Key Files

Customize the following files according to your project needs:

```
docs/sphinx_doc/source/
├── index.rst              # English homepage: README content + grouped sidebar navigation
├── index_ZH.rst           # Chinese homepage: README content + grouped sidebar navigation
├── api.rst                # API documentation index
├── external_links.yaml    # External project links
└── extra_assets.yaml      # Additional resources
```

**Example: `index.rst`**
```rst
.. Home page content
.. Usually just include README.md directly
.. include:: README.md
   :parser: myst_parser.sphinx_

.. Sidebar navigation
.. Captioned glob toctrees render as always-expanded groups (e.g. "Guides",
.. "Documentation") in the left sidebar of the theme
.. toctree::
   :maxdepth: 2
   :caption: Guides
   :glob:

   guides/*

.. toctree::
   :maxdepth: 2
   :caption: Documentation
   :glob:

   docs/*

.. toctree::
   :hidden:

   api
```

> Tip: a `:glob:` toctree collects files automatically but sorts them alphabetically; list entries explicitly when the reading order matters (as this template's own `index.rst` does).

> Note: For usage of extra_assets.yaml, see [Writing Documentation](writing.md)

### 3.3 Configure External Project Links

Edit `docs/sphinx_doc/source/external_links.yaml`:

```yaml
url_template: "https://{repo_name}.github.io/{project}/{language}/{version}/index.html"

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

> `url_template` represents the template for external links, where `{repo_owner}`, `{project}`, and `{language}` will be replaced with actual values.  
> `{version}` will be replaced with `main`.


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

## Next Step

Ready to publish? Continue with [Deploy with GitHub Actions](deployment.md).
