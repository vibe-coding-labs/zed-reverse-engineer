---
title: 免费额度分析
description: Zed Free/Pro 限制分析，以及自带 API Key 的使用路径
---

# 免费额度分析

## 一、Zed 的免费额度

### 1.1 免费计划限制

```
Plan::ZedFree → UsageLimit::Limited(2000)
```

免费计划 (Zed Free) 限制的是 **Edit Predictions（编辑预测）**，也就是 Zeta2 模型的内联代码补全功能，共 **2000 次**，用完服务端返回 `402 Payment Required`。

### 1.2 哪些功能是免费的？

| 功能 | 是否免费 | 说明 |
|------|---------|------|
| **自带 API Key 使用 AI** | ✅ 完全免费 | 配置自己的 Anthropic/OpenAI Key |
| **ACP 外部 Agent** | ✅ 完全免费 | 连接 Claude Code CLI、Codex CLI |
| **代码编辑** | ✅ 免费 | 编辑器核心功能 |
| **多人在线协作** | ✅ 免费 | 多人编辑 |
| **Zeta2 编辑预测** | ⚠️ 限 2000 次 | 免费计划只有 2000 次 |
| **Zed 托管的 LLM** | ⚠️ 需要 Pro | API 调用按量计费 |

---

## 二、自带 API Key 方案

Zed 完全支持自带 API Key，配置后直连上游 API，**不经过 Zed Cloud 计费系统**。

```json
{
  "language_models": {
    "anthropic": { "api_key": "sk-ant-xxxxxxxx" },
    "openai": { "api_key": "sk-xxxxxxxx" }
  }
}
```

```
┌──────────┐          ┌────────────────┐          ┌──────────────┐
│ Zed AI   │──────────▶ 直连上游 API    │──────────▶  Anthropic    │
│ 聊天/Agent│          │ (跳过 cloud)   │          │  /OpenAI      │
└──────────┘          └────────────────┘          └──────────────┘
```

---

## 三、计费方案对比

| 方案 | 适合场景 | 费用 |
|------|---------|------|
| 自带 API Key | 已有 API Key 的用户 | API Key 自己的费用 |
| Zed Free + ACP | 想用 Claude Code/Codex | CLI 工具自己的费用 |
| Zed Pro | 想要一次性计费 | $10/月 |
| 反向代理 | 多工具共享 Key | API Key + 运维费用 |

---

## 参考

- `crates/cloud_api_types/src/plan.rs` — Plan 类型定义
- `crates/cloud_llm_client/src/cloud_llm_client.rs` — UsageLimit 定义
- [Zed 定价页面](https://zed.dev/pricing)