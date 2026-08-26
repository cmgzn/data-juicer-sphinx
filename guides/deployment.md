# Deploy with GitHub Actions

The recommended way to use this template: your project's CI pulls the template, builds the docs, and publishes them to GitHub Pages automatically.

Deployment is **incremental**: a push to `main` builds only `main`, a tag push builds only that tag (tags are immutable and never need rebuilding), and PRs build only the checked-out code. Previously published versions stay untouched on `gh-pages` (`keep_files: true`). Use `workflow_dispatch` with `full: true` to rebuild every version (refreshes the theme on old tags and cleans orphan files).

## 1. Create the Workflow

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
    inputs:
      full:
        description: "Full rebuild of all versions (refreshes theme on old tags, cleans orphan files)"
        type: boolean
        default: false

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
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            # PR preview: build the checked-out code only, no worktree
            python build_versions.py --current preview
          elif [ "${{ github.event_name }}" = "workflow_dispatch" ] && [ "${{ inputs.full }}" = "true" ]; then
            # Manual full rebuild: every branch and tag (orphan cleanup + theme refresh)
            python build_versions.py --tags
          elif [[ "${GITHUB_REF}" == refs/tags/* ]]; then
            # Tag push: tags are immutable, build only this tag
            python build_versions.py --branches --tags "${GITHUB_REF_NAME}"
          else
            # Branch push (main) or dispatch without full: build only branches
            python build_versions.py
          fi

      - name: Generate versions.json
        if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}
        run: |
          cd docs/sphinx_doc
          python build_versions.py --emit-versions-json

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
        if: ${{ (github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/'))) || github.event_name == 'workflow_dispatch' }}
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/sphinx_doc/build
          # Incremental deploy: keep previously published versions untouched.
          # A full rebuild (full=true) replaces the whole site to clean orphans.
          keep_files: ${{ !(github.event_name == 'workflow_dispatch' && inputs.full) }}
          cname: your-domain.com  # Optional: if using custom domain
```

> Notes on incremental deployment:
> - The version switcher loads its version list from `versions.json` at runtime, so pages of old versions automatically see newly published tags.
> - `keep_files` never deletes files: pages removed from a rebuilt version may linger until the next full rebuild.
> - Old tags keep the theme they were published with; run a full rebuild to refresh them.

## 2. Enable GitHub Pages

1. Go to repository Settings → Pages
2. Select `gh-pages` branch as Source
3. Save and visit `https://your-domain.github.io/your-project/`
