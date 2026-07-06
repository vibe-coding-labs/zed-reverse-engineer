# 分析报告 — UI 面板 crate 批量 (9 个)

**分析时间**: 2026-07-06

| crate | 行数 | 功能 | AI 相关？ |
|-------|------|------|----------|
| `sidebar` | 23,469 | 侧边栏容器管理 | ❌ 纯 UI |
| `project_panel` | 19,500 | 项目文件树面板 | ❌ 纯 UI |
| `terminal_view` | 9,552 | 终端面板视图 | ❌ UI |
| `outline_panel` | 8,252 | 符号大纲面板 | ❌ UI |
| `file_finder` | 7,233 | 文件搜索面板 | ❌ UI |
| `tasks_ui` | 2,035 | 任务管理 UI | ❌ UI |
| `command_palette` | 1,563 | 命令面板 | ❌ UI |
| `notifications` | 684 | 通知 UI | ❌ UI |
| `command_palette_hooks` | 153 | 命令面板钩子 | ❌ |

所有 UI 面板 crate 均不包含 AI 通信或网络协议逻辑。