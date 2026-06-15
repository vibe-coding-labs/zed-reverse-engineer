# Zed 免费额度分析 & 「白嫖」路径

## 一、Zed 的免费额度到底有多少？

根据源码分析 + 官方定价页面，Zed 的免费计划（Zed Free）**并没有所谓的「免费大模型额度」**—— 它限制的是 **Edit Predictions（编辑预测）**，也就是 Zeta2 模型的内联代码补全功能。

### 1.1 免费计划限制

```
Plan::ZedFree → UsageLimit::Limited(2000)
```

也就是 **2000 次编辑预测**，用完就没了，服务端返回 `402 Payment Required`。

### 1.2 哪些东西是免费的？

Zed 编辑器本身完全免费，以下功能不需要付费：

| 功能 | 是否免费 | 说明 |
|------|---------|------|
| **自带 API Key 使用 AI** | ✅ 完全免费 | 配置自己的 Anthropic/OpenAI Key，无限使用 |
| **ACP 外部 Agent** | ✅ 完全免费 | 连接 Claude Code CLI、Codex CLI 等 |
| **代码编辑** | ✅ 免费 | 编辑器核心功能 |
| **多人在线协作** | ✅ 免费 | 多人编辑 |
| **Zeta2 编辑预测** | ⚠️ 限 2000 次 | 免费计划只有 2000 次 |
| **Zed 托管的 LLM** | ⚠️ 需要 Pro | API 调用按量计费（$5 赠送） |

---

## 二、最关键的发现：自带 API Key 完全免费

这是 **白嫖的最优路径**:grinning: 

```yaml
# settings.json
"language_models": {
  "anthropic": {
    "api_key": "sk-ant-xxxxxxxx"
  },
  "openai": {
    "api_key": "sk-xxxxxxxx"
  }
}
```

**配置自己的 API Key 后，Zed 直接连接上游 API（`api.anthropic.com`、`api.openai.com` 等），完全不经过 Zed Cloud 的计费系统。** 所有 AI 聊天、Agent、内联助手功能都能用，没有任何限制。

```
┌──────────┐          ┌────────────────┐          ┌──────────────┐
│ Zed AI   │──────────▶ 直连上游 API    │──────────▶  Anthropic    │
│ 聊天/Agent│          │ (跳过 cloud)   │          │  /OpenAI      │
└──────────┘          └────────────────┘          └──────────────┘
```

---

## 三、免费试用路线

### 3.1 14 天 Pro 试用

Zed 提供 **14 天 Pro 免费试用**，包含 $5 的 LLM 额度（不含 Opus 模型）。

**条件**：
- GitHub 账号注册时间 > 30 天（否则 `is_account_too_young = true`）
- 无逾期发票
- 未试用过（`trial_started_at` 为空）

**触发时机**：在 AI 面板中点击 "Start 14-day Free Pro Trial"

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│ Zed Free     │───▶│ Zed Pro Trial    │───▶│ Zed Pro      │
│ 2000 预测     │    │ 14天 + $5 额度   │    │ $10/月       │
│ 无托管 LLM    │    │ 含 Opus 外的模型  │    │ 无限 + 续费  │
└──────────────┘    └──────────────────┘    └──────────────┘
```

### 3.2 试用中的限制

```rust
// 试用期间 Opus 模型不可用！
// 代码中的 trial 限制检查:
$20 token credit during the 2-week free trial;
Opus models are excluded from the trial.
```

---

## 四、四层「白嫖」方案

### 方案 1：自带 API Key（推荐，零门槛）

```
Zed + 自己的 Anthropic/OpenAI API Key
├── AI 聊天 ✅ 无限
├── Inline Assistant ✅ 无限
├── Agent 模式 ✅ 无限
└── Zeta2 编辑预测 ❌ 2000次
```

**成本**：只用你自己的 API Key 费用，Zed 不分账
**优点**：零配置，Zed 原生支持，完全免费（除了 API Key 本身的消耗）

**配置方法**：
1. 打开 Settings → `language_models.json`
2. 添加你的 API Key
3. 重启 Zed，选择该 provider

### 方案 2：ACP 外部 Agent

```
Zed ──ACP──▶ Claude Code CLI / Codex CLI / OpenCode
            (JSON-RPC 2.0 over stdio)
```

Zed 可以通过 ACP (Agent Communication Protocol) 调用外部 Agent 进程，这些 Agent 使用它们自己的认证和计费，与 Zed 无关。

**配置**：
```json
{
  "agent_servers": [
    {
      "id": "claude-code",
      "path": "/usr/local/bin/claude",
      "args": ["--acp"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-xxxx" }
    }
  ]
}
```

### 方案 3：ZED_SERVER_URL 劫持

```bash
# 启动你自己的 mock 服务
export ZED_SERVER_URL=http://localhost:3000
zed
```

搭建一个模拟 cloud.zed.dev 的反向代理，返回 fake 的 Pro 响应。

**需要 mock 的端点**：
- `GET /client/users/me` → 返回认证用户
- `POST /client/llm_tokens` → 返回假 token
- `GET /models` → 返回模型列表
- `POST /completions` → 转发到真实 API

### 方案 4：Student 计划

代码中有一个 `Plan::ZedStudent`，功能等同 Pro，如果有学生认证渠道可能免费。

```rust
Some(Plan::ZedStudent) => (
    "You have access to Zed's hosted models through your Student subscription.",
    true,
),
```

---

## 五、免费用户可用的关键 API

### 5.1 完全可用的（免 Zed 计费）

| API | 端点 | 说明 |
|-----|------|------|
| Anthropic Chat | `api.anthropic.com/v1/messages` | 自带 Key |
| OpenAI Chat | `api.openai.com/v1/chat/completions` | 自带 Key |
| Google Gemini | `generativelanguage.googleapis.com` | 自带 Key |
| Ollama | `localhost:11434` | 本地免费 |
| LM Studio | `localhost:1234` | 本地免费 |

### 5.2 需要 Zed Pro 的

| API | 限制 |
|-----|------|
| Zed 托管的 LLM | 需要 Pro 订阅 |
| Edit Predictions (Zeta2) | 免费 2000 次 |
| Playground 模型 | Pro 用户 |

---

## 六、最佳实践建议

### 最高性价比方案

```
┌─────────────────────────────────────┐
│ 方案：Zed Free + 自备 Anthropic Key │
├─────────────────────────────────────┤
│ ✓ AI Agent + Chat 无限制            │
│ ✓ 内联 Assistant 无限制              │
│ ✓ Codebase 问答 无限制               │
│ ✓ 2000 次编辑预测作为补充             │
│ ✗ 需要自付 API 费用                   │
│ ✗ 不能使用 Zed 托管的模型             │
└─────────────────────────────────────┘
```

### 试用最大化

```
┌─────────────────────────────────────────┐
│ 方案：利用 14 天 Pro 试用                 │
├─────────────────────────────────────────┤
│ 1. 注册 GitHub 账号（等 30 天后）         │
│ 2. 安装 Zed，登录                        │
│ 3. 开始 14 天 Pro 试用（获 $5 额度）      │
│ 4. 14 天内尽情使用 Zed 托管模型           │
│ 5. 试用结束后回到 Free + 自带 Key        │
└─────────────────────────────────────────┘
```

---

## 七、关于反向代理到 Claude Code / Codex

理清了 Zend 的免费策略后，反向代理的核心思路更清晰了：

**不需要劫持 Zed Cloud 的计费系统**，因为：
1. Claude Code 和 Codex 都有自己的 API Key 认证
2. 只需要在它们和 Zed Cloud API 格式之间做协议转换
3. Zed 本身的认证可以走自己的 API Key 绕过计费

详细方案见 `03-reverse-proxy-design.md`。
