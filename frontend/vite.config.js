import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const DJANGO_TARGET = 'http://172.28.226.114:8000'
//const DJANGO_TARGET = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 读取 .env.local 中的天地图密钥（仅 dev server 端使用，不打包进前端）
  const env = loadEnv(mode, process.cwd(), '')
  const tiandituKey = env.TIANDITU_KEY || ''

  return {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'chart-js': ['chart.js'],
          d3: ['d3'],
          tools: ['heatmap.js'],
          'vue-vendor': ['vue', 'vue-router', 'pinia', 'vue-i18n'],
          'utils': ['axios', '@element-plus/icons-vue'],
          igv: ['igv'],
          echarts: ['echarts'],
          clustergrammer: ['clustergrammer'],
          drawrnajs: ['drawrnajs'],
          phylotree: ['phylotree']
        }
      }
    },
    chunkSizeWarningLimit: 2000
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
      // Sequence Server 代理配置
      '/blast': {
        target: 'http://172.28.226.114:4567' ,
        changeOrigin: true,
        // 把前端 /blast 开头的路径，去掉 /blast 传给后端
        rewrite: (path) => path.replace(/^\/blast/, ''),
        // 核心逻辑：拦截并改写重定向地址
        configure: (proxy, options) => {
          proxy.on('proxyRes', (proxyRes, req, res) => {
            const code = proxyRes.statusCode;
            // 拦截 301, 302, 303, 307, 308 重定向
            if ([301, 302, 303, 307, 308].includes(code)) {
              if (proxyRes.headers.location) {
                const originalLocation = proxyRes.headers.location;
                
                // 情况1：后端返回了绝对路径 (如 http://172.28.226.114:4567/9fc89b49...)
                if (originalLocation.startsWith('http://172.28.226.114:4567/')) {
                  // 强行替换回前端的代理地址
                  proxyRes.headers.location = originalLocation.replace(
                    'http://172.28.226.114:4567/' , 
                    'http://localhost:5713/blast/'  // 注意改成你本地 Vue 的真实端口
                  );
                } 
                // 情况2：后端返回了相对根路径 (如 /9fc89b49...)
                else if (originalLocation.startsWith('/')) {
                  // 加上 /blast 前缀
                  proxyRes.headers.location = '/blast' + originalLocation;
                }
              }
            }
          });
        }
      },
      // Sequence Server 静态资源代理
      '/css': {
        target: 'http://172.28.226.114:4567',
        changeOrigin: true,
      },
      '/js': {
        target: 'http://172.28.226.114:4567',
        changeOrigin: true,
      },
      '/fonts': {
        target: 'http://172.28.226.114:4567',
        changeOrigin: true,
      },
      '/vendor': {
        target: 'http://172.28.226.114:4567',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://172.28.226.114:4567',
        changeOrigin: true,
      },
      // 天地图 API 代理：前端通过 /tianditu-api 加载脚本，密钥由 proxy 注入
      // 密钥存储在 .env.local（TIANDITU_KEY），源码中无明文
      '/tianditu-api': {
        target: 'http://api.tianditu.gov.cn',
        changeOrigin: true,
        rewrite: (path) => {
          const query = path.includes('?') ? path.substring(path.indexOf('?')) : ''
          return `/api${query}${query ? '&' : '?'}tk=${tiandituKey}`
        },
      },
      // 天地图瓦片图代理（地图切片请求）
      '/tianditu-tile': {
        target: 'http://t0.tianditu.gov.cn',
        changeOrigin: true,
        rewrite: (path) => {
          const query = path.includes('?') ? path.substring(path.indexOf('?')) : ''
          return path.replace(/^\/tianditu-tile/, '') + (query ? '&' : '?') + 'tk=' + tiandituKey
        },
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
  }
})
