# 循环分析报告 #45 — Agent 终端工具 (TerminalTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/terminal_tool.rs` (2,639 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`TerminalTool` 是 AI Agent 执行 shell 命令的工具，也是 Agent 最重要的能力之一。

## 输入参数

```rust
pub struct TerminalToolInput {
    pub command: String,       // 要执行的命令
    pub cd: String,            // 工作目录
    pub timeout_ms: Option<u64>,  // 超时（毫秒）
    pub head_lines: Option<usize>, // 只返回前 N 行
    pub tail_lines: Option<usize>, // 只返回后 N 行
}
```

## 安全要求

Agent 工具输入的文档明确要求：
- 不要使用 `$VAR`、`${VAR}`、`$(...)`、反引号等 shell 替换——Agent 必须自己解析值
- git 只读命令必须加 `--no-pager`
- 可能打开编辑器的 git 命令必须加 `GIT_EDITOR=true`
- 超时后自动 kill 终端

## 沙箱模式

```rust
pub struct SandboxedTerminalToolInput {
    // 类似 TerminalToolInput，但在沙箱中运行
}
```

沙箱模式在支持的平台上（macOS Seatbelt）运行时提供额外的安全隔离。

## 输出处理

- 同时读取 stdout 和 stderr，保持写入顺序
- 支持 `head_lines`/`tail_lines` 限制返回行数（节省 token）
- 返回组合输出字符串

## 关键文件

- `crates/agent/src/tools/terminal_tool.rs` — 终端工具实现
- `crates/agent/src/sandboxing.rs` — 沙箱隔离