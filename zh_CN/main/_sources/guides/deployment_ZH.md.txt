# 使用 GitHub Actions 部署

这是使用本模板的推荐方式：由项目的 CI 拉取模板、构建文档并自动发布到 GitHub Pages。

部署是**增量**的：push 到 `main` 只构建 main，push tag 只构建该 tag（tag 不可变，无需重建），PR 只构建当前检出的代码。已发布的版本在 `gh-pages` 上保持不动（`keep_files: true`）。需要重建全部版本时（刷新旧 tag 的主题、清理孤儿文件），用 `workflow_dispatch` 并勾选 `full: true`。

## 1. 创建 Workflow

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
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            # PR 预览：只构建当前检出的代码，不走 worktree
            python build_versions.py --current preview
          elif [ "${{ github.event_name }}" = "workflow_dispatch" ] && [ "${{ inputs.full }}" = "true" ]; then
            # 手动全量重建：所有分支和 tag（清理孤儿文件 + 刷新主题）
            python build_versions.py --tags
          elif [[ "${GITHUB_REF}" == refs/tags/* ]]; then
            # tag push：tag 不可变，只构建该 tag
            python build_versions.py --branches --tags "${GITHUB_REF_NAME}"
          else
            # 分支 push（main）或未勾选 full 的手动触发：只构建分支
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
          # 增量发布：已发布的版本保持不动。
          # 全量重建（full=true）会整站替换，从而清理孤儿文件。
          keep_files: ${{ !(github.event_name == 'workflow_dispatch' && inputs.full) }}
          cname: your-domain.com  # 可选：如果使用自定义域名
```

> 增量部署注意事项：
> - 版本切换器在运行时从 `versions.json` 加载版本列表，旧版本页面能自动看到新发布的 tag。
> - `keep_files` 不会删除文件：被重建版本中移除的页面可能残留，直到下一次全量重建。
> - 旧 tag 保留其发布时的主题外观；如需统一刷新，跑一次全量重建。

## 2. 启用 GitHub Pages

1. 进入仓库 Settings → Pages
2. Source 选择 `gh-pages` 分支
3. 保存后访问 `https://your-domain.github.io/your-project/`
