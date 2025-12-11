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

见[第 5 节](#5-github-actions-自动部署)

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

或在 GitHub Actions workflow 中设置（见第 5 节）。

### 3.2 自定义关键文件

根据你的项目需求自定义以下文件：

```
docs/sphinx_doc/source/
├── index.rst              # 英文主页：项目介绍 + 页眉导航（DOCS/API）
├── index_ZH.rst           # 中文主页：项目介绍 + 页眉导航（DOCS/API）
├── docs_index.rst         # 英文文档索引
├── docs_index_ZH.rst      # 中文文档索引
├── api.rst                # API 文档索引
├── external_links.yaml    # 项目外链
└── extra_assets.yaml      # 额外资源
```

**示例：`index.rst`**
```rst
.. 项目介绍
.. 通常直接 include README.md 即可
.. include:: README.md
   :parser: myst_parser.sphinx_

.. 页眉导航
.. 设置几个 toctree，页眉就会显示几个导航
.. 此处建议只保留 DOCS 和 API，以免页眉导航过多
.. toctree::
   :maxdepth: 2
   :caption: DOCS

   docs_index

.. toctree::
   :maxdepth: 2
   :caption: API

   api
```

> 注意：extra_assets.yaml 的用法见[测试文档](../docs/test_ZH.md)

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

## 5. GitHub Actions 自动部署

在你的项目中创建 `.github/workflows/docs.yml`：

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
      HTML_TITLE: Your Project Title  # 可选：自定义标题
      MIN_TAG: v0.0.0             # 可选：最小版本
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 获取完整历史以支持多版本构建

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@master
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
      - name: Install dependencies with uv # 安装你的项目依赖
        run: |
          uv pip install --system --upgrade pip
          uv pip install --system -e .[all]

      - name: Fetch Data-Juicer Sphinx Template # 拉取模板覆盖docs/sphinx_doc，跳过自定义文件
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
          python build_versions.py --tags

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
        with:
          if: ${{ github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/')) }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/sphinx_doc/build
          cname: your-domain.com  # 可选：如果使用自定义域名
```

**启用 GitHub Pages**：
1. 进入仓库 Settings → Pages
2. Source 选择 `gh-pages` 分支
3. 保存后访问 `https://your-domain.github.io/your-project/`