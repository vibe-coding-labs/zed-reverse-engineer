# Zed 14天 Pro 试用深度分析 & 白嫖方案

## 一、14天试用的完整流程（源码级）

```
┌─────────────────────────────────────────────────────────┐
│ 1. 用户启动 Zed                                           │
│    ↓                                                     │
│ 2. 点击 "Start 14-day Free Pro Trial"                    │
│    ↓                                                     │
│ 3. 调用 zed_urls::start_trial_url(cx)                    │
│    = https://zed.dev/account/start-trial                  │
│    ↓                                                     │
│ 4. 浏览器打开 zed.dev 登录页面 → GitHub OAuth            │
│    ↓                                                     │
│ 5. OAuth回调 → cloud.zed.dev 记录 trial_started_at     │
│    ↓                                                     │
│ 6. Zed收到 UserUpdated WebSocket 通知 → 刷新plan信息      │
│    ↓                                                     │
│ 7. PlanInfo.trial_started_at = now                       │
│    plan_v3 = "zed_pro_trial"                             │
│    ↓                                                     │
│ 8. 用户现在可以使用託管模型 ($5额度 +14天)               │
└─────────────────────────────────────────────────────────┘
```

**触发条件的源码判断** (`CloudLanguageModelProvider::configuration_view`):

```rust
// 是否显示 "开始试用" 按钮
if plan == None || plan == ZedFree {
    if eligible_for_trial {  // trial_started_at == None
        show "Start 14-day Free Pro Trial"  // ← 点击后打开浏览器
    } else {
        show "Upgrade to Pro"  // 已试过了，直接付费
    }
}
```

**注意**：点击试用按钮只是**打开浏览器**到 `https://zed.dev/account/start-trial`，然后用户手动完成 GitHub OAuth 流程。Zed 客户端本身没有特殊的 API 调用，试用状态由服务端 `cloud.zed.dev` 管理。

---

## 二、限制条件（绕过难度递增）

### 2.1 GitHub 账号注册 > 30 天 ✅ 简单

```rust
// is_account_too_young = true 时：
// 1. 不显示 trial 按钮
// 2. 显示警告横幅：
"To prevent abuse of our service, GitHub accounts created fewer than
 30 days ago are not eligible for the Pro trial."
// 3. 唯一选项是直接付费升级
```

**绕过**：等 30 天，或找一个老账号。

### 2.2 每个 GitHub 账号仅一次试用 ✅

```rust
eligible_for_trial = plan.trial_started_at == None
```

**绕过**：换 GitHub 账号。Zed 的 credential 和 GitHub 账号绑定，登出换号即可。

### 2.3 试用到期后回到 Free ✅

试用到期后 `plan_v3` 变回 `zed_free`，`trial_started_at` 变成过去的时间，`eligible_for_trial = false`，不再显示试用按钮。

**绕过**：换 GitHub 账号再来一次。

---

## 三、白嫖方案

### 方案 1：多 GitHub 账号轮流试用（纯手动）

```
1. 准备多个 GitHub 账号（>30天老号）
2. Zed → Sign Out → Sign In with GitHub → Account B
3. 点 "Start 14-day Free Pro Trial"
4. 获得 14天 + $5 额度
5. 到期后切换到 Account C，继续白嫖
```

**限制**：每次只有 $5 + 14天，用完不续，而且`$20 token credit during the 2-week free trial; Opus models are excluded from the trial.`

### 方案 2：ZED_SERVER_URL 本地劫持（硬核）

```bash
# 启动本地 mock 服务
ZED_SERVER_URL=http://localhost:3000 zed
```

**思路**：搭建一个返回 `Plan::ZedProTrial` 的假服务端，让客户端永远以为自己还在试用中。

**需要 mock 的端点**：

| 端点 | 方法 | 必须返回 |
|------|------|---------|
| `/client/users/me` | GET | 有效用户信息 + HTTP 200 |
| `/client/llm_tokens` | POST | 有效 token |
| `/models` | GET | 模型列表 |
| `/completions` | POST | ✅ **关键** — 流式转发到真实 API |

**关键挑战**：
- LLM Token 格式未知（`cloud_llm_client.rs` 中 token 是个 `String`，但服务端可能做签名验证）
- `/completions` 需要转发到真实的 upstream API（Anthropic/OpenAI），这需要你自己花钱付 API Key
- 简单来说：**试用不是限制在客户端，而是在服务端 cloud.zed.dev 的计费系统**

### 方案 3：破解 LLM Token 绕过计费

从源码看，Zed 的 LLM Completion 流程是：

```
1. POST /client/llm_tokens → 拿到 {"token": {"0": "llm_xxxx"}}
2. POST /completions → Authorization: Bearer {token}
3. 服务端验证 token → 检查 plan → 转发或返回 402
```

**可能的破解点**：

如果 mock 端的 `/client/llm_tokens` 返回任意 token，而 `/completions` 直接转发而不检查 plan，那就能绕过计费。

但问题是 **`/completions` 转发到 upstream API（Anthropic/OpenAI）需要你自己的 API Key**。Zed 只是一种代理，它不会凭空变出免费的大模型调用。

---

## 四、真相：Zed 没有什么好薅的🐑:sheep:

说实话，Zed 的「免费」策略设计得很干净：

| 你想白嫖的东西 | 行不行 | 原因 |
|-------------|--------|------|
| **Zed 托管的 Claude API** | ❌ | 要付费，$10/月起 |
| **Zeta2 编辑预测** | ⚠️ 2000次 | 免费用户只有 2000 次 |
| **通过反向代理绕过计费** | ⚠️ 可但无意义 | 你需要自备 API Key 付上游的钱 |
| **14天试用无限续杯** | ✅ 可行 | 换 GitHub 号就行，但只有 $5 |
| **用反向代理给 Claude Code** | ✅ 可行 | 这是真正有价值的场景 |

### 真正有价值的玩法：反向代理给 Claude Code

```
Zed ←─── CloudAPI 格式 ───→ 反向代理 ←─── OpenAI 格式 ───→ Claude Code / Codex
                                      ↓
                               自备 API Key
```

这个方案的真正价值**不是白嫖 Zed**，而是：
1. **协议转换**：把 Zed Cloud API 格式转成 OpenAI/Anthropic 格式
2. **统一出口**：多个工具公用一个 API Key
3. **流量控制和审计**：在代理层做

**总结：Zed 就是个大号的代理客户端。它自己没有模型，全是租的 Anthropic/OpenAI 的。想白嫖它 = 白嫖 Anthropic，想白嫖 Anthropic = 不可能😂**
