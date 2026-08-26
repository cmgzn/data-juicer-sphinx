# 为你的项目启用本模板

## 1. 准备工作

确保你的项目满足以下条件：

- 使用 Git 进行版本控制
- Python 3.11+
- 有需要生成文档的分支或标签（例如 `main`、`v1.5.0` 等）

## 2. 集成到你的项目

### 方法 A：直接复制（用于本地测试）

```bash
# 克隆模板仓库
git clone https://github.com/datajuicer/data-juicer-sphinx.git

# 复制 docs/sphinx_doc 到你的项目
cp -r data-juicer-sphinx/docs/sphinx_doc your-project/docs/

# 请在复制时跳过你的自定义文件，以免覆盖
```

### 方法 B：使用 GitHub Actions （用于自动部署）

见[使用 GitHub Actions 部署](deployment_ZH.md)——推荐的接入方式。

## 3. 自定义配置

### 3.1 设置项目信息

在构建时通过环境变量设置：

```bash
export PROJECT="your-project-name"        # 例如：data-juicer-hub
export REPO_OWNER="your-repo-owner"       # 例如：datajuicer
export PACKAGE_DIR="your-project-src"     # 生成 API 文档所用的包目录（可选）
export HTML_TITLE="Your Project Title"    # 例如：Data Juicer Hub（可选）
export MIN_TAG="v0.0.1"               # 指定从此版本开始构建（可选）
```

或在 GitHub Actions workflow 中设置（见[使用 GitHub Actions 部署](deployment_ZH.md)）。

### 3.2 自定义关键文件

根据你的项目需求自定义以下文件：

```
docs/sphinx_doc/source/
├── index.rst              # 英文主页：README 内容 + 侧边栏分组导航
├── index_ZH.rst           # 中文主页：README 内容 + 侧边栏分组导航
├── api.rst                # API 文档索引
├── external_links.yaml    # 项目外链
└── extra_assets.yaml      # 额外资源
```

**示例：`index.rst`**
```rst
.. 主页内容
.. 通常直接 include README.md 即可
.. include:: README.md
   :parser: myst_parser.sphinx_

.. 侧边栏导航
.. 带 :caption: 的 :glob: toctree 会在主题左侧边栏中渲染为
.. 默认展开的分组（如 "Guides"、"Documentation"）
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

> 提示：`:glob:` toctree 会自动收集文件，但按字母顺序排列；需要控制阅读顺序时请显式列出条目（本模板自身的 `index.rst` 就是这样写的）。

> 注意：extra_assets.yaml 的用法见[文档写作指南](writing_ZH.md)

### 3.3 配置项目外链

编辑 `docs/sphinx_doc/source/external_links.yaml`：

```yaml
url_template: "https://{repo_owner}.github.io/{project}/{language}/{version}/index.html"

projects:
  data-juicer:
    repo_name: data-juicer
    display_name: Data Juicer
  
  data-juicer-hub:
    repo_name: data-juicer-hub
    display_name: DJ Hub
  
  your-new-project:          # 添加你的项目
    repo_name: your-repo-name
    display_name: Your Display Name

link_order:                  # 控制外链显示顺序
  - data-juicer
  - data-juicer-hub
  - your-new-project
```

> `url_template` 表示外链的模板，其中`{repo_owner}`、`{project}`、`{language}` 会被替换为实际值。
> `{version}` 会被替换为 `main`。


### 3.4 自定义 Logo 和图标

替换以下文件：

```
docs/sphinx_doc/source/_static/images/
└── icon.png     # 你的项目图标
```

## 4. 本地构建测试

### 4.1 安装依赖

```bash
cd your-project
pip install .
```

或使用 `uv`（推荐）：
```bash
uv pip install .
```

### 4.2 构建文档

```bash
cd docs/sphinx_doc

# 基础构建：只构建 main 分支，启用 API 文档
PROJECT="your-project" python build_versions.py

# 构建所有有效标签（>= MIN_TAG）
PROJECT="your-project" python build_versions.py --tags

# 构建指定标签
PROJECT="your-project" python build_versions.py --tags v1.5.0 v1.6.0

# 构建指定分支
PROJECT="your-project" python build_versions.py --branches main dev

# 禁用 API 文档生成
PROJECT="your-project" python build_versions.py --no-api-doc

# 仅构建英文文档
PROJECT="your-project" python build_versions.py --languages en

# 完整示例：构建 main 和 dev 分支 + 所有标签，启用 API 文档
PROJECT="your-project" python build_versions.py \
    --branches main dev \
    --tags \
    --languages en zh_CN
```

### 4.3 查看构建结果

```bash
# 启动本地服务器
python -m http.server 8000 --directory build

# 访问 http://localhost:8000/en/main/index.html
# 或     http://localhost:8000/zh_CN/main/index_ZH.html
```

## 下一步

准备发布？继续阅读[使用 GitHub Actions 部署](deployment_ZH.md)。
