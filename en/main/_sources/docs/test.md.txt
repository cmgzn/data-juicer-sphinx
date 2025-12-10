# Test Document

This is a test document. It is located at `docs/test.md` in the root directory and has both Chinese and English versions.

If you can see this document, it means the [script](sphinx_doc/build_versions.py) successfully copied external Markdown documents from the project to the Sphinx source directory (`docs/sphinx_doc/source/docs_index/`) before the Sphinx build, enabling them to be built normally.

> 💡 **Integration Rules**:  
> The build script automatically scans all folders in the project root directory except `outputs/`, `sphinx_doc/`, and `.github/`, and copies Markdown files (`.md`) within them to the documentation build source directory.  
> Therefore, you can write Markdown documents in any unexcluded directories such as `docs/`, `guides/`, `src/`, etc.

As long as these files are correctly referenced through `:glob:` in `docs/sphinx_doc/source/docs_index/index.rst` (English) and `index_ZH.rst` (Chinese), they will typically appear in the final site like this document.

## Example

```rst
====
Docs
====

Files in this project

.. toctree::
   :maxdepth: 2
   :glob:

   guides/*

.. toctree::
   :maxdepth: 2
   :glob:
   
   docs/*
```

`docs/*` will match all files copied from the `docs/` directory, such as this document.

## Media Asset References

### Image Display

You can directly reference images, videos, and other media resources in your project using relative paths in Markdown documents:

```markdown
![Example Image](imgs/TEST.png)
```

![Example Image](imgs/TEST.png)

Or:

```markdown
<img src="imgs/TEST.png" width="70%" height="70%">
```

<img src="imgs/TEST.png" width="70%" height="70%">

### Asset Management Configuration

To ensure media resources are correctly built and displayed, you need to configure the [extra_assets.yaml](sphinx_doc/source/extra_assets.yaml) file to specify the paths where media resources are stored (relative to the project root). For example:

```yaml
assets_dirs:
  - docs/imgs
  - resources
```

The build script will automatically copy resource files from these directories to the Sphinx build output directory, ensuring that the resources can be accessed normally in the final generated website.

### Usage Instructions

1. **Place resource files**: Put image, video, and other media files in specified folders in the project root directory (such as `imgs/`)
2. **Configure resource paths**: Declare the directories containing resources in [extra_assets.yaml](sphinx_doc/source/extra_assets.yaml)
3. **Reference resources**: Use relative paths in Markdown, for example `imgs/TEST.png`
4. **Local preview**: When editing locally, relative paths should correctly point to resource files
5. **Automatic mapping**: The build script automatically handles path mapping, ensuring resources display correctly in the built website

With this configuration, you can preview both documents and images in your local editor while also ensuring that all media resources display correctly in the generated website.

## Automatic Mapping of In-Repository Links

### What are In-Repository Links?

In Markdown, you can reference other files in the code repository using relative paths, for example:

```markdown
[View Script](sphinx_doc/build_versions.py)
[Configuration File](sphinx_doc/source/extra_assets.yaml)
[Related Documentation](docs/README.md)
```

These relative links in the form of `./xxx` or `path/to/file` point to files inside the project repository.

### Automatic Mapping

The build script automatically converts these in-repository relative links to GitHub repository links. First, make sure you have correctly set the following environment variables:

```bash
export PROJECT = "your-project-name"        # For example: data-juicer-hub
export REPO_OWNER = "your-repo-owner"       # For example: datajuicer
```

Original relative link:

```markdown
[Script](sphinx_doc/build_versions.py)
```

[conf.py](sphinx_doc/source/conf.py) automatically calculates the file's path relative to the project root and maps it to a GitHub link:

```
https://github.com/datajuicer/data-juicer-sphinx/blob/main/docs/sphinx_doc/build_versions.py
```

If multi-version builds are enabled, the links will also automatically point to the corresponding version branches.
