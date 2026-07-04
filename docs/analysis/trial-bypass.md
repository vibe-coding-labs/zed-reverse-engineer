---
title: 试用绕过分析
description: Zed 14天 Pro 试用的源码级分析及各种绕过方案评估
---

# 试用绕过分析

## 一、14天试用流程（源码级）

```
1. 用户点击 "Start 14-day Free Pro Trial"
   → 打开浏览器到 https://zed.dev/account/start-trial
2. GitHub OAuth 登录
3. cloud.zed.dev 记录 trial_started_at
4. Zed 收到 UserUpdated WebSocket 通知 → 刷新 plan 信息
5. PlanInfo.trial_started_at = now, plan_v3 = "zed_pro_trial"
6. 用户获得 14天 + $5 LLM 额度
```

## 二、限制条件

### GitHub 账号注册 > 30 天

```rust
// is_account_too_young = true 时：
// 1. 不显示 trial 按钮
// 2. 显示警告横幅
"You are not eligible for the Pro trial."
// 3. 唯一选项是直接付费升级
```

### 每个账号仅一次试用

```rust
eligible_for_trial = plan.trial_started_at == None
```

### 试用到期后自动回到 Free

`trial_started_at` 变为过去时间，不再显示试用按钮。

---

## 三、白嫖方案评估

| 方法 | 可行性 | 限制 |
|------|--------|------|
| **多 GitHub 号轮流试用** | ✅ 可行 | 每个号 $5 额度 + 14天，需 >30 天老号 |
| **ZED_SERVER_URL 劫持** | ⚠️ 半可行 | 绕过客户端限制，但转发上游仍需自费 |
| **破解服务端** | ❌ 不可能 | 服务端不开源 |
| **找其他登录方式** | ❌ 不可能 | 只有 GitHub OAuth |
| **自带 API Key** | ✅ 能用但自费 | 你付上游的钱 |

---

## 四、关键发现

Zed **就是一个代理客户端**，它自己没有模型算力。它的"免费额度"本质上是：

- **Zeta2 编辑预测**: Zed 自己训的小模型，免费 2000 次
- **托管 Claude/OpenAI**: 租来的，试用送 $5，用完付费

**唯一的白嫖路径**: 多准备几个注册超过 30 天的 GitHub 号，轮流 14 天试用。每个号 $5 额度，用完换号。

---

## 参考

- `crates/ai_onboarding/src/young_account_banner.rs` — 年龄限制
- `crates/language_models/src/provider/cloud.rs` — 试用 UI
- `crates/cloud_api_types/src/plan.rs` — PlanInfo 定义