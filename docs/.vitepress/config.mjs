import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/zed-reverse-engineer/',
  title: 'Zed Reverse Engineer',
  description: 'Zed Editor 逆向分析 — AI协议、登录授权、反向代理方案',
  lang: 'zh-CN',
  lastUpdated: true,

  head: [
    ['meta', { name: 'theme-color', content: '#00a67e' }],
    ['link', { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' }],
  ],

  themeConfig: {
    logo: '/favicon.svg',

    nav: [
      { text: '首页', link: '/' },
      { text: '通信协议', link: '/protocol/ai-protocol' },
      { text: '授权协议', link: '/protocol/auth-protocol' },
      { text: '深度分析', link: '/protocol/deep-dive' },
      { text: '方案设计', link: '/design/reverse-proxy' },
      { text: '架构分析', link: '/architecture/overview' },
      { text: '分析', link: '/analysis/free-tier' },
    ],

    sidebar: {
      '/protocol/': [
        {
          text: '通信协议',
          items: [
            { text: 'AI 通信协议分析', link: '/protocol/ai-protocol' },
            { text: '登录授权协议分析', link: '/protocol/auth-protocol' },
            { text: '全链路深度分析', link: '/protocol/deep-dive' },
          ],
        },
      ],
      '/architecture/': [
        {
          text: '架构分析',
          items: [
            { text: '整体架构分层', link: '/architecture/overview' },
            { text: 'Agent 核心设计', link: '/architecture/agent-core' },
            { text: 'Agent 工具系统', link: '/architecture/agent-tools' },
            { text: 'ACP 与外部 Agent', link: '/architecture/agent-servers' },
            { text: 'LLM 抽象层与 Provider', link: '/architecture/language-model-layer' },
            { text: '会话持久化', link: '/architecture/agent-persistence' },
            { text: 'ACP 协议客户端', link: '/architecture/acp-protocol-client' },
            { text: 'Agent UI 与技能', link: '/architecture/agent-ui-skills' },
          ],
        },
      ],
      '/design/': [
        {
          text: '方案设计',
          items: [
            { text: '反向代理方案设计', link: '/design/reverse-proxy' },
          ],
        },
      ],
      '/analysis/': [
        {
          text: '深度分析',
          items: [
            { text: '免费额度分析', link: '/analysis/free-tier' },
            { text: '试用绕过分析', link: '/analysis/trial-bypass' },
            { text: '工作盲区分析', link: '/analysis/blindspots' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/vibe-coding-labs/zed-reverse-engineer' },
    ],

    footer: {
      message: '基于 Apache 2.0 许可证开源',
      copyright: `© ${new Date().getFullYear()} Vibe Coding Labs`,
    },

    editLink: {
      pattern: 'https://github.com/vibe-coding-labs/zed-reverse-engineer/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页',
    },

    lastUpdatedText: '最后更新',
  },
})