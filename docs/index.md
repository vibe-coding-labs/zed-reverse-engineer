---
layout: home

hero:
  name: Zed Reverse Engineer
  text: Zed 编辑器逆向分析
  tagline: AI 通信协议 · 登录授权流程 · 反向代理方案 · 开源存档
  image:
    src: /hero.svg
    alt: Zed Reverse Engineer
  actions:
    - theme: brand
      text: AI 通信协议 →
      link: /protocol/ai-protocol
    - theme: brand
      text: 登录授权协议 →
      link: /protocol/auth-protocol
    - theme: alt
      text: 反向代理方案 →
      link: /design/reverse-proxy
    - theme: alt
      text: GitHub 仓库
      link: https://github.com/vibe-coding-labs/zed-reverse-engineer

features:
  - icon: 🔬
    title: AI 通信协议
    details: 深入分析 Zed 与 cloud.zed.dev 的 AI 通信协议，包括 LLM Completion API、ACP 协议、流式响应格式
    link: /protocol/ai-protocol
  - icon: 🔐
    title: 登录授权协议
    details: 完整剖析 GitHub OAuth 登录流程、LLM Token 认证、WebSocket 连接、计费系统
    link: /protocol/auth-protocol
  - icon: 🔀
    title: 反向代理方案
    details: 设计 ZED_SERVER_URL 劫持方案，实现协议转换，适配 Claude Code/Codex 等工具
    link: /design/reverse-proxy
  - icon: 💰
    title: 免费额度分析
    details: 全面评估 Free/Pro 限制、14天试用机制、多账号轮换策略
    link: /analysis/free-tier
  - icon: 🐍
    title: Python 脚本
    details: 提供完整的 Python 授权模拟脚本，包含 RSA 加密、OAuth 回调、API 调用
    link: https://github.com/vibe-coding-labs/zed-reverse-engineer/tree/main/scripts
  - icon: 📦
    title: 各平台二进制
    details: 已存档 Linux/macOS/Windows 各平台 Zed 预编译二进制，供离线分析
    link: https://github.com/vibe-coding-labs/zed-reverse-engineer/tree/main/data
---