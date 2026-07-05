# 循环分析报告 #9 — 功能开关系统 (Feature Flags)

**分析时间**: 2026-07-05
**源码位置**: `crates/feature_flags/src/` (940 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 使用功能开关系统来控制新功能的发布。开关由远程服务控制（`cloud.zed.dev` 的 `feature_flags` 字段）。

## 功能开关列表

| 开关名 | 类型 | Staff 默认 | 说明 |
|--------|------|-----------|------|
| `notebooks` | presence | — | 笔记功能 |
| `panic` | presence | — | 崩溃测试 |
| `acp-beta` | presence | — | ACP 协议 Beta（标记"可复用"） |
| `agent-sharing` | presence | — | Agent 线程分享 |
| `diff-review` | presence | ❌ 关闭 | Diff 审查 |
| `create-thread-tool` | presence | ✅ 开启 | Agent 创建子线程 |
| `lsp-tool` | presence | ❌ 关闭 | LSP 工具（查找引用等） |
| `rename-tool` | presence | ✅ 开启 | 重命名工具 |
| `project-panel-undo-redo` | presence | ✅ 开启 | 项目面板撤销重做 |
| `agent-thread-worktree-label` | enum | ❌ 关闭 | Agent 线程标签类型 |
| `auto-watch-screens` | presence | — | 自动监控屏幕 |
| `sandboxing` | presence | ❌ 关闭 | 终端沙箱隔离 |

## 开关类型

```rust
// presence — 简单的开启/关闭
pub struct AcpBetaFeatureFlag;
impl FeatureFlag for AcpBetaFeatureFlag {
    const NAME: &'static str = "acp-beta";
    type Value = PresenceFlag;  // 有 = 开启，无 = 关闭
}

// enum — 多值开关
pub enum AgentThreadWorktreeLabel { Both, Worktree, Branch }
```

## Staff 特权

Staff 用户（Zed 员工）默认开启更多开关，普通用户只有明确启用才可用。

## 与反向代理的关系

功能开关不直接影响反向代理。但 `acp-beta` 开关需要打开才能使用 ACP 协议的外部 Agent 功能，如果你要通过 ACP 桥接 Claude Code 的话需要关注。

## 关键文件

- `crates/feature_flags/src/flags.rs` — 所有开关定义
- `crates/feature_flags/src/store.rs` — 开关存储
- `crates/feature_flags/src/feature_flags.rs` — 注册机制