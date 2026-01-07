# Ask AI Widget - Build Instructions

## 📁 Project Structure

```
docs/sphinx_doc/source/_static/
├── ask-ai-modules/              # Modularized source code
│   ├── ask-ai-i18n.js          # Internationalization configuration
│   ├── ask-ai-api.js           # API communication layer
│   ├── ask-ai-ui.js            # UI rendering and interaction
│   └── ask-ai-widget.js        # Main controller
├── ask-ai-widget.js            # Bundled single file (for production)
├── ask-ai-widget.js.backup     # Original file backup
├── package.json                # Node.js dependency configuration
├── rollup.config.js            # Rollup bundling configuration
└── BUILD.md                    # This document
```

## 🚀 Quick Start

### 1. Install Dependencies

Run the following command in the `docs/sphinx_doc/source/_static/` directory:

```bash
npm install
```

### 2. Build and Bundle

```bash
npm run build
```

This will:
- Read all modules in the `ask-ai-modules/` directory
- Bundle them into a single file using Rollup
- Output to `ask-ai-widget.js` (overwriting the original file)

### 3. Development Mode (Watch for File Changes)

```bash
npm run watch
```

In development mode, any modifications to files in `ask-ai-modules/` will automatically trigger a rebuild.

## 📝 Module Descriptions

### ask-ai-i18n.js
- **Purpose**: Internationalization configuration
- **Exports**: `I18N` object and `detectLanguage()` function
- **Size**: ~2KB

### ask-ai-api.js
- **Purpose**: API communication layer
- **Exports**: `AskAIApi` class
- **Responsibilities**:
  - API connection verification
  - Session history loading
  - Streaming response handling
  - Session clearing
- **Size**: ~8KB

### ask-ai-ui.js
- **Purpose**: UI rendering and interaction
- **Exports**: `AskAIUI` class
- **Responsibilities**:
  - DOM creation and management
  - Event binding
  - Message rendering
  - Theme switching
  - Markdown rendering
- **Size**: ~12KB

### ask-ai-widget.js
- **Purpose**: Main controller
- **Exports**: `AskAIWidget` class (default export)
- **Responsibilities**:
  - Integration of all modules
  - Initialization process
  - Business logic coordination
- **Size**: ~4KB

## 🔧 Modifying Code

### Modification Workflow

1. **Edit Module Files**: Modify the corresponding module in the `ask-ai-modules/` directory
2. **Rebuild**: Run `npm run build`
3. **Test**: Test the bundled file in your browser

### Adding New Features

If you need to add new functionality:

1. Determine which module the feature belongs to (I18N, API, UI, or main controller)
2. Add code to the corresponding module
3. If cross-module calls are needed, implement them through export/import mechanisms
4. Rebuild and test

## 📦 Bundling Information

### Bundling Configuration Explanation

`rollup.config.js` configuration:

```javascript
{
  input: 'ask-ai-modules/ask-ai-widget.js',  // Entry file
  output: {
    file: 'ask-ai-widget.js',                 // Output file
    format: 'iife',                           // Immediately Invoked Function Expression
    name: 'AskAIWidget',                      // Global variable name
    globals: { marked: 'marked' }             // External dependency mapping
  },
  external: ['marked']                        // Don't bundle marked library
}
```

## 🔍 Troubleshooting

### Build Failures

If the build fails, check:

1. Whether Node.js version is >= 14
2. Whether dependencies are correctly installed (`npm install`)
3. Whether there are syntax errors in the module files

### Function Anomalies

If functionality is abnormal after bundling:

1. Check the browser console for errors
2. Verify that marked.js is correctly loaded

## 📚 Related Documentation

- [Rollup Official Documentation](https://rollupjs.org/)
- [ES6 Module Specification](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [Sphinx Documentation](https://www.sphinx-doc.org/)