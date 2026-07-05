# 循环分析报告 #18 — Agent 服务器存储 (Agent Server Store)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/agent_server_store.rs` (2,129 行)
**分析前状态**: ⚠️ 之前接触过 ACP 协议，但 Agent 服务器配置系统没碰过

## 概述

`AgentServerStore` 管理 Zed 中的所有 Agent 服务器配置。Agent 可以是内置的（如 Gemini），也可以是用户自定义的外部 CLI 进程。

## Agent 定义

```rust
pub struct AgentServerCommand {
    pub path: PathBuf,         // 可执行文件路径
    pub args: Vec<String>,     // 命令行参数
    pub env: Option<HashMap<String, String>>,  // 环境变量
}
```

Agent 通过 `AgentId` 标识（基于 SharedString 的透明包装），通过 ACP 协议连接。

## Agent 来源

```rust
pub enum ExternalAgentSource {
    Custom,    // 用户手动配置
    Registry,  // 从 Agent 注册表安装
}
```

## 存储状态

```rust
enum AgentServerStoreState {
    Local {
        node_runtime: NodeRuntime,
        fs: Arc<dyn Fs>,
        http_client: Arc<dyn HttpClient>,
        settings: Option<AllAgentServersSettings>,
    },
    Remote {
        project_id: u64,
        upstream_client: Entity<RemoteClient>,
    },
}
```

本地模式下使用 `http_client` 从注册表下载 Agent；远程模式下通过 `upstream_client` 代理。

## 与反向代理的关系

Agent 服务器的配置直接决定了 ACP 如何与外部 Agent 进程通信。如果要做 ACP 桥接方案，需要理解 `AgentServerStore` 如何管理命令参数和环境变量。

## 关键文件

- `crates/project/src/agent_server_store.rs` — Agent 服务器配置管理
- `crates/project/src/agent_registry_store.rs` — Agent 注册表（从 GitHub/zed.dev 安装 Agent）