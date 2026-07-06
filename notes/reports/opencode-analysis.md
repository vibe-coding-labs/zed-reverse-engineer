# 分析报告 — OpenCode CLI 集成

**源码位置**: `crates/opencode/src/opencode.rs` (729 行)
**分析前状态**: ❌ 完全没碰过

## 概述

OpenCode 是 Open AI 的开源 CLI 编码代理，Zed 通过 ACP 协议支持将其作为外部 Agent 集成。

## API 端点

```
https://opencode.ai/zen
```

OpenCode 使用 OpenAI 兼容的 Chat Completions 格式。

## 支持的订阅/模型

```rust
pub enum OpenCodeSubscription {
    Pro,        // $20/月
    ProPlus,    // $200/月（含 o1 pro）
    Free,       // 免费层
}

pub enum Model {
    O4Mini,         // GPT 4o-mini
    O3,             // o3 推理模型
    O4MiniHigh,     // 4o-mini-高推理
    Codex,          // Codex CLI 模型
    CodexMini,      // Codex Mini
    // ...
}
```

## Agent 集成

OpenCode 作为外部 Agent 通过 ACP 协议连接，Zed 的 Agent 面板可以配置 OpenCode CLI 地址。

## 关键文件

- `crates/opencode/src/opencode.rs` — OpenCode 集成实现