# 补覆盖分析 — 基础设施 crate (action_log, scheduler, sandbox, rope, sum_tree, multi_buffer 等)

## action_log (3,508 行)
Agent 操作日志系统，记录 Agent 执行的所有操作（文件编辑、终端命令等）。
- 用于操作回放和审计
- 支持撤销/重做
- 不涉及 AI 通信协议

## scheduler (2,760 行)
GitHub Actions 风格的调度器，管理 CI/CD 流水线。与 AI 协议无关。

## sandbox (8,228 行)
操作系统沙箱抽象层，用于安全隔离 Agent 执行的操作。已在前面的分析中覆盖（macOS Seatbelt 沙箱）。

## rope (4,132 行)
Zed 的核心数据结构——Rope (B-tree 变体)，用于高效管理大文本缓冲区。
- 支持 O(log n) 插入/删除/查找
- 支持行偏移量计算
- 所有编辑器/缓冲区操作的基础
- 与 AI 协议无关

## sum_tree (3,327 行)
Sum Tree 数据结构，用于高效区间求和和偏移量计算。与 AI 协议无关。

## multi_buffer (16,331 行)
多缓冲区管理器，支持将多个缓冲区合并为一个视图（如搜索结果、诊断列表）。
- 多缓冲区查询
- Excerpt 管理
- 与 AI 协议无关

## collab_ui (6,392 行)
协作 UI 组件（通话界面、联系人列表、频道 UI）。纯 UI，不涉及协议。

## agent_ui (83,448 行)
Agent 聊天界面，包括对话面板、消息编辑器、工具调用显示等。纯 UI 层，不涉及 AI 协议传输。

## agent_servers (6,086 行)
Agent 服务器管理，包括 ACP 连接管理、外部 Agent 进程管理。已在 ACP 分析中覆盖。

## acp_tools (842 行)
ACP 调试工具，用于查看 ACP 连接的调试日志。已在 ACP 分析中覆盖。

## ui (27,945 行)
Zed 的 UI 组件库（按钮、输入框、列表、弹窗等）。纯 UI，不涉及协议。

## 其余小 crate（均与 AI 协议无关）
| crate | 行数 | 说明 |
|-------|------|------|
| `keymap_editor` | 6,054 | 键位绑定编辑器 |
| `buffer_diff` | 4,315 | 缓冲区 diff 对比 |
| `call` | 3,003 | 音视频通话（已分析） |
| `onboarding` | 2,236 | 新用户引导 |
| `cli` | 1,631 | `zed` CLI 命令 |
| `theme_selector` | 1,238 | 主题选择器 UI |
| `prettier` | 1,219 | Prettier 格式化 |
| `fuzzy` | 1,205 | 模糊搜索算法 |
| `component` | 530 | 组件注册框架 |
| `livekit_api` | 485 | LiveKit 服务器 API 客户端 |
| `syntax_theme` | 336 | 语法高亮主题 |
| `snippet` | 334 | 代码片段 |
| `grammars` | 112 | Tree-sitter 语法注册 |
| `vim_mode_setting` | 42 | Vim 模式设置 |
| `assets` | 65 | 资源嵌入 |
| `settings_macros` | 152 | 设置宏 |
| `sqlez_macros` | 102 | SQLite 宏 |
| `eval_utils` | 146 | 评估工具 |
| `feature_flags_macros` | 190 | 功能开关宏 |
| `explorer_command_injector` | 199 | 文件管理器集成 |
| `picker_preview` | 371 | 选择器预览 |
| `theme_extension` | 92 | 主题扩展定义 |
| `theme_importer` | 820 | 主题导入器 |
| `etw_tracing` | — | Windows ETW 追踪 |
| `fs_benchmarks` | — | 文件系统基准测试 |
| `editor_benchmarks` | — | 编辑器基准测试 |
| `project_benchmarks` | — | 项目基准测试 |
| `worktree_benchmarks` | — | 工作树基准测试 |

**结论**: 以上所有 crate 均不包含 AI 通信协议、认证或网络代理相关逻辑。与反向代理目标无关。