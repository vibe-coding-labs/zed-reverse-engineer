# 分析报告 — 扩展/语言/调试器 crate 批量 (16 个)

| crate | 行数 | 用途 | AI 相关？ |
|-------|------|------|----------|
| `dev_container` | 15,058 | Dev Container 开发环境 | ❌ |
| `languages` | 14,607 | 语言语法配置（Tree-sitter） | ❌ |
| `extension_host` | 9,907 | 扩展 WASM 宿主（已覆盖） | ⚠️ |
| `language_tools` | 5,368 | 语言工具函数 | ❌ |
| `dap_adapters` | 3,130 | DAP 适配器配置 | ❌ |
| `dap` | 2,800 | DAP 协议实现 | ❌ |
| `extension` | 2,748 | 扩展系统（已完整分析） | ⚠️ |
| `extensions_ui` | 2,387 | 扩展管理 UI | ❌ |
| `language_core` | 1,919 | 语言核心类型 | ❌ |
| `extension_api` | 840 | 扩展 API 定义 | ❌ |
| `language_extension` | 830 | 语言扩展 WASM 绑定 | ❌ |
| `extension_cli` | 690 | 扩展 CLI 构建工具 | ❌ |
| `language_selector` | 770 | 语言选择器 | ❌ |
| `language_onboarding` | 100 | 语言入门引导 | ❌ |
| `debug_adapter_extension` | 243 | 调试适配器扩展 | ❌ |
| `debugger_ui` | 25,066 | 调试器 UI（纯 UI） | ❌ |

所有扩展/语言/调试器 crate 不包含 AI 通信协议逻辑。