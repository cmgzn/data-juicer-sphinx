# Data-Juicer Sphinx 文档模板

这是一个为 Data-Juicer 生态系统设计的统一文档构建模板，基于 Sphinx 和内置的 `data_juicer_theme`（现代风格自定义主题），提供多版本、多语言文档构建能力，让所有子项目保持一致的文档外观和用户体验。

## 特性

- **统一外观**：所有子项目共享相同的文档主题和样式
- **多版本支持**：自动构建多个 Git 分支和标签的文档，CI 采用增量部署（只重建变化的版本；不可变的 tag 只构建一次）
- **多语言支持**：默认支持中英文
- **生态互联**：通过页眉外链在不同项目文档间无缝切换
- **Markdown 友好**：自动发现并集成项目中的 Markdown 文档
- **AI 助手**：内置 “Ask Juicer” 问答组件（底部浮动输入栏、选中文本提问、可拖拽调宽侧边面板），支持流式回复、思考过程与工具调用展示；配置 `JUICER_API_URL` 后自动启用

## 项目结构

```
data-juicer-sphinx/
├── data_juicer_sphinx_theme/                     # 自定义 Sphinx 主题包
│   ├── theme.conf / layout.html / search.html    # 主题定义与模板
│   └── static/                                   # 主题 CSS/JS
├── docs/
│   └── sphinx_doc/                                 # Sphinx 文档构建目录
│       ├── build_versions.py                       # 多版本构建脚本（主入口）
│       ├── make.bat / Makefile                     # 构建脚本
│       ├── redirect.html                           # 重定向页面
│       └── source/                                 # 文档源文件
│           ├── conf.py                             # Sphinx 配置文件
│           ├── custom_myst.py                      # 自定义 MyST 扩展
│           ├── external_links.yaml                 # 外部项目链接配置
│           ├── index.rst / index_ZH.rst            # 主页（建议自定义）
│           ├── api.rst                          # API 文档索引（建议自定义）
│           └── _static/                         # 静态资源
│               ├── images/                      # Logo 和图标
│               ├── ask-ai-widget.js / .css      # 打包后的 Ask-AI 组件及样式
│               └── ask-ai-modules/              # 组件模块化源码 + rollup 构建
├── guides/                                      # 使用指南
├── pyproject.toml                               # 项目配置（注册主题）
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

在线文档：[datajuicer.github.io/data-juicer-sphinx](https://datajuicer.github.io/data-juicer-sphinx/zh_CN/main/index_ZH.html)

- [为你的项目启用本模板](guides/setup_ZH.md)——接入、自定义与本地构建
- [使用 GitHub Actions 部署](guides/deployment_ZH.md)——增量 CI 部署
- [文档写作指南](guides/writing_ZH.md)——内容、媒体资源与链接映射
- [常见问题](guides/faq_ZH.md)
- [工作原理](docs/how_it_works_ZH.md)——构建机制与增量流水线

## 贡献指南

欢迎为模板贡献改进！❤