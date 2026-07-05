# 循环分析报告 #15 — 扩展系统 (Extension)

**分析时间**: 2026-07-06
**源码位置**: `crates/extension/src/` (2,314 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 的扩展系统支持通过 WASM 扩展来扩展编辑器功能，包括语言支持、主题、LLM Provider 等。

## 扩展类型

通过 `extension_manifest.rs` 中的清单定义，扩展可以包含：
- **语言支持**（语法高亮、Tree-sitter 解析）
- **主题**
- **LLM Provider**（可替换内置的 Anthropic/OpenAI Provider）
- **Context Server**（MCP 服务器）
- **LSP 适配器**

## LLM Provider 扩展

Zed 支持通过扩展提供自定义 LLM Provider。当扩展安装了某个 Provider 后，**内置的同名 Provider 会被自动隐藏**（通过 `set_builtin_provider_hiding_fn` 机制）。

```rust
// 例如：安装 "anthropic" 扩展 → 隐藏内置的 Anthropic Provider
```

## 扩展构建与运行时

扩展使用 `cargo-zigbuild` 交叉编译为 WASM 模块，在沙箱中运行。扩展与 Zed 主进程通过 protobuf over pipe 通信（`extension_host_proxy.rs`）。

## 扩展清单

```rust
// crates/extension/src/extension_manifest.rs
pub struct ExtensionManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: Option<String>,
    pub repository: Option<String>,
    pub languages: Option<Vec<LanguageGrammar>>,
    pub themes: Option<Vec<Theme>>,
    pub language_models: Option<Vec<LanguageModelEntry>>,
    pub context_servers: Option<Vec<ContextServerEntry>>,
}
```

## 与反向代理的关系

扩展系统不影响 AI 通信协议的劫持方案。如果未来有人开发了自定义 LLM Provider 扩展，那也是直连第三方 API，不走 cloud.zed.dev。

## 关键文件

- `crates/extension/src/extension_manifest.rs` — 扩展清单格式
- `crates/extension/src/extension_builder.rs` — 扩展构建
- `crates/extension/src/extension_host_proxy.rs` — 扩展进程通信