# 循环分析报告 #39 — LSP 协议客户端

**分析时间**: 2026-07-06
**源码位置**: `crates/lsp/src/` (2,542 行)
**分析前状态**: ❌ 完全没碰过

## 概述

LSP crate 是 Zed 的 LSP (Language Server Protocol) 客户端，管理与语言服务器的通信。

## 通信方式

LSP 通过 **stdin/stdout** 与语言服务器子进程通信，使用 JSON-RPC 2.0 协议：
- `stdin` — 发送请求/通知
- `stdout` — 接收响应/通知
- `stderr` — 日志输出

## 与 AI Agent 的关系

Agent 通过 LSP 工具调用语言服务器：
- `GoToDefinitionTool` → `textDocument/definition`
- `FindReferencesTool` → `textDocument/references`
- `GetCodeActionsTool` → `textDocument/codeAction`
- `ApplyCodeActionTool` → 执行代码操作
- `RenameTool` → `textDocument/rename`

## 支持的 LSP 扩展

```rust
// 二进制 strings 确认的 LSP 扩展
textDocument/switchSourceHeader      // 切换头文件/源文件
textDocument/signatureHelp            // 签名帮助
experimental/externalDocs             // 外部文档
experimental/parentModule             // 父模块
experimental/runnables                // 可运行项
rust-analyzer/expandMacro             // 宏展开
```

## 关键文件

- `crates/lsp/src/lsp.rs` — LSP 客户端核心 (2,329 行)
- `crates/lsp/src/input_handler.rs` — 输入处理器