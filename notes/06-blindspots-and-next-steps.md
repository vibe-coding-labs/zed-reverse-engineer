# 工作盲区分析 & 下一步行动计划

> **Plan Type:** Research + Feature（混合）
> **Scope:** Medium
> **Risk:** Low

---

## 一、已完成的工作回顾

| # | 工作项 | 状态 | 产出 |
|---|--------|------|------|
| 1 | 官网调研 & 二进制下载 | ✅ | 5 个平台文件下载到 `data/` |
| 2 | 源码结构分析 | ✅ | 234 个 crate 概览 |
| 3 | AI 通信协议分析 | ✅ | `notes/01-ai-protocol-analysis.md` |
| 4 | 登录授权协议分析 | ✅ | `notes/02-auth-protocol-analysis.md` |
| 5 | 反向代理方案设计 | ✅ | `notes/03-reverse-proxy-design.md` |
| 6 | 免费额度 & 试用分析 | ✅ | `notes/04-free-tier-analysis.md`、`notes/05-trial-bypass-analysis.md` |
| 7 | Python 授权脚本 | ✅ | `scripts/zed_auth.py` |

---

## 二、分析盲区盘点（按优先级排序）

### P0 — 必须补齐

#### 盲区 1：从未用真实账号跑通端到端流程 ⚠️

**问题：** 我们的协议分析全部基于读源码，**从未实际向 cloud.zed.dev 发过一个请求**。不确定：
- `/client/users/me` 返回的真实 JSON 结构是否和我们推导的一致
- `/client/llm_tokens` 的参数格式是否正确（`organization_id` 的序列化方式）
- `/completions` 的 402/403 行为是否和我们预期一致
- WebSocket 连接能否正常建立

**风险：** 如果协议推导有偏差，后面的反向代理和账号池设计都是空中楼阁。

#### 盲区 2：回调服务器 + RSA 解密从未实测

**问题：** `authenticate_via_browser()` 流程中的：
- 本地回调服务器能否正常接收 zed.dev 的跳转
- RSA OAEP-SHA256 解密是否能正确解密 access_token
- 这些都没有实测过

---

### P1 — 重要但要依赖 P0

#### 盲区 3：反向代理从未实现和测试

**问题：** `notes/03-reverse-proxy-design.md` 只停留在设计文档层面，没有实际代码。需要 P0 验证了协议正确性后才能实现。

#### 盲区 4：账号池架构从未设计

**问题：** 用户想要「搞到好多账号之后，可以做账号池」。但账号池的架构还没设计：
- 如何存储多个 credentials（加密存储？）
- 如何检测 token 过期并切换账号
- 账号间如何做负载均衡（round-robin？）
- 如何检测 402/403 并自动换号

---

### P2 — 锦上添花

#### 盲区 5：Collab RPC 协议未分析

**发现：** Zed 有一个完整的 protobuf RPC 系统（`crates/proto/proto/*.proto`，协议版本 68），用于多人协作。但这和我们反向代理的目标关系不大，优先级低。

#### 盲区 6：Edit Prediction (Zeta2) 协议未分析

**发现：** Edit Prediction 有自己的 API（`/edit_predictions`、`x-zed-edit-predictions-usage-limit` 头），但这是 Zeta2 模型的内联代码补全，不是我们关注的重点。

#### 盲区 7：二进制逆向分析未做

**发现：** 我们只分析了源码，没有对下载的二进制做过 strings、network trace、或反汇编分析。

---

## 三、优先级排序

```
P0 ────────────────────────────────────────────────
  ├── 端到端实测（验证协议推导）
  │   └── 用 scripts/zed_auth.py 跑一次真实登录
  │
P1 ────────────────────────────────────────────────
  ├── 实现反向代理（目标：Zed ←→ 代理 ←→ Claude Code）
  ├── 实现账号池（目标：多账号自动切换）
  │
P2 ────────────────────────────────────────────────
  ├── Collab RPC 分析
  ├── Edit Prediction 分析
  └── 二进制逆向分析
```

---

## 四、下一步行动

### Step 1：P0 — 端到端实测（最紧急）

**目标：** 用真实 GitHub 账号登录一次 Zed，捕获完整的网络请求。

**方案 A（推荐）：抓包 Zed 客户端**
```bash
# 1. 设置 HTTP/HTTPS 代理
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080

# 2. 启动 mitmproxy
mitmproxy -s capture_zed.py

# 3. 启动 Zed，正常登录使用
zed

# 4. 捕获到的关键请求：
#    - GET /client/users/me            → 确认 PlanInfo 结构
#    - POST /client/llm_tokens          → 确认 Token 获取
#    - POST /completions                 → 确认 Completion 请求
#    - wss://cloud.zed.dev/client/users/connect → WebSocket 握手
```

**方案 B（备用）：用 Python 脚本跑一次**
```bash
# 修改 zed_auth.py 中的 main()，取消注释方式 1
python scripts/zed_auth.py
```
但需要用户在本地浏览器完成 GitHub OAuth。

### Step 2：P1 — 实现反向代理

**前置条件：** P0 验证完成后

**实现目标：** `ZED_SERVER_URL=http://localhost:3000 zed` 能正常工作

### Step 3：P1 — 实现账号池

**前置条件：** P1 反向代理完成后

### Step 4：P2 — 其他分析

**前置条件：** P0/P1 全部完成

---

## 五、结论

**最大的盲区是「从来没实测过」。** 所有分析都基于读源码，没有向 cloud.zed.dev 发过一个真实请求。这是**零成本就能验证**的事（只需要一个 GitHub 账号 + mitmproxy）。

建议立即执行 Step 1 方案 A：**抓包 Zed 客户端**，验证我们的协议推导是否正确。