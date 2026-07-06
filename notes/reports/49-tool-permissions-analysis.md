# 循环分析报告 #49 — Agent 工具权限系统 (ToolPermissions)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tool_permissions.rs` (2,415 行)
**分析前状态**: ❌ 完全没碰过

## 概述

工具权限系统是 Agent 的安全层，决定哪些工具调用可以自动执行、哪些需要用户确认、哪些被禁止。

## 权限决策模型

```rust
pub enum ToolPermissionDecision {
    Allow,             // 自动允许，无需确认
    Deny(String),      // 自动拒绝（含原因）
    Confirm,           // 需要用户确认
}
```

## 决策优先级（从高到低）

| 优先级 | 规则 | 说明 |
|--------|------|------|
| 1 | **硬编码安全规则** | 不可绕过的安全检查（如阻止 `rm -rf /`） |
| 2 | `always_deny` | 用户配置的拒绝模式 |
| 3 | `always_confirm` | 用户配置的确认模式 |
| 4 | `always_allow` | 用户配置的自动允许模式 |
| 5 | **工具特定默认值** | 工具自身的默认权限 |
| 6 | **全局默认值** | `tool_permissions.default` |

## 路径安全

`decide_permission_for_paths()` 和 `normalize_path()` 函数处理文件路径权限，确保 Agent 不能访问项目目录之外的文件。

## Shell 兼容性

终端工具的命令通过 brush-parser 解析以提取子命令，不同 ShellKind 的兼容性影响权限模式的工作方式。

## 关键文件

- `crates/agent/src/tool_permissions.rs` — 权限系统核心