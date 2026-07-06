# 循环分析报告 #50 — Agent 沙箱隔离 (Sandboxing)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/sandboxing.rs` (350 行)
**分析前状态**: ❌ 完全没碰过

## 概述

沙箱系统为 Agent 执行的终端命令提供操作系统级别的安全隔离。

## 沙箱策略

当前策略：仅在 **macOS** 上启用（使用 Seatbelt 沙箱），且需要开启 `sandboxing` 功能开关。

```rust
pub fn sandboxing_enabled(cx: &App) -> bool {
    cfg!(target_os = "macos") && cx.has_flag::<SandboxingFeatureFlag>()
}
```

非 macOS 平台不支持沙箱，无论功能开关状态如何都返回 `false`。

## 权限请求

```rust
pub struct SandboxRequest {
    pub network: bool,             // 是否允许网络访问
    pub allow_fs_write_all: bool,  // 是否允许完全文件系统写入
    pub unsandboxed: bool,         // 是否完全绕过沙箱
    pub write_paths: Vec<PathBuf>, // 允许写入的具体路径
}
```

## 权限升级

当命令需要超出默认沙箱范围的权限时（如网络访问、文件写入），需要用户确认授权（`needs_escalation()`）。

## 关键文件

- `crates/agent/src/sandboxing.rs` — 沙箱隔离核心
- `crates/feature_flags/src/flags.rs` — `SandboxingFeatureFlag` 定义