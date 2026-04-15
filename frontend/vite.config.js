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
    // 启用historyApiFallback，解决SPA路由刷新404问题
    historyApiFallback: true,
    // 禁用对node_modules中文件的source map加载
    sourcemapIgnoreList: (source) => {
      return source.includes('node_modules')
    },
    proxy: {
      // 匹配 CottonOGD_api 路径
      '^/CottonOGD_api': {
        target: 'http://172.28.226.114:8000',
        //target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      // 匹配 admin 路径及其子路径
      '^/admin.*': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      // 匹配 admin 路径
      '^/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      // 匹配 data/genome 路径
      '^/data/genome': {
        target: 'http://172.28.226.114:8000',
        //target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      // 匹配 download_genome 路径
      '^/download_genome': {
        target: 'http://172.28.226.114:8000',
        //target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      // 匹配 jbrowse 路径
      '^/jbrowse': {
        target: 'http://172.28.226.114:8000',
        //target: 'http://127.0.0.1:8000',
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