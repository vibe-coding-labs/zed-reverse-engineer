# 循环分析报告 #12 — Copilot 认证机制 (Device Flow)

**分析时间**: 2026-07-05
**源码位置**: `crates/copilot_ui/src/sign_in.rs` (708 行)
**分析前状态**: ❌ 完全没碰过

## Copilot 认证方式

Copilot 使用 **GitHub Device Authorization Flow** 进行认证，与 Zed 的 Web OAuth 不同。

## Device Flow 流程

```
1. 客户端向 GitHub 请求 device_code
2. GitHub 返回 user_code + verification_uri
3. 客户端显示: "请打开 https://github.com/login/device 输入代码: ABCD-1234"
4. 用户手动完成网页授权
5. 客户端轮询 GitHub API 直到用户授权完成
6. 获取 access_token → 用于 Copilot API 调用
```

## 与 Zed OAuth 的区别

| 特性 | Zed OAuth | Copilot Device Flow |
|------|-----------|-------------------|
| 流程 | Web 重定向 OAuth | Device Authorization Flow |
| 用户操作 | 自动跳转浏览器 | 手动输入 code |
| 回调 | 本地 HTTP 服务器 | 轮询 GitHub API |
| 适用场景 | 桌面应用 | 无浏览器/CLI 环境 |

## Copilot 状态机

```rust
enum Status {
    Checking,           // 检查状态中
    SigningIn,          // 登录中
    SignedOut,          // 已登出
    Authorized,         // 已授权
}
```

## 关键文件

- `crates/copilot_ui/src/sign_in.rs` — 登录 UI 和 Device Flow 实现
- `crates/copilot/src/` — Copilot 核心实现