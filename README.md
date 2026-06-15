# 🧠 Zed Reverse Engineer

对 [Zed](https://zed.dev/) 编辑器进行逆向分析的开源项目。

## 🎯 目标

1. **分析清楚 Zed 的 AI 通信协议** — 与 cloud.zed.dev 的交互方式
2. **分析清楚登录授权协议** — GitHub OAuth、LLM Token、认证流程
3. **设计反向代理方案** — 将 Zed 的 AI 能力/协议适配给 Claude Code、Codex 等工具

## 📦 二进制文件

各平台预编译二进制下载到 `data/` 目录下（v1.6.3）：

| 平台 | 架构 | 文件 | 大小 |
|------|------|------|------|
| Linux | x86_64 | `data/linux/zed-linux-x86_64.tar.gz` | 84 MB |
| macOS | Apple Silicon | `data/macos/zed-macos-aarch64.dmg` | 135 MB |
| macOS | Intel | `data/macos/zed-macos-x86_64.dmg` | 75 MB |
| Windows | x86_64 | `data/windows/zed-windows-x86_64.exe` | 82 MB |
| Windows | ARM64 | `data/windows/zed-windows-aarch64.exe` | 70 MB |

## 🔬 分析文档

| # | 文档 | 说明 |
|---|------|------|
| 1 | [AI通信协议分析](notes/01-ai-protocol-analysis.md) | LLM Completion API、ACP协议、请求/响应格式、流式机制 |
| 2 | [登录授权协议分析](notes/02-auth-protocol-analysis.md) | GitHub OAuth、LLM Token、WebSocket、计费系统 |
| 3 | [反向代理方案设计](notes/03-reverse-proxy-design.md) | 3种方案对比、推荐方案、实现细节 |
| 4 | [免费额度分析](notes/04-free-tier-analysis.md) | Free/Pro 限制、自带Key方案 |
| 5 | [试用机制分析](notes/05-trial-bypass-analysis.md) | 14天Pro试用源码级分析、绕过方案评估 |

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
- **状态消息**: Server 可发 Queued/Started/StreamEnded/Failed 状态

### 认证流程

```
GitHub OAuth → user_id + access_token → POST /client/llm_tokens → Bearer Token
```
- LLM Token 按 `organization_id` 缓存
- 过期通过响应头 `x-zed-expired-token` 通知刷新
- WebSocket `wss://cloud.zed.dev/client/users/connect` 保持实时连接
- 可使用 `ZED_SERVER_URL` 环境变量覆盖服务端地址

### 试用与付费

| 计划 | 价格 | 托管LLM | 编辑预测 |
|------|------|---------|---------|
| Free | $0 | ❌ | 2000次 |
| Pro | $10/月 | $5额度+按量 | 无限 |
| Pro Trial | 14天免费 | $20额度(不含Opus) | 无限 |
| Business | $30/座位/月 | 按量(无限定额度) | 无限 |

**Zed 本身不持有算力，所有模型都是租用的上游 API**。试用结束后要么付费，要么自备 API Key。

## 🚀 反向代理方案（推荐）

利用 `ZED_SERVER_URL` 环境变量劫持流量到自建代理：

```bash
ZED_SERVER_URL=http://localhost:3000 zed
```

代理需要实现 4 个核心端点：`/completions`、`/models`、`/client/llm_tokens`、`/client/users/me`。

详细方案见 [notes/03-reverse-proxy-design.md](notes/03-reverse-proxy-design.md)

## 📁 项目结构

```
zed-reverse-engineer/
├── README.md
├── LICENSE                # Apache 2.0
├── data/                  # 各平台预编译二进制
│   ├── linux/
│   │   └── zed-linux-x86_64.tar.gz
│   ├── macos/
│   │   ├── zed-macos-aarch64.dmg
│   │   └── zed-macos-x86_64.dmg
│   └── windows/
│       ├── zed-windows-x86_64.exe
│       └── zed-windows-aarch64.exe
└── notes/                 # 分析文档
    ├── 01-ai-protocol-analysis.md
    ├── 02-auth-protocol-analysis.md
    ├── 03-reverse-proxy-design.md
    ├── 04-free-tier-analysis.md
    └── 05-trial-bypass-analysis.md
```

## ⚖️ 许可证

Apache 2.0

## 🙏 致谢

- [Zed](https://zed.dev/) — 优秀的开源编辑器
- [Zed Source Code](https://github.com/zed-industries/zed) — 本项目的分析基础
