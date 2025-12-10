# 测试文档

这是一个测试文档。它位于根目录下的 `docs/test_ZH.md`，具有中英两个版本。

如果你能看到这个文档，说明 [脚本](sphinx_doc/build_versions.py) 成功在 Sphinx 构建前，将项目中的外部 Markdown 文档复制到了 Sphinx 源目录（`docs/sphinx_doc/source/docs_index/`），从而使其能被正常构建。

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

## 媒体资源引用

### 图片显示

你可以在 Markdown 文档中使用相对路径直接引用项目中的图片、视频等媒体资源：

```markdown
![示例图片](imgs/TEST.png)
```

![示例图片](imgs/TEST.png)

或者：

```markdown
<img src="imgs/TEST.png" width="70%" height="70%">
```

<img src="imgs/TEST.png" width="70%" height="70%">

### 资源管理配置

为了确保媒体资源能够正确地被构建和显示，需要配置 [extra_assets.yaml](sphinx_doc/source/extra_assets.yaml) 文件，指定媒体资源存放的路径（相对于项目根目录）。例如：

```yaml
assets_dirs:
  - docs/imgs
  - resources
```

构建脚本会自动将这些目录中的资源文件复制到 Sphinx 构建输出目录中，确保在最终生成的网站中可以正常访问这些资源。

### 使用说明

1. **放置资源文件**：将图片、视频等媒体文件放在项目根目录下的指定文件夹中（如 `imgs/`）
2. **配置资源路径**：在 [extra_assets.yaml](sphinx_doc/source/extra_assets.yaml) 中声明资源所在的目录
3. **引用资源**：在 Markdown 中使用相对路径引用，例如 `imgs/TEST.png`
4. **本地预览**：在本地编辑时，相对路径应能正确指向资源文件
5. **自动映射**：构建脚本会自动处理路径映射，构建后的网页中也能正确显示资源

这样配置后，你既可以在本地编辑器中预览文档和图片，也能保证生成的网站中所有媒体资源都能显示。

## 仓库内链接的自动映射

### 什么是仓库内链接？

在 Markdown 中，你可以使用相对路径引用代码库中的其他文件，例如：

```markdown
[查看脚本](sphinx_doc/build_versions.py)
[配置文件](sphinx_doc/source/extra_assets.yaml)
[相关文档](docs/README.md)
```

这些 `./xxx` 或 `path/to/file` 形式的相对链接指向的是项目仓库内部的文件

### 自动映射

构建脚本会自动将这些仓库内的相对链接转换为 GitHub 仓库的链接。首先，请确保已经正确设置以下环境变量：

```bash
export PROJECT = "your-project-name"        # 例如：data-juicer-hub
export REPO_OWNER = "your-repo-owner"       # 例如：datajuicer
```

原始的相对链接：

```markdown
[脚本](sphinx_doc/build_versions.py)
```

[conf.py](sphinx_doc/source/conf.py) 会自动计算该文件相对于项目根目录的路径，并映射为 GitHub 链接：

```
https://github.com/datajuicer/data-juicer-sphinx/blob/main/docs/sphinx_doc/build_versions.py
```

如果启用了多版本构建，链接还会自动指向对应的版本分支。
