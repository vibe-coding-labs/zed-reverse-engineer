# 循环分析报告 #34 — REPL (交互式编程/Jupyter)

**分析时间**: 2026-07-06
**源码位置**: `crates/repl/src/` (4,453 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 内置 REPL 系统，支持 Jupyter kernel 连接，可以在编辑器中交互式运行代码。

## 实现方式

Zed 的 REPL 使用 Jupyter 协议：
- **Kernel 启动**: 通过 `ipykernel` 或自定义 kernel 规范启动子进程
- **协议**: Jupyter ZMQ 协议（基于 `runtimelib` crate）
- **配置**: 支持 `jupyter_settings.rs` 配置 kernel 路径
- **输出渲染**: `outputs.rs` 支持富文本输出（文本、图片、HTML）

## 与 AI 的关系

Agent 的代码执行能力是通过终端工具（`TerminalTool`）实现的，而不是通过 REPL。REPL 是独立的交互式编程功能。

## 关键文件

- `crates/repl/src/session.rs` — REPL 会话管理
- `crates/repl/src/kernels/` — Kernel 管理
- `crates/repl/src/repl_editor.rs` — REPL 编辑器
- `crates/repl/src/outputs.rs` — 输出渲染