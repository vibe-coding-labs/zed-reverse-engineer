# 循环分析报告 #17 — LiveKit 音视频通话 (WebRTC)

**分析时间**: 2026-07-06
**源码位置**: `crates/livekit_client/src/` (1,941 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 使用 [LiveKit](https://livekit.io) 作为音视频通话的 WebRTC 基础设施。LiveKit 是一个开源 SFU (Selective Forwarding Unit) 服务器。

## 房间模型

```rust
pub enum RoomEvent {
    Connected,                          // 连接建立
    Disconnected { reason },            // 断开连接
    ParticipantConnected,               // 参与者加入
    ParticipantDisconnected,            // 参与者离开
    TrackSubscribed,                    // 订阅音视频轨
    TrackUnsubscribed,                  // 取消订阅
    TrackPublished,                     // 发布音视频轨
    ActiveSpeakersChanged { speakers }, // 当前发言人变更
    ConnectionQualityChanged,           // 连接质量变更
    RoomMetadataChanged,                // 房间元数据变更
    Reconnecting,                       // 重连中
    Reconnected,                        // 重连成功
}
```

## 音频处理

使用 `cpal`（跨平台音频库）和 `rodio`（音频播放库）处理音频输入输出。支持多种采样格式转换（I8/I16/I24/I32/F32）。

## 连接质量

```rust
pub enum ConnectionQuality {
    Excellent,
    Good,
    Poor,
    Lost,
}
```

## 与反向代理的关系

不相关。LiveKit 音视频通话是独立于 AI 通信的另一个子系统，不使用 HTTP 协议，而是 WebRTC/DTLS/SRTP。

## 关键文件

- `crates/livekit_client/src/livekit_client.rs` — 核心客户端实现
- `crates/livekit_client/src/remote_video_track_view.rs` — 远程视频渲染
- `crates/livekit_client/src/record.rs` — 录制支持