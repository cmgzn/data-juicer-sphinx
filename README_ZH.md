# Data-Juicer Sphinx 文档模板

这是一个为 Data-Juicer 生态系统设计的统一文档构建模板，基于 Sphinx 和 pydata-sphinx-theme，提供多版本、多语言文档构建能力，让所有子项目保持一致的文档外观和用户体验。

## 特性

- **统一外观**：所有子项目共享相同的文档主题和样式
- **多版本支持**：自动构建多个 Git 分支和标签的文档
- **多语言支持**：默认支持中英文
- **生态互联**：通过页眉外链在不同项目文档间无缝切换
- **Markdown 友好**：自动发现并集成项目中的 Markdown 文档

## 项目结构

```
data-juicer-sphinx/
├── docs/
│   └── sphinx_doc/                              # Sphinx 文档构建目录
│       ├── build_versions.py                    # 多版本构建脚本（主入口）
│       ├── make.bat / Makefile                  # 构建脚本
│       ├── redirect.html                        # 重定向页面
│       └── source/                              # 文档源文件
│           ├── conf.py                          # Sphinx 配置文件
│           ├── custom_myst.py                   # 自定义 MyST 扩展
│           ├── external_links.yaml              # 外部项目链接配置
│           ├── index.rst / index_ZH.rst         # 主页（建议自定义）
│           ├── docs_index/                      # 文档索引目录
│           │   ├── index.rst / index_ZH.rst     # 文档索引页（建议自定义）
│           │   └── ...                          # 自动复制的 Markdown 文件
│           ├── api.rst                          # API 文档索引（建议自定义）
│           ├── _static/                         # 静态资源
│           │   ├── custom.css                   # 自定义样式
│           │   └── images/                      # Logo 和图标
│           └── _templates/                      # 自定义模板
│               └── version-language-switcher.html
├── guides/                                      # 使用指南
├── pyproject.toml                               # 项目配置
├── README.md                                    
└── README_ZH.md                                 
```

## 快速开始

快速构建一个最简单的 Data-Juicer Sphinx 英文文档（不含 api 文档）：

```bash
git clone https://github.com/datajuicer/data-juicer-sphinx.git

uv pip install .

cd docs/sphinx_doc
export PROJECT="data-juicer-sphinx"
python build_versions.py -A -l en
```

## 文档

[此处](https://datajuicer.github.io/data-juicer-sphinx/zh_CN/main/index_ZH.html)

## 核心原理

### **隔离构建环境（Git Worktree）**
- 为每个版本（分支/标签）创建独立的 Git 工作树（位于 `.worktrees/<version>`）。
- 构建完成后自动清理（除非在`docs/sphinx_doc/build_versions.py`中设置 `KEEP_WORKTREES=True`），避免污染主工作区。

### **文档内容聚合**
- 自动扫描整个工作树，收集所有 `.md` 和 `.rst` 文件（排除 `outputs`, `sphinx_doc`, `.github` 等目录）。
- 将这些文件复制到统一的 Sphinx 源目录 `docs/sphinx_doc/source/docs_index/` 下。
- （data-juicer 算子文档定制）对于 `operators/` 目录下的次级文件夹，自动生成对应的 `index.rst` 和 `index_ZH.rst`，便于算子分类索引。

## 常见问题

### Q1: 构建失败，提示找不到模块

**A**: 确保在构建前安装了所有依赖：
```bash
uv pip install .
```

### Q2: API 文档没有生成

**A**: 检查以下几点：
- 确保没有使用 `--no-api-doc` 或 `-A` 参数
- 确保项目有可导入的 Python 模块
- 检查 `CODE_ROOT` 环境变量是否正确设置

### Q3: 外链不显示

**A**: 
1. 检查 `external_links.yaml` 配置是否正确
2. 确认 `PROJECT` 环境变量设置正确
3. 查看浏览器控制台是否有 JavaScript 错误

### Q4: 中文文档链接不存在

**A**: 确保：
- 中文文档以 `_ZH.md` 或 `_ZH.rst` 结尾
- `index_ZH.rst` 存在并正确配置

### Q5: 版本切换后页面不存在

**A**: 不同版本的文档结构可能不同：
- 旧版本可能没有某些新页面
- 切换版本会尝试访问相同路径，不存在时会跳回首页

## 贡献指南

欢迎为模板贡献改进！❤