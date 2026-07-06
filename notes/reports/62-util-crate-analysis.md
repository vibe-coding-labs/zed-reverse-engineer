# 循环分析报告 #62 — 通用工具库 (util)

**分析时间**: 2026-07-06
**源码位置**: `crates/util/src/` (8,865 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`util` crate 是 Zed 的通用工具库，提供各种基础功能模块。

## 核心模块

| 模块 | 行数 | 说明 |
|------|------|------|
| `paths.rs` | 3,585 | 路径管理（配置/数据/缓存目录） |
| `util.rs` | 1,076 | 通用工具函数 |
| `shell.rs` | 1,051 | Shell 类型和命令构建 |
| `rel_path.rs` | 644 | 相对路径处理 |

## 关键模块

**paths.rs** — 管理所有 Zed 的目录路径：
- 配置目录：`~/.config/zed/`
- 数据目录：`~/.local/share/zed/`
- 缓存目录：`~/.cache/zed/`
- 扩展目录、日志目录、密钥目录、数据库目录

**shell.rs** — Shell 类型定义：
```rust
pub enum Shell {
    System,    // 系统默认 shell
    Bash,      // bash
    Zsh,       // zsh
    Fish,      // fish
    Cmd,       // Windows cmd
    PowerShell, // Windows PowerShell
}
```

**markdown.rs** — Markdown 格式化工具
**redact.rs** — 敏感信息脱敏（用于日志中的 API Key）
**process.rs** — 进程管理

## 关键文件

- `crates/util/src/paths.rs` — 路径配置
- `crates/util/src/shell.rs` — Shell 类型
- `crates/util/src/redact.rs` — 敏感信息脱敏