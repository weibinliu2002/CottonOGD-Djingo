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
      // 使用正则表达式匹配所有需要转发的路径
      '^/(api|tools|jbrowse|assets/jbrowse|Browse)': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => {
          // 只有/api路径需要去掉前缀，其他路径直接转发
          if (path.startsWith('/api')) {
            return path.replace(/^\/api/, '');
          }
          return path;
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})