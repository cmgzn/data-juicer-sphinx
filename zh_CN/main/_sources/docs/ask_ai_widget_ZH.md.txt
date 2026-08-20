# Ask-AI 组件开发指南

## 📁 项目结构

```
docs/sphinx_doc/source/_static/
├── ask-ai-modules/              # 模块化源代码
│   ├── ask-ai-i18n.js          # 国际化配置
│   ├── ask-ai-api.js           # API 通信层
│   ├── ask-ai-ui.js            # UI 渲染和交互
│   └── ask-ai-widget.js        # 主控制器
├── ask-ai-widget.js            # 打包后的单文件（用于生产）
├── ask-ai-widget.css           # 组件样式（Mintlify 风格，跟随明暗主题）
├── package.json                # Node.js 依赖配置
└── rollup.config.js            # Rollup 打包配置
```

> 本文档位于 `docs/ask_ai_widget.md`（会渲染进站点），不在 `_static/` 内。

> 组件仅在配置了 `JUICER_API_URL` 时才会加载（见 `docs/sphinx_doc/source/conf.py`）。

## 🚀 快速开始

### 1. 安装依赖

在 `docs/sphinx_doc/source/_static/` 目录下运行：

```bash
npm install
```

### 2. 构建打包文件

```bash
npm run build
```

这将会：
- 读取 `ask-ai-modules/` 目录下的所有模块
- 使用 Rollup 将它们打包成单个文件
- 输出到 `ask-ai-widget.js`（覆盖原文件）

### 3. 开发模式（监听文件变化）

```bash
npm run watch
```

在开发模式下，任何对 `ask-ai-modules/` 中文件的修改都会自动触发重新打包。

## 📝 模块说明

### ask-ai-i18n.js
- **功能**：国际化配置
- **导出**：`I18N` 对象和 `detectLanguage()` 函数
- **大小**：约 2KB

### ask-ai-api.js
- **功能**：API 通信层
- **导出**：`AskAIApi` 类
- **职责**：
  - API 连接检查
  - 会话历史加载
  - 流式响应处理
  - 会话清除
- **大小**：约 8KB

### ask-ai-ui.js
- **功能**：UI 渲染和交互
- **导出**：`AskAIUI` 类
- **职责**：
  - DOM 创建和管理（底部浮动输入栏、选中文本提问气泡、可拖拽调宽侧边面板）
  - 事件绑定
  - 消息渲染（流式回复、思考过程、工具调用、反馈按钮）
  - 主题切换
  - Markdown 渲染
- **大小**：约 12KB

### ask-ai-widget.js
- **功能**：主控制器
- **导出**：`AskAIWidget` 类（默认导出）
- **职责**：
  - 整合所有模块
  - 初始化流程
  - 业务逻辑协调
- **大小**：约 4KB

## 🔧 修改代码

### 修改流程

1. **编辑模块文件**：在 `ask-ai-modules/` 目录下修改对应的模块
2. **重新构建**：运行 `npm run build`
3. **测试**：在浏览器中测试打包后的文件

### 添加新功能

如果需要添加新功能：

1. 确定功能属于哪个模块（I18N、API、UI 或主控制器）
2. 在对应模块中添加代码
3. 如果需要跨模块调用，通过导出/导入机制实现
4. 重新构建并测试

## 📦 打包说明

### 打包配置说明

`rollup.config.js` 配置：

```javascript
{
  input: 'ask-ai-modules/ask-ai-widget.js',  // 入口文件
  output: {
    file: 'ask-ai-widget.js',                 // 输出文件
    format: 'iife',                           // 立即执行函数格式
    name: 'AskAIWidget',                      // 全局变量名
    globals: { marked: 'marked' }             // 外部依赖映射
  },
  external: ['marked']                        // 不打包 marked 库
}
```

## 🔍 故障排查

### 构建失败

如果构建失败，检查：

1. Node.js 版本是否 >= 18（Rollup 4 要求；系统自带的 Node 12 会报语法错误）
2. 依赖是否正确安装（`npm install`）
3. 模块文件中是否有语法错误

### 功能异常

如果打包后功能异常：

1. 检查浏览器控制台错误
2. 确认 marked.js 已正确加载

## 📚 相关文档

- [Rollup 官方文档](https://rollupjs.org/)
- [ES6 模块规范](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [Sphinx 文档](https://www.sphinx-doc.org/)
