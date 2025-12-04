# 测试文档

这是一个测试文档。它位于根目录下的 `docs/test_ZH.md`，具有中英两个版本。

如果你能看到这个文档，说明 [构建脚本](sphinx_doc/build_versions.py) 成功在 Sphinx 构建前，将项目中的外部 Markdown 文档复制到了 Sphinx 源目录（`docs/sphinx_doc/source/docs_index/`），从而使其能被正常构建。

> 💡 **集成规则**：  
> 构建脚本会自动扫描项目根目录下除 `outputs/`、`sphinx_doc/` 和 `.github/` 之外的所有文件夹，并将其中的 Markdown 文件（`.md`）复制到文档构建源目录中。  
> 因此，你可以在 `docs/`、`guides/`、`src/` 等任意未被排除的目录中编写 Markdown 文档。

只要在 `docs/sphinx_doc/source/docs_index/index.rst`（英文）和 `index_ZH.rst`（中文）中通过 `:glob:` 正确引用这些文件，通常它们会像本文档一样出现在最终站点中。

## 示例

```rst
====
文档
====

该项目的文件

.. toctree::
   :maxdepth: 2
   :glob:

   guides/*

.. toctree::
   :maxdepth: 2
   :glob:
   
   docs/*
```

`docs/*` 将匹配所有从 `docs/` 目录复制过来的文件，例如本文档。