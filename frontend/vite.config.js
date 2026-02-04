import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vite.dev/config/
export default defineConfig({
  // vite.config.js
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // 将大型库单独打包
          'element-plus': ['element-plus'],
          'chart-js': ['chart.js'],
          'd3': ['d3'],
          'tools': ['heatmap.js'],
        }
      }
    },
    chunkSizeWarningLimit: 1000 // 调整chunk大小警告阈值
  },
  // 显式设置publicDir配置
  publicDir: 'public',
  plugins: [
    // ...
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
    vue()
  ],
  server: {
    port: 5713,
    hmr: true,
    proxy: {
      // 匹配 CottonOGD_api 路径
      '^/CottonOGD_api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      // 匹配 data/genome 路径
      '^/data/genome': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})