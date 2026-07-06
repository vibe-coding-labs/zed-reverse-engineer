# 分析报告 — Anthropic/OpenAI 兼容 Provider (API 兼容层)

**源码位置**: `crates/language_models/src/provider/anthropic_compatible.rs` + `api_compatible.rs` + `open_ai_compatible.rs`
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 通过兼容 Provider 层支持任意兼容 Anthropic 或 OpenAI API 格式的自托管服务。

## Anthropic 兼容

**配置示例**：
```json
{ "language_models": { "anthropic_compatible": { "api_url": "https://my-proxy.example.com", "api_key": "sk-ant-xxx" } } }
```
- 支持自定义 `api_url`
- 复用 `anthropic` crate 的请求/响应格式
- 支持自定义模型能力声明

## OpenAI 兼容

**配置示例**：
```json
{ "language_models": { "open_ai_compatible": { "api_url": "https://my-proxy.example.com/v1", "api_key": "sk-xxx" } } }
```
- 支持自定义 `api_url`
- 复用 `open_ai` crate 的 Chat Completions 格式
- 支持流式和非流式

## API 兼容基类

`api_compatible.rs` 提供共享的配置 UI、凭证管理和设置界面。

## 与反向代理的关系

Zed 原生支持自定义 API 端点！这意味着：
- 不需要劫持 `ZED_SERVER_URL`
- 直接在 `settings.json` 中配置自定义端点即可
- 比 ZED_SERVER_URL 劫持更干净

## 关键文件

- `crates/language_models/src/provider/anthropic_compatible.rs` — Anthropic 兼容
- `crates/language_models/src/provider/open_ai_compatible.rs` — OpenAI 兼容
- `crates/language_models/src/provider/api_compatible.rs` — 共享基类