# 分析报告 — Workspace 工作区子模块批量

**源码位置**: `crates/workspace/src/` (47,447 行)

Workspace 是 Zed 的窗口/工作区管理框架，管理面板、dock、标签页等 UI 布局。不参与任何 AI 或网络协议。

## 子模块速览

| 文件 | 行数 | 功能 |
|------|------|------|
| `workspace.rs` | 16,327 | 主工作区管理 |
| `pane.rs` | 9,429 | 标签页/窗格 |
| `persistence.rs` | 5,943 | 工作区状态持久化 |
| `multi_workspace.rs` | 2,296 | 多窗口管理 |
| `notifications.rs` | 1,896 | 通知系统 |
| `item.rs` | 1,869 | Item trait（可编辑项） |
| `dock.rs` | 1,556 | Dock 面板容器 |
| `pane_group.rs` | 1,551 | 窗格分组 |

## AI 相关功能

Workspace 管理 Agent 面板的生命周期：
- `agent_panel_position()` — Agent 面位置
- `PanelAdded(Agent)` — Agent 面板事件

但不涉及任何 AI 通信协议逻辑。

## 结论

与反向代理目标无关。