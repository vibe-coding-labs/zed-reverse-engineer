# 循环分析报告 #30 — Diagnostics (诊断系统)

**分析时间**: 2026-07-06
**源码位置**: `crates/diagnostics/src/` (5,078 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Diagnostics 系统显示代码错误、警告、信息。这是 Zed 编辑器的核心 UX 组件之一。

## 与 AI 的关系

AI Agent 可以读取诊断信息：
- `diagnostics_tool.rs` — Agent 工具之一，用于获取当前缓冲区的诊断信息
- 诊断数据作为 `ActiveBufferDiagnostic` 传递给 ZetaPrompt（编辑预测）
- AI 可以通过 LSP 工具获取代码操作建议

## 与反向代理的关系

不相关，诊断系统是纯本地 UI 组件。

## 关键文件

- `crates/diagnostics/src/buffer_diagnostics.rs` — 缓冲区诊断管理
- `crates/diagnostics/src/diagnostics.rs` — 诊断面板
- `crates/agent/src/tools/diagnostics_tool.rs` — Agent 诊断工具