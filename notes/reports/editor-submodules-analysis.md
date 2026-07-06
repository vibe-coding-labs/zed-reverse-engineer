# 分析报告 — Editor 编辑器子模块批量

**文件**: `crates/editor/src/*.rs` (50+ 文件，合计 12 万+ 行)

## 编辑器和 AI 的关系

编辑器是 AI Agent 工具（EditFileTool、ReadFileTool、WriteFileTool 等）操作的**目标**。Agent 修改文件 → 编辑器反映变更。但编辑器本身**不参与 AI 通信协议**。

## 核心子模块速览

| 模块 | 行数 | 功能 | AI 相关？ |
|------|------|------|----------|
| `editor.rs` | 12,264 | 编辑器主入口 | ❌ |
| `element.rs` | 12,041 | 渲染/Vim/多光标 | ❌ |
| `split.rs` | 6,352 | 分屏/多窗格 | ❌ |
| `display_map.rs` | 4,219 | 行号/折叠/滚动 | ❌ |
| `hover_links.rs` | 3,252 | 悬停超链接 | ❌ |
| `input.rs` | 3,077 | 输入处理 | ❌ |
| `git.rs` | 2,841 | Git 内联标记 | ✅ Git 状态展示 |
| `items.rs` | 2,806 | 项目集成 | ❌ |
| `hover_popover.rs` | 2,709 | 悬停弹出 | ❌ |
| `edit_prediction.rs` | 2,600 | **编辑预测集成** | ✅ |
| `semantic_tokens.rs` | 2,485 | 语义 Token 高亮 | ❌ |
| `navigation.rs` | 2,407 | 导航历史 | ❌ |
| `selection.rs` | 2,372 | 选区管理 | ❌ |
| `bracket_colorization.rs` | 1,685 | 括号染色 | ❌ |
| `code_lens.rs` | 1,673 | Code Lens | ❌ |
| `movement.rs` | 1,509 | 光标移动 | ❌ |
| `completions.rs` | 1,508 | 代码补全 UI | ❌ |
| `runnables.rs` | 1,306 | 运行按钮 | ❌ |
| `selections_collection.rs` | 1,282 | 选区和光标集合 | ❌ |
| `inlays.rs` | 1,134 | 内联显示 | ❌ |
| `folding_ranges.rs` | 1,098 | 折叠 | ❌ |
| `scroll.rs` | 1,079 | 滚动 | ❌ |
| `clipboard.rs` | 1,076 | 剪贴板 | ❌ |
| `persistence.rs` | 1,064 | 编辑器状态持久化 | ❌ |
| `tasks.rs` | 1,053 | 任务集成 | ❌ |
| `code_actions.rs` | 970 | 代码操作 | ❌ |
| `diagnostics.rs` | 821 | 诊断显示 | ❌ |
| `linked_editing_ranges.rs` | 766 | 关联编辑区 | ❌ |
| `highlight_matching_bracket.rs` | 742 | 括号匹配高亮 | ❌ |
| `fold.rs` | 676 | 折叠操作 | ❌ |
| `rust_analyzer_ext.rs` | 667 | RA 扩展 | ❌ |
| `signature_help.rs` | 653 | 签名帮助 | ❌ |
| `bookmarks.rs` | 559 | 书签 | ❌ |
| `code_context_menus.rs` | 2,040 | 代码上下文菜单 | ❌ |
| `split_editor_view.rs` | 556 | 分屏视图 | ❌ |
| `indent_guides.rs` | 537 | 缩进线 | ❌ |
| `config.rs` | 508 | 配置 | ❌ |
| `editor_settings.rs` | 474 | 编辑器设置 | ❌ |
| `actions.rs` | 456 | 动作定义 | ❌ |
| `clangd_ext.rs` | 449 | Clangd 扩展 | ❌ |
| `rewrap.rs` | 401 | 自动换行 | ❌ |
| `blink_manager.rs` | 379 | 光标闪烁 | ❌ |
| `lsp_ext.rs` | 377 | LSP 扩展 | ❌ |
| `document_colors.rs` | 373 | 文档颜色 | ❌ |
| `document_links.rs` | 361 | 文档链接 | ❌ |
| `mouse_context_menu.rs` | 331 | 右键菜单 | ❌ |
| `jsx_tag_auto_close.rs` | 276 | JSX 自动闭合 | ❌ |
| `document_symbols.rs` | 255 | 文档符号 | ❌ |
| `markdown_actions.rs` | 237 | Markdown 操作 | ❌ |
| `document_links.rs` | 361 | 文档链接 | ❌ |
| `split_editor_view.rs` | 556 | 分屏视图 | ❌ |

## 与 AI 相关的模块

只有 `edit_prediction.rs`（2,600 行）与 AI 直接相关，负责编辑预测（Zeta2）的编辑器内集成。其他模块均与 AI 协议无关。