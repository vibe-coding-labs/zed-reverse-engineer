# 循环分析报告 #29 — Mistral & Codestral Providers

**分析时间**: 2026-07-06
**源码位置**: `crates/mistral/src/` (477 行) + `crates/codestral/src/` (426 行)
**分析前状态**: ❌ 完全没碰过

## Mistral AI

**端点**: `https://api.mistral.ai/v1/chat/completions`  
**认证**: `Authorization: Bearer {api_key}`  
**格式**: OpenAI 兼容

支持 Mistral 的 API，包括流式响应。

## Codestral (Mistral 代码模型)

**端点**: `https://api.mistral.ai/v1/fim/completions`  
**认证**: `Authorization: Bearer {api_key}`  
**格式**: FIM (Fill-in-the-Middle) 格式，用于代码补全

Codestral 是 Mistral 专门用于代码补全的模型，使用 FIM 格式而非 Chat Completions 格式。主要用于编辑预测（Edit Prediction）。

## 与反向代理的关系

同其他直连 Provider，不经过 cloud.zed.dev。

## 关键文件

- `crates/mistral/src/mistral.rs` — Mistral Provider
- `crates/codestral/src/codestral.rs` — Codestral Provider（代码补全专用）