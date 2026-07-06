# 循环分析报告 #70 — 项目设置系统 (ProjectSettings)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/project_settings.rs` (1,622 行)
**分析前状态**: ❌ 完全没碰过

## 概述

ProjectSettings 定义项目的所有可配置设置，从 LSP 配置到 Node.js 运行时到 OAuth 客户端。

## 核心设置结构

```rust
pub struct ProjectSettings {
    pub session: SessionSettings,                    // 会话/编辑器设置
    pub node: NodeBinarySettings,                    // Node.js 路径
    pub lsp: Option<GlobalLspSettings>,              // LSP 全局设置
    pub lsp_notifications: LspNotificationSettings,  // LSP 通知
    pub context_servers: Option<HashMap<String, ContextServerSettings>>,  // MCP 服务器
}

pub struct SessionSettings {
    pub autosave: AutosaveSetting,
    pub tab_size: u32,
    pub line_indent: u32,
    pub format_on_save: FormatOnSave,
    pub scroll_beyond_last_line: ScrollBeyondLastLine,
}

pub enum ContextServerSettings {
    Stdio { command: String, args: Vec<String>, env: HashMap<String, String> },
    Http { url: String, headers: HashMap<String, String>, oauth: Option<OAuthClientSettings> },
}
```

## MCP 服务器配置

Context server（MCP）可以在项目设置中配置，支持 stdio 和 HTTP 两种传输方式，HTTP 方式支持 OAuth 认证。

## 关键文件

- `crates/project/src/project_settings.rs` — 项目设置定义