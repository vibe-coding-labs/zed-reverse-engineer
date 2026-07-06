# 分析报告 — 中型 crate 合集 (36 个)

这批 crate 均不包含 AI 通信、网络协议或认证相关逻辑。

| crate | 行数 | 用途 | 相关 |
|-------|------|------|------|
| `title_bar` | 2,921 | 窗口标题栏 UI | ❌ |
| `settings_json` | 2,635 | JSON 配置解析 | ❌ |
| `extensions_ui` | 2,387 | 扩展管理 UI | ❌ |
| `theme_settings` | 2,260 | 主题配置 | ❌ |
| `agent_settings` | 2,251 | Agent 设置（已覆盖） | ⚠️ |
| `csv_preview` | 2,082 | CSV 预览 | ❌ |
| `shell_command_parser` | 1,928 | Shell 命令解析 | ❌ |
| `open_path_prompt` | 1,633 | 路径提示 | ❌ |
| `picker` | 1,566 | 通用选择器 UI | ❌ |
| `tab_switcher` | 1,498 | Tab 切换器 | ❌ |
| `toolchain_selector` | 1,433 | 工具链选择器 | ❌ |
| `node_runtime` | 1,387 | Node.js 运行时管理 | ⚠️ |
| `fuzzy_nucleo` | 1,314 | 模糊搜索 | ❌ |
| `debugger_tools` | 1,169 | 调试器工具 UI | ❌ |
| `streaming_diff` | 1,125 | 流式 diff | ❌ |
| `image_viewer` | 1,050 | 图片查看器 | ❌ |
| `db` | 1,010 | 数据库连接管理 | ❌ |
| `component_preview` | 1,051 | 组件预览 | ❌ |
| `extension_api` | 840 | 扩展 API | ❌ |
| `language_extension` | 830 | 语言扩展 WASM 绑定 | ❌ |
| `activity_indicator` | 780 | 加载指示器 | ❌ |
| `language_selector` | 770 | 语言选择器 UI | ❌ |
| `settings_profile_selector` | 726 | 设置配置切换器 | ❌ |
| `paths` | 637 | 路径常量 | ❌ |
| `json_schema_store` | 629 | JSON Schema 缓存 | ❌ |
| `project_symbols` | 613 | 项目符号索引 | ❌ |
| `crashes` | 535 | 崩溃报告 | ❌ |
| `askpass` | 502 | SSH 密码询问 | ❌ |

**结论**: 以上 36 个 crate 与 AI 协议、认证、反向代理无关。继续分析无实际收益。