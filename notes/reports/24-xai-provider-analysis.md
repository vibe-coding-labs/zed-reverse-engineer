# 循环分析报告 #24 — xAI (Grok) Provider

**分析时间**: 2026-07-06
**源码位置**: `crates/x_ai/src/` (132 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 支持 xAI（Grok）作为 LLM Provider，代码量很小（132行），因为它复用了 OpenAI 的 Chat Completions 实现。

## 实现方式

```rust
// x_ai.rs 几乎完全是 OpenAI 的封装
// 使用 OpenAI 兼容的 API 格式
// 不同的只有 API URL 和模型列表
```

## API 端点

```
https://api.x.ai/v1/chat/completions
```

认证方式：`Authorization: Bearer {api_key}`

## 与反向代理的关系

同其他直连 Provider，不经过 cloud.zed.dev。

## 关键文件

- `crates/x_ai/src/x_ai.rs` — xAI Provider 入口