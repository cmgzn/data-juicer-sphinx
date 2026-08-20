# 工作原理

介绍模板如何构建与发布文档。新用户可以跳过本页；它主要在排查构建问题或扩展模板时有用。

## 隔离构建环境（Git Worktree）

- 为每个版本（分支/标签）创建独立的 Git 工作树（位于 `.worktrees/<version>`）。
- 构建完成后自动清理（除非在 `docs/sphinx_doc/build_versions.py` 中设置 `KEEP_WORKTREES=True`），避免污染主工作区。

## 文档内容聚合

- 构建时扫描整个工作树，收集所有 `.md` 和 `.rst` 文件（排除 `outputs`、`sphinx_doc`、`.github` 等目录）。完整规则见[文档写作指南](../guides/writing_ZH.md)。
- 收集到的文件被复制到统一的 Sphinx 源目录 `docs/sphinx_doc/source/` 下。
- （data-juicer 算子文档定制）对于 `operators/` 目录下的次级文件夹，自动生成对应的 `index.rst` 和 `index_ZH.rst`，便于算子分类索引。

## 增量 CI 流水线

每次 CI 运行只构建实际发生变化的那个版本：

1. **事件分流**：push 到 `main` 只构建 main；push tag 只构建该 tag；PR 将当前检出的代码构建为 `preview` 产物；`workflow_dispatch` 勾选 `full: true` 时重建所有版本。
2. **单版本构建**：`build_versions.py` 只构建该版本（所有语言），输出到 `build/<lang>/<version>/`。
3. **versions.json**：完整版本列表（`main` + 有效 tag）每次重新生成并发布到站点根目录，使每个页面的版本切换器在运行时始终展示最新版本。
4. **合并发布**：部署步骤使用 `keep_files: true`，只覆盖本次构建的版本目录，已发布的其他版本保持不动。全量重建则不带 `keep_files` 部署，整站替换并清理孤儿文件。

完整 workflow 见[使用 GitHub Actions 部署](../guides/deployment_ZH.md)。
