# How It Works

Background on how the template builds and publishes documentation. New users can skip this page; it is mainly useful when debugging builds or extending the template.

## Isolated Build Environment (Git Worktree)

- For each version (branch/tag), the build script creates an independent Git worktree at `.worktrees/<version>`.
- Worktrees are cleaned up automatically after building (unless `KEEP_WORKTREES=True` is set in `docs/sphinx_doc/build_versions.py`), so the main working directory is never polluted.

## Documentation Content Aggregation

- The build scans the whole worktree and collects all `.md` and `.rst` files (excluding directories like `outputs`, `sphinx_doc`, and `.github`). See [Writing Documentation](../guides/writing.md) for the full rules.
- Collected files are copied into the unified Sphinx source directory `docs/sphinx_doc/source/`.
- (Customized for Data-Juicer operator documentation) For subdirectories under `operators/`, corresponding `index.rst` and `index_ZH.rst` files are generated automatically to provide categorized operator indexes.

## Incremental CI Pipeline

Each CI run builds only the version that actually changed:

1. **Event routing**: a push to `main` builds `main`; a tag push builds that tag only; a PR builds the checked-out code as a `preview` artifact; `workflow_dispatch` with `full: true` rebuilds every version.
2. **Single-version build**: `build_versions.py` builds just that version (all languages) into `build/<lang>/<version>/`.
3. **versions.json**: the full version list (`main` + valid tags) is regenerated and published to the site root, so the version switcher on every page always shows up-to-date entries at runtime.
4. **Merge-publish**: the deploy step uses `keep_files: true`, overwriting only the version directory built in this run while previously published versions stay untouched. A full rebuild deploys without `keep_files`, replacing the whole site and cleaning up orphan files.

See [Deploy with GitHub Actions](../guides/deployment.md) for the complete workflow configuration.
