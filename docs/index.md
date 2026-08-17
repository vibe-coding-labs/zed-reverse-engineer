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
      text: 架构分析 →
      link: /architecture/overview
    - theme: alt
      text: 反向代理方案 →
      link: /design/reverse-proxy

features:
  - icon: 🧩
    title: 整体架构分层
    details: 243 个 crate 全景归类，GPUI/Workspace/Agent/云服务六大层次与核心数据流
    link: /architecture/overview
  - icon: 🤖
    title: Agent 核心设计
    details: Thread 主循环、工具调度、权限确认、沙箱隔离、中止恢复的完整机制
    link: /architecture/agent-core
  - icon: 🛠️
    title: Agent 工具系统
    details: AgentTool 契约、32+ 内置工具分类、流式编辑会话、MCP 集成、撤销机制
    link: /architecture/agent-tools
  - icon: 🔌
    title: ACP 与外部 Agent
    details: AgentServer 统一抽象、JSON-RPC over stdio 桥接、Claude Code/Codex 接入、会话持久化
    link: /architecture/agent-servers
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