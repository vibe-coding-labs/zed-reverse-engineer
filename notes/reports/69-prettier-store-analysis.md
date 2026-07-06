# 循环分析报告 #69 — Prettier 格式化集成 (PrettierStore)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/prettier_store.rs` (990 行)
**分析前状态**: ❌ 完全没碰过

## 概述

PrettierStore 管理项目的 Prettier 代码格式化器，自动安装和调用 Prettier。

## 核心功能

```rust
pub struct PrettierStore {
    // 按 worktree 管理的 Prettier 配置
    worktree_prettiers: HashMap<WorktreeId, PrettierInstance>,
}
```

| 功能 | 说明 |
|------|------|
| 自动安装 | 检测项目缺失 Prettier 时自动安装默认版本 |
| 格式化 | 调用 Prettier 格式化代码 |
| 配置同步 | 响应 settings.json 变更自动更新配置 |
| 插件管理 | 按语言加载对应 Prettier 插件 |

## 与 AI Agent 的关系

Agent 不直接调用 Prettier，但文件编辑后用户可能触发格式化。Agent 的修改需要在格式化后保持正确性。

## 关键文件

- `crates/project/src/prettier_store.rs` — Prettier 管理