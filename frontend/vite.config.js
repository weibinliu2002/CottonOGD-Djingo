import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const DJANGO_TARGET = 'http://172.28.226.114:8000'
const SEQUENCE_SERVER_TARGET = 'http://172.28.226.114:4567'

// https://vite.dev/config/
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'chart-js': ['chart.js'],
          d3: ['d3'],
          tools: ['heatmap.js']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },
  publicDir: 'public',
  plugins: [
    AutoImport({
      resolvers: [ElementPlusResolver()]
    }),
    Components({
      resolvers: [ElementPlusResolver()]
    }),
    vue()
  ],
  server: {
    port: 5713,
    hmr: true,
    historyApiFallback: true,
    sourcemapIgnoreList: (source) => source.includes('node_modules'),
    proxy: {
      '^/CottonOGD_api': {
        target: DJANGO_TARGET,
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      '^/admin': {
        target: DJANGO_TARGET,
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      '^/data/genome': {
        target: DJANGO_TARGET,
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      '^/download_genome': {
        target: DJANGO_TARGET,
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      '^/jbrowse': {
        target: DJANGO_TARGET,
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      '^/assets/jbrowse': {
        target: DJANGO_TARGET,
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost'
      },
      '^/sequence-server': {
        target: SEQUENCE_SERVER_TARGET,
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => path.replace(/^\/sequence-server/, '')
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
