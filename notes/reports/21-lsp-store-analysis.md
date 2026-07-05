# 循环分析报告 #21 — LSP 集成层 (Language Server Protocol)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/lsp_store.rs` (15,222 行)
**分析前状态**: ❌ 完全没碰过

## 概述

LSP Store 是 Zed 与语言服务器通信的核心层，支持多个 LSP 服务器并行运作。

## 支持的 LSP 扩展

| 扩展模块 | 说明 |
|----------|------|
| `rust_analyzer_ext` | Rust Analyzer 专用扩展 |
| `clangd_ext` | C/C++ clangd 扩展 |
| `json_language_server_ext` | JSON 语言服务器 |
| `vue_language_server_ext` | Vue 语言服务器 |
| `code_lens` | Code Lens 支持 |

## LSP 请求

Zed 的核心功能依赖 LSP（与 AI 无关但很重要）：
- 代码补全、跳转定义、查找引用
- 代码诊断（红色波浪线）
- 悬停提示、文档符号
- 代码操作（重构）

## 与反向代理的关系

LSP 集成与 AI 通信协议是独立的，不经过 cloud.zed.dev。不影响反向代理方案。

## 关键文件

- `crates/project/src/lsp_store.rs` — LSP 存储核心（15,222 行）
- `crates/lsp/src/` — LSP 协议客户端（2,542 行）