# Zed 登录方式 & 白嫖可行性终极分析

## 登录方式：只有 GitHub OAuth，别无选择

翻了全部源码，Zed 的登录**只有 GitHub OAuth**，没有邮箱注册、没有 Google 登录、没有其他任何方式。

### 登录流程（源码证实）

```
Zed 客户端
  │
  ├── 打开浏览器 → https://zed.dev/native_app_signin?native_app_port=xxxx&native_app_public_key=xxx
  │                  ↓
  │               GitHub OAuth 页面（只有这一个选项）
  │                  ↓
  │               用户授权后，GitHub 回调 Zed 服务端
  │                  ↓
  ├── 本地启动 tiny_http 监听 127.0.0.1:随机端口
  │   接收回调 → 拿到 {user_id, access_token}
  │   解密 access_token（RSA加密传输）
  │
  └── 凭证存入系统 keychain
```

### 关键证据

1. **服务端源码** (`collab/src/auth.rs`): 用户模型只有 `github_login` 字段
2. **客户端源码** (`client.rs`): `authenticate_as_admin` 也是根据 `github_login` 来模拟
3. **Zed 注册页**: `https://zed.dev/sign_up` 只有 "Sign Up with GitHub" 一个按钮
4. **无邮箱/密码字段**: 代码中找不到任何 password hash、email registration 逻辑

---

## 试用的真实限制在哪里？

**关键结论：限制全在服务端（cloud.zed.dev），客户端只是读取显示，没法在本地绕过。**

### 限制数据流

```
cloud.zed.dev 服务端
  │
  ├── GET /client/users/me 返回 ↓
  │   {
  │     "plan_v3": "zed_free",           ← 计划
  │     "trial_started_at": null,        ← 试用开始时间（非空=已用过）
  │     "is_account_too_young": false,   ← GitHub 账号<30天
  │     "has_overdue_invoices": false    ← 逾期发票
  │     "usage": { "edit_predictions": { "used": 0, "limit": "2000" } }
  │   }
  │
  └── POST /completions 检查
      ├── Plan == ZedFree → 402 Payment Required
      ├── trial_started_at 已过期 → 402
      └── 已超额 → 402
```

### 客户端能做啥？啥也做不了

```rust
// Zed 客户端只是读服务端数据展示：
eligible_for_trial = user_store.trial_started_at().is_none()
// 如果 trial_started_at != null → 不显示试用按钮
// 但这个值是服务端返回的，客户端没法改
```

点击 "Start 14-day Free Pro Trial" → 打开浏览器到 `https://zed.dev/account/start-trial` → 这完全在 Zed 服务端控制。

---

## 白嫖可能性逐条评估

| 方法 | 可行性 | 限制 | 
|------|--------|------|
| **多 GitHub 号轮流试用** | ✅ 可行 | 每个号$5额度+14天，需要>30天老号 |
| **ZED_SERVER_URL 劫持** | ⚠️ 半可行 | 能绕过客户端限制，但 `/completions` 转发到上游还得自费 |
| **破解服务端** | ❌ 不可能 | 服务端不开源，跑在 cloud.zed.dev |
| **找其他登录方式** | ❌ 不可能 | 只有 GitHub OAuth |
| **改源码重新编译** | ❌ 无意义 | 服务端验证，改客户端没用 |
| **自备 API Key** | ✅ 能用但自费 | 你付上游的钱，Zed 不分账 |

---

## 真相

Zed **就是个代理客户端**，它自己没有模型算力。它的"免费额度"本质上是：
- Zeta2 编辑预测：Zed 自己训的小模型，免费2000次
- 托管 Claude/OpenAI：租来的，试用送$5，用完付费

想白嫖 = 白嫖 Anthropic/OpenAI 的 API。而 Anthropic/OpenAI 的 API 不存在"免费额度绕过"这回事，它们在计费上比谁都精😂

**唯一的白嫖路径：多准备几个注册超过30天的 GitHub 号，轮流14天试用。每个号$5额度，够轻度使用。用完换号，无限循环。**
