# 循环分析报告 #60 — Agent 小工具合集 (13 个工具)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/` 多个文件
**分析前状态**: ❌ 完全没碰过

## 工具总览

| 工具 | 行数 | 输入 | 功能 |
|------|------|------|------|
| `FindPathTool` | 271 | `path: String` | 按路径搜索文件 |
| `DiagnosticsTool` | 258 | (无) | 获取当前文件诊断 |
| `CopyPathTool` | 662 | `path: String` | 复制文件/目录 |
| `RenameTool` | 125 | `path, new_name` | 重命名符号 |
| `CreateDirectoryTool` | 564 | `path: String` | 创建目录 |
| `DeletePathTool` | 709 | `path, trash` | 删除文件/目录 |
| `MovePathTool` | 688 | `source, destination` | 移动文件/目录 |
| `CreateThreadTool` | 201 | `description, tasks` | 创建 Agent 子线程 |
| `ListAgentsAndModelsTool` | 78 | (空) | 列出可用 Agent/模型 |
| `ApplyCodeActionTool` | 145 | `action` | 应用 LSP 代码操作 |
| `GoToDefinitionTool` | 111 | `path, position` | 跳转到定义 |
| `FindReferencesTool` | 102 | `path, position` | 查找引用 |
| `GetCodeActionsTool` | 116 | `path, range` | 获取代码操作列表 |

## 路径操作工具

`CopyPathTool`、`DeletePathTool`、`MovePathTool` 共享相同的路径安全机制：
- 目标必须在项目根目录内
- 支持移入回收站（`trash` 参数）
- 操作前要求用户确认

## LSP 工具

`GoToDefinitionTool`、`FindReferencesTool`、`GetCodeActionsTool` 通过 LSP 协议调用语言服务器。受 `LspToolFeatureFlag` 控制，默认只对 staff 用户开启。

## 子线程工具

`CreateThreadTool` 可以创建独立的 Agent 子线程在后台运行，受 `CreateThreadToolFeatureFlag` 控制。

## 关键文件

- `crates/agent/src/tools/find_path_tool.rs`
- `crates/agent/src/tools/diagnostics_tool.rs`
- `crates/agent/src/tools/copy_path_tool.rs`
- `crates/agent/src/tools/rename_tool.rs`
- `crates/agent/src/tools/create_directory_tool.rs`
- `crates/agent/src/tools/delete_path_tool.rs`
- `crates/agent/src/tools/move_path_tool.rs`
- `crates/agent/src/tools/create_thread_tool.rs`
- `crates/agent/src/tools/list_agents_and_models_tool.rs`
- `crates/agent/src/tools/apply_code_action_tool.rs`
- `crates/agent/src/tools/go_to_definition_tool.rs`
- `crates/agent/src/tools/find_references_tool.rs`
- `crates/agent/src/tools/get_code_actions_tool.rs`