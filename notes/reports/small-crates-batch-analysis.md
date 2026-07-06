# 循环分析报告 #77 — 小工具 crate 合集 (35 个)

**分析时间**: 2026-07-06

## 无关键逻辑的工具 crate（仅供记录）

| crate | 行数 | 用途 |
|-------|------|------|
| `auto_update_ui` | 399 | 自动更新弹窗 UI |
| `benchmarks` | 6 | 基准测试入口 |
| `breadcrumbs` | 127 | 面包屑导航 |
| `clock` | 338 | 仿真时钟（测试用） |
| `env_var` | 40 | 环境变量工具宏 |
| `feedback` | 145 | 反馈/报告 bug（打开 GitHub 链接） |
| `file_icons` | 166 | 文件类型图标 |
| `input_latency_ui` | 322 | 输入延迟显示 UI |
| `install_cli` | 122 | CLI `zed` 命令安装 |
| `journal` | 300 | 操作日志持久化 |
| `line_ending_selector` | 271 | 换行符选择器 UI |
| `media` | 362 | 媒体播放器 |
| `menu` | 37 | 菜单组件 |
| `oauth_callback_server` | 493 | OAuth 回调 HTTP 服务器（已分析） |
| `panel` | 35 | 面板 trait 定义 |
| `refineable` | 132 | derive 宏 |
| `release_channel` | 292 | 发布渠道（已分析） |
| `schema_generator` | 43 | JSON Schema 生成器 |
| `session` | 149 | 会话 ID（已分析） |
| `snippet_provider` | 464 | 代码片段 |
| `snippets_ui` | 364 | 代码片段 UI |
| `svg_preview` | 365 | SVG 渲染 |
| `system_specs` | 297 | 系统规格信息 |
| `ui_input` | 318 | UI 输入组件 |
| `ui_macros` | 239 | UI 宏 |
| `ui_prompt` | 214 | UI Prompt 组件 |
| `util_macros` | 286 | 工具宏 |
| `watch` | 317 | 文件系统监听 |
| `web_search` | 72 | Web 搜索注册表（已分析） |
| `web_search_providers` | 165 | Web 搜索 Provider（已分析） |
| `which_key` | 420 | Which-key 弹出键位提示 |
| `windows_resources` | 125 | Windows 资源定义 |
| `zed_env_vars` | 6 | 环境变量列表 |
| `zlog_settings` | 30 | 日志设置 |
| `ztracing` / `ztracing_macro` | 95+7 | OpenTelemetry 追踪 |

以上所有 crate 均不包含 AI、网络或认证相关逻辑。与反向代理目标无关。