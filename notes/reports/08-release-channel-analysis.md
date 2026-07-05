# 循环分析报告 #8 — 发布渠道与版本控制系统

**分析时间**: 2026-07-05
**源码位置**: `crates/release_channel/src/lib.rs` (292 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 有 4 个发布渠道，由编译时确定的 `RELEASE_CHANNEL` 文件控制。

## 发布渠道

| 渠道 | 标识 | 显示名 | App ID | 更新检查 |
|------|------|--------|--------|----------|
| Dev | `dev` | Zed Dev | `dev.zed.Zed-Dev` | ❌ 不检查更新 |
| Nightly | `nightly` | Zed Nightly | `dev.zed.Zed-Nightly` | ✅ |
| Preview | `preview` | Zed Preview | `dev.zed.Zed-Preview` | ✅ |
| Stable | `stable` | Zed | `dev.zed.Zed` | ✅ |

## 渠道选择

渠道在编译时从 `zed/RELEASE_CHANNEL` 文件读取。Dev 模式下可通过 `ZED_RELEASE_CHANNEL` 环境变量覆盖。

## 版本号构建

```rust
// 版本格式: {pkg_version}+{channel}.{build_id}.{commit_sha}
// 示例: 1.6.3+stable.20260704.abc1234
// 可通过 ZED_APP_VERSION 环境变量覆盖
pub fn load(pkg_version, build_id, commit_sha) -> Version
```

## 与反向代理的关系

反向代理需要关注 `x-zed-version` 请求头，这个头来自 `AppVersion::global()`。客户端的版本号影响：
- 服务端兼容性判断（`x-zed-minimum-required-version` 响应头）
- 功能开关（某些 API 只在特定版本后可用）

## 关键发现

- `dev` 渠道不检查更新，适合本地开发
- 版本号包含 build ID 和 commit SHA，可用于精确追踪
- `ZED_APP_VERSION` 环境变量可覆盖版本号