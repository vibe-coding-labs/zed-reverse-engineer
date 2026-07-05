# 循环分析报告 #4 — GitHub Copilot Chat 集成

**分析时间**: 2026-07-04
**源码位置**: `crates/copilot_chat/src/` (2,358 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 内置了完整的 GitHub Copilot Chat 支持，可以直接用 Copilot 订阅调用模型。Copilot Chat 使用 OpenAI 兼容的 API 格式。

## 认证方式

Copilot 通过 GitHub OAuth token 认证，支持两种环境变量：

```
GH_COPILOT_TOKEN          # 非官方但广泛使用
GITHUB_COPILOT_TOKEN      # 官方变量名
```

如果未设置，Zed 会通过 `gh` CLI 的 OAuth token 或者 GitHub CLI 的 device flow 获取。

## API 端点

| 端点 | 用途 |
|------|------|
| `https://api.githubcopilot.com/chat/completions` | 流式聊天补全（OpenAI 格式） |
| `https://api.githubcopilot.com/responses` | 非流式响应 |
| `https://api.githubcopilot.com/v1/messages` | Anthropic 格式消息 |
| `https://api.githubcopilot.com/models` | 模型列表 |
| `https://api.github.com/graphql` | Copilot 订阅状态查询 |

企业用户可配置 `enterprise_uri` 来指向私有 GitHub Enterprise 实例。

## 支持的模型端点格式

Copilot 支持三种调用方式：

| 方式 | 端点 | 协议 |
|------|------|------|
| `chat_completions` | `/chat/completions` | OpenAI Chat API |
| `responses` | `/responses` | OpenAI Responses API |
| `messages` | `/v1/messages` | Anthropic Messages API |

## 与 Zed Cloud 的关系

Copilot Chat 是**独立于 Zed Cloud** 的集成：
- 不经过 `cloud.zed.dev`
- 直接连接到 `api.githubcopilot.com`
- 使用 GitHub Copilot 订阅计费，跟 Zed Pro 无关
- 完全可以在 Free 计划下使用（只要你有 Copilot 订阅）

## 流式响应

Copilot Chat 使用 OpenAI 标准的 SSE (Server-Sent Events) 格式流式返回。

## 与反向代理的关系

Copilot Chat 集成不影响反向代理方案。它跟 Anthropic 直连一样，是另一种 "自带 Key" 的路径，不走 Zed Cloud 的计费系统。

## 关键文件

- `crates/copilot_chat/src/copilot_chat.rs` — 主实现（1920 行）
- `crates/copilot_chat/src/responses.rs` — Responses API 实现（438 行）
- `crates/copilot_ui/src/` — Copilot Chat UI 实现