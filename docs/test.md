# TEST DOCUMENT

This is a test document. It resides at `docs/test.md` in the root directory and exists in both Chinese and English versions.

If you can see this document, it means the [build script](sphinx_doc/build_versions.py) successfully copied external Markdown documents from the project into the Sphinx source directory (`docs/sphinx_doc/source/docs_index/`) before the Sphinx build process, enabling them to be properly included in the final documentation.

> 💡 **Integration Rules**:  
> The build script automatically scans all directories under the project root—excluding `outputs/`, `sphinx_doc/`, and `.github/`—and copies any Markdown files (`.md`) into the documentation source directory used for building.  
> Therefore, you can write Markdown documentation in any non-excluded directory such as `docs/`, `guides/`, `src/`, etc.

As long as these files are correctly referenced using `:glob:` in `docs/sphinx_doc/source/docs_index/index.rst` (English) and `index_ZH.rst` (Chinese), they will typically appear on the final site just like this document.

## Example

```rst
====
DOCS
====

the documentation for the project

.. toctree::
   :maxdepth: 2
   :glob:

   guides/*

.. toctree::
   :maxdepth: 2
   :glob:
   
   docs/*
```

The pattern `docs/*` will match all files copied from the `docs/` directory, for example this very document.