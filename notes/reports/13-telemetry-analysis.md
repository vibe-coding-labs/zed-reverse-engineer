# 循环分析报告 #13 — 遥测系统 (Telemetry)

**分析时间**: 2026-07-05
**源码位置**: `crates/telemetry/` + `crates/telemetry_events/` + `crates/client/src/telemetry.rs`
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 有遥测系统，收集使用数据以改进产品。用户可以控制遥测级别。

## 遥测级别

```rust
// 两个独立控制维度:
pub fn metrics_enabled(&self) -> bool     // 使用指标
pub fn diagnostics_enabled(&self) -> bool // 诊断数据
```

## 事件类型

```rust
pub enum Event {
    Keymap Changed,
    Documentation Viewed,
    Assistant Event,          // AI 助手使用数据
    Edit Event,               // 编辑事件
    Project Discovered,       // 项目类型
    // ... 更多事件
}
```

## 数据上报

遥测事件通过 `mpsc::UnboundedSender<Event>` 异步队列发送，不阻塞主线程。

## 隐私保护

- `metrics_id` 是随机 UUID，不与 user_id 直接关联
- 用户可在设置中关闭
- 源码中有 `has_checksum_seed` 机制用于匿名化处理

## 关键文件

- `crates/telemetry/src/telemetry.rs` — 遥测宏和发送器
- `crates/telemetry_events/src/telemetry_events.rs` — 事件类型定义
- `crates/client/src/telemetry.rs` — 客户端遥测实现