import { defineConfig } from 'vitepress';

export default defineConfig({
  title: '股票分析数据看板',
  description: '基于本地 MySQL 股票分析快照的 VitePress 数据展示',
  cleanUrls: true,
  lastUpdated: false,
  themeConfig: {
    logo: '/logo.svg',
    nav: [{ text: '分析看板', link: '/' }],
    sidebar: false,
    search: {
      provider: 'local',
    },
    outline: {
      level: [2, 3],
    },
    socialLinks: [],
  },
  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:3210',
          changeOrigin: true,
        },
      },
    },
  },
});
