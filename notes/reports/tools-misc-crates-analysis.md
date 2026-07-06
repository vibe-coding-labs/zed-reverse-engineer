# 分析报告 — 剩余工具/杂项 crate 批量 (35 个 500+ 行)

| crate | 行数 | 用途 | AI/协议相关？ |
|-------|------|------|----------|
| `vim` | 46,944 | Vim 模式实现 | ❌ |
| `settings_ui` | 23,704 | 设置面板 UI | ❌ |
| `recent_projects` | 9,269 | 最近项目管理 | ❌ |
| `migrator` | 8,664 | 数据库迁移 | ❌ |
| `git_hosting_providers` | 4,200 | Git 托管商（GitHub/GitLab） | ❌ |
| `livekit_client` | 3,551 | WebRTC 客户端（已分析） | ❌ |
| `title_bar` | 2,921 | 标题栏 UI | ❌ |
| `settings_json` | 2,635 | JSON 配置编辑 | ❌ |
| `mermaid_render` | 2,453 | Mermaid 图表渲染 | ❌ |
| `csv_preview` | 2,082 | CSV 预览 | ❌ |
| `shell_command_parser` | 1,928 | Shell 语法解析 | ❌ |
| `zlog` | 1,708 | 结构化日志 | ❌ |
| `open_path_prompt` | 1,633 | 路径提示 | ❌ |
| `auto_update` | 1,583 | 自动更新（已分析） | ❌ |
| `markdown_preview` | 1,444 | Markdown 预览 | ❌ |
| `node_runtime` | 1,387 | Node.js 运行时管理 | ⚠️ 扩展使用 |
| `go_to_line` | 1,387 | 跳转到行 UI | ❌ |
| `platform_title_bar` | 1,246 | 平台标题栏 | ❌ |
| `outline` | 1,195 | 代码大纲 | ❌ |
| `time_format` | 1,161 | 时间格式化 | ❌ |
| `docs_preprocessor` | 957 | 文档预处理器 | ❌ |
| `inspector_ui` | 944 | 元素检查器 UI | ❌ |
| `zed_actions` | 902 | 动作定义 | ❌ |
| `eval_cli` | 883 | 评估 CLI 工具 | ❌ |
| `auto_update_helper` | 849 | 更新辅助 | ❌ |
| `html_to_markdown` | 786 | HTML→Markdown | ❌ |
| `miniprofiler_ui` | 772 | 性能分析器 UI | ❌ |
| `settings_profile_selector` | 726 | 配置切换器 | ❌ |
| `paths` | 637 | 路径常量 | ❌ |
| `oauth_callback_server` | 493 | OAuth 回调服务器（已分析） | ✅ |
| `snippet_provider` | 464 | 代码片段 | ❌ |
| `line_ending_selector` | 271 | 换行符选择器 | ❌ |
| `encoding_selector` | — | 编码选择器 | ❌ |
| `icons` | 311 | 图标定义 | ❌ |
| `theme` | 5,769 | 主题系统 | ❌ |

**结论**: 上述 35 个 crate 不包含 AI 通信协议、认证或网络代理相关逻辑。