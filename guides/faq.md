# Frequently Asked Questions

## Q1: Build fails with "module not found" error

**A**: Ensure all dependencies are installed before building:

```bash
uv pip install .
```

## Q2: API documentation isn't generated

**A**: Check the following:

- Ensure you didn't use the `--no-api-doc` or `-A` flags
- Verify your project contains importable Python modules
- Confirm the `CODE_ROOT` environment variable is correctly set

## Q3: External links aren't displayed

**A**:

1. Verify that `external_links.yaml` is configured correctly
2. Ensure the `PROJECT` environment variable is properly set
3. Check the browser console for JavaScript errors

## Q4: Chinese documentation links don't exist

**A**: Ensure:

- Chinese documentation files end with `_ZH.md` or `_ZH.rst`
- `index_ZH.rst` exists and is correctly configured

## Q5: Page doesn't exist after switching versions

**A**: Documentation structures may differ between versions:

- Older versions might lack certain new pages
- Version switching tries to access the same path; if unavailable, it redirects to the homepage

## Q6: Orphan pages left on the site, or old tags still use an outdated theme

**A**: Incremental deployment never deletes files, and tag pages keep the theme they were published with. Run a manual full rebuild to fix both: trigger `workflow_dispatch` with `full: true` (see [Deploy with GitHub Actions](deployment.md)). It rebuilds every version and replaces the whole site, cleaning up orphan files and refreshing the theme everywhere.
