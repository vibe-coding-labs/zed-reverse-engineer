# 🧠 Zed Reverse Engineer

> 📖 **在线文档**: [https://vibe-coding-labs.github.io/zed-reverse-engineer](https://vibe-coding-labs.github.io/zed-reverse-engineer)

对 [Zed](https://zed.dev/) 编辑器进行逆向分析的开源项目。

## 🎯 目标

1. **分析清楚 Zed 的 AI 通信协议** — 与 cloud.zed.dev 的交互方式
2. **分析清楚登录授权协议** — GitHub OAuth、LLM Token、认证流程
3. **设计反向代理方案** — 将 Zed 的 AI 能力/协议适配给 Claude Code、Codex 等工具

## 📖 在线文档

所有分析文档已整理为 VitePress 文档网站，阅读体验更好：

[**https://vibe-coding-labs.github.io/zed-reverse-engineer**](https://vibe-coding-labs.github.io/zed-reverse-engineer)

| 页面 | 说明 |
|------|------|
| [整体架构分层](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/overview) | 243 个 crate 六大层次全景与核心数据流 |
| [Agent 核心设计](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/agent-core) | Thread 主循环、工具调度、权限确认、沙箱、中止恢复 |
| [Agent 工具系统](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/agent-tools) | AgentTool 契约、32+ 工具分类、流式编辑、MCP |
| [ACP 与外部 Agent](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/agent-servers) | AgentServer 抽象、JSON-RPC 桥接、Claude Code 接入 |
| [LLM 抽象层与 Provider](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/language-model-layer) | LanguageModel 三层抽象、20 个 Provider 适配矩阵 |
| [会话持久化](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/agent-persistence) | Thread 的 SQLite schema、zstd 序列化、保存/恢复时机 |
| [ACP 协议客户端](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/acp-protocol-client) | 双向 JSON-RPC 方法清单、SessionUpdate 通知、终端事件流 |
| [Agent UI 与技能](https://vibe-coding-labs.github.io/zed-reverse-engineer/architecture/agent-ui-skills) | 面板状态机、消息渲染、Skills 目录/格式/优先级 |
| [AI 通信协议](https://vibe-coding-labs.github.io/zed-reverse-engineer/protocol/ai-protocol) | LLM Completion API、ACP 协议、流式机制 |
| [登录授权协议](https://vibe-coding-labs.github.io/zed-reverse-engineer/protocol/auth-protocol) | GitHub OAuth、LLM Token、WebSocket |
| [反向代理方案](https://vibe-coding-labs.github.io/zed-reverse-engineer/design/reverse-proxy) | 3 种方案对比、实现细节 |
| [免费额度分析](https://vibe-coding-labs.github.io/zed-reverse-engineer/analysis/free-tier) | Free/Pro 限制、BYOK 方案 |
| [试用绕过分析](https://vibe-coding-labs.github.io/zed-reverse-engineer/analysis/trial-bypass) | 14 天试用机制、多账号策略 |
| [工作盲区](https://vibe-coding-labs.github.io/zed-reverse-engineer/analysis/blindspots) | 盲区盘点、P0/P1/P2 优先级 |

## 📦 二进制文件

各平台预编译二进制下载到 `data/` 目录下（v1.6.3）：

| 平台 | 架构 | 文件 | 大小 |
|------|------|------|------|
| Linux | x86_64 | `data/linux/zed-linux-x86_64.tar.gz` | 84 MB |
| macOS | Apple Silicon | `data/macos/zed-macos-aarch64.dmg` | 135 MB |
| macOS | Intel | `data/macos/zed-macos-x86_64.dmg` | 75 MB |
| Windows | x86_64 | `data/windows/zed-windows-x86_64.exe` | 82 MB |
| Windows | ARM64 | `data/windows/zed-windows-aarch64.exe` | 70 MB |

## 🐍 Python 脚本

| 脚本 | 说明 |
|------|------|
| `scripts/zed_auth.py` | Zend 授权协议 Python 实现（RSA 加密、OAuth、API 调用） |
| `scripts/zed_auth_flow.py` | OAuth 全自动化脚本（Playwright + GitHub 登录） |
| `scripts/zed_mock_server.py` | Cloud API Mock Server |
| `scripts/zed_live_test.py` | 真实 API 测试脚本 |
| `scripts/capture_zed.py` | mitmproxy 抓包脚本 |

## 🏗️ 架构速览

```
Zed Editor
  │
  ├── CloudLanguageModelProvider (provider_id = "zed.dev")
  │     │
  │     ├── POST /completions   ──→  cloud.zed.dev  ──→  Anthropic/OpenAI/Google/xAI
  │     ├── GET  /models        ──→  cloud.zed.dev
  │     └── POST /llm_tokens    ──→  cloud.zed.dev  (获取Bearer Token)
  │
  ├── Anthropic Provider (直连)  ──→  api.anthropic.com
  ├── OpenAI Provider (直连)     ──→  api.openai.com
  ├── Google Provider (直连)     ──→  generativelanguage.googleapis.com
  ├── Ollama (本地)               ──→  localhost:11434
  ├── LM Studio (本地)            ──→  localhost:1234
  │
  └── ACP (Agent Communication Protocol)
        └── JSON-RPC 2.0 over stdio  ──→  Claude Code CLI / Codex CLI / OpenCode
```

## 🔑 关键发现

### AI 通信协议

- **核心端点**: `POST https://cloud.zed.dev/completions`
- **认证**: `Authorization: Bearer {llm_token}`
- **请求体**: `CompletionBody` 包含 `provider`、`model`、`provider_request`（原始上游格式）
- **流式响应**: JSON Lines 格式，每行是 `{"Status": ...}` 或 `{"Event": ...}`

### 认证流程

```
GitHub OAuth → user_id + access_token → POST /client/llm_tokens → Bearer Token
```

- LLM Token 按 `organization_id` 缓存
- 过期通过响应头 `x-zed-expired-token` 通知刷新
- 可使用 `ZED_SERVER_URL` 环境变量覆盖服务端地址

### 试用与付费

| 计划 | 价格 | 托管LLM | 编辑预测 |
|------|------|---------|---------|
| Free | $0 | ❌ | 2000次 |
| Pro | $10/月 | $5额度+按量 | 无限 |
| Pro Trial | 14天免费 | $20额度(不含Opus) | 无限 |
| Business | $30/座位/月 | 按量 | 无限 |

**Zed 本身不持有算力，所有模型都是租用的上游 API。**

## 🚀 反向代理方案

利用 `ZED_SERVER_URL` 环境变量劫持流量到自建代理：

```bash
ZED_SERVER_URL=http://localhost:3000 zed
```

代理需要实现 4 个核心端点：`/completions`、`/models`、`/client/llm_tokens`、`/client/users/me`。

详细方案见 [反向代理方案设计](https://vibe-coding-labs.github.io/zed-reverse-engineer/design/reverse-proxy)

## 📁 项目结构

```
zed-reverse-engineer/
├── README.md
├── LICENSE                 # Apache 2.0
├── .github/workflows/      # GitHub Actions 部署
├── docs/                   # VitePress 文档网站源码
│   ├── .vitepress/
│   ├── protocol/           # 通信协议文档
│   ├── design/             # 方案设计文档
│   └── analysis/           # 深度分析文档
├── data/                   # 各平台预编译二进制
├── scripts/                # Python 脚本
└── notes/                  # 原始分析笔记
```

## ⚖️ 许可证

Apache 2.0

## 🙏 致谢

- [Zed](https://zed.dev/) — 优秀的开源编辑器
- [Zed Source Code](https://github.com/zed-industries/zed) — 本项目的分析基础