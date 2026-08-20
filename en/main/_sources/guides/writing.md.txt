# Writing Documentation

How to add content to your documentation site: where to put Markdown files, how to reference media assets, and how in-repository links are handled.

## Markdown Collection Rules

The build script automatically scans all folders in the project root directory except `outputs/`, `sphinx_doc/`, and `.github/`, and copies the Markdown files (`.md`) within them to the Sphinx source directory (`docs/sphinx_doc/source/`, preserving their relative paths) before building. You can therefore write Markdown documents in any non-excluded directory such as `docs/`, `guides/`, or `src/`.

For a file to appear on the site, it must be referenced by a toctree in `docs/sphinx_doc/source/index.rst` (English) and `index_ZH.rst` (Chinese). For example:

```rst
.. include:: README.md
   :parser: myst_parser.sphinx_

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/setup
   guides/deployment

.. toctree::
   :maxdepth: 2
   :caption: Reference
   :glob:

   docs/*
```

Explicit entries give you full control over the sidebar order; a `:glob:` toctree collects every copied file under that directory automatically (in alphabetical order). Each captioned toctree renders as an always-expanded group in the left sidebar.

## Media Asset References

### Image Display

You can directly reference images, videos, and other media resources in your project using relative paths in Markdown documents:

```markdown
![Example Image](../docs/imgs/TEST.png)
```

![Example Image](../docs/imgs/TEST.png)

Or:

```markdown
<img src="../docs/imgs/TEST.png" width="70%" height="70%">
```

<img src="../docs/imgs/TEST.png" width="70%" height="70%">

### Asset Management Configuration

To ensure media resources are correctly built and displayed, configure the [extra_assets.yaml](../docs/sphinx_doc/source/extra_assets.yaml) file to specify the paths where media resources are stored (relative to the project root). For example:

```yaml
assets_dirs:
  - docs/imgs
  - resources
```

The build script will automatically copy resource files from these directories to the Sphinx build output directory, ensuring that the resources can be accessed normally in the final generated website.

### Usage Instructions

1. **Place resource files**: Put image, video, and other media files in specified folders in the project root directory (such as `imgs/`)
2. **Configure resource paths**: Declare the directories containing resources in [extra_assets.yaml](../docs/sphinx_doc/source/extra_assets.yaml)
3. **Reference resources**: Use relative paths in Markdown, for example `imgs/TEST.png`
4. **Local preview**: When editing locally, relative paths should correctly point to resource files
5. **Automatic mapping**: The build script automatically handles path mapping, ensuring resources display correctly in the built website

With this configuration, you can preview both documents and images in your local editor while also ensuring that all media resources display correctly in the generated website.

## Automatic Mapping of In-Repository Links

### What are In-Repository Links?

In Markdown, you can reference other files in the code repository using relative paths, for example:

```markdown
[View Script](../docs/sphinx_doc/build_versions.py)
[Configuration File](../docs/sphinx_doc/source/extra_assets.yaml)
```

These relative links in the form of `./xxx` or `path/to/file` point to files inside the project repository.

### Automatic Mapping

The build script automatically converts these in-repository relative links to GitHub repository links. First, make sure you have correctly set the following environment variables:

```bash
export PROJECT="your-project-name"        # For example: data-juicer-hub
export REPO_OWNER="your-repo-owner"       # For example: datajuicer
```

Original relative link:

```markdown
[Script](../docs/sphinx_doc/build_versions.py)
```

[conf.py](../docs/sphinx_doc/source/conf.py) automatically calculates the file's path relative to the project root and maps it to a GitHub link:

```
https://github.com/datajuicer/data-juicer-sphinx/blob/main/docs/sphinx_doc/build_versions.py
```

If multi-version builds are enabled, the links will also automatically point to the corresponding version branches.

> Note: links ending in `.md`/`.rst` are resolved to the built documentation pages instead of GitHub, and media files (images, videos, ...) stay relative so they load from the built site.

## Rendering Reference

Common Markdown syntax supported out of the box:

- ~~Strikethrough~~
- **Bold text**: **This is bold**
- *Italic text*: *This is italic*
- ***Bold and italic***: ***This is both***
- `Inline code`: `print("hello")`
- > Blockquote: > This is a quote
- [Link](https://example.com): [Example Link](https://example.com)
