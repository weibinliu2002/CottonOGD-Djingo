<template>
  <div class="app">
    <!-- 顶部信息栏 -->
    <div class="top-info-bar">
      <div class="container">
        <div class="top-info-content">
          <div class="info-left">
            <!--<span class="database-status">Database version: v1.0 | Last updated: 2025-01-29</span>-->
          </div>
          <div class="info-right">
            <!-- 语言切换 -->
            <div class="language-selector">
              <select 
                v-model="currentLanguage"
                class="language-select"
              >
                <option value="en-US">English</option>
                <option value="zh-CN">中文</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 头部容器 -->
    <header class="header">
      <div class="container">
        <div class="header-inner">
          <!-- Logo和标题 -->
          <div class="header-brand">
            <div class="logo-container">
              <img src="@/assets/images/favicon.png" alt="CottonOGD Logo" class="logo">
            </div>
            <div class="brand-text">
              <h1 class="brand-title">CottonOGD</h1>
              <p class="brand-subtitle">Cotton Orthogroups Database</p>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 导航栏 -->
    <nav class="main-nav">
      <div class="container">
        <div class="nav-inner">
          <!-- 导航链接 -->
          <ul class="nav-menu">
            <li class="nav-item">
              <router-link class="nav-link" to="/" exact-active-class="active">{{ t('home') }}</router-link>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                {{ t('browse') }}
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/browse/tf">{{ t('transcription_factors_') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/browse/tr">{{ t('transposons') }}</router-link></li>
              </ul>
            </li>
            
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                {{ t('Genome Brower') }}
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/jbrowse">{{ t('jbrowse_view') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/IGV">{{ t('igv_view') }}</router-link></li>
              </ul>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                {{ t('tools') }}
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/tools/id-search">{{ t('id_search') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/blastp">BLASTP</router-link></li>

                <li><router-link class="dropdown-item" to="/tools/go-annotation">{{ t('go_annotation') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/kegg-annotation">{{ t('kegg_annotation') }}</router-link></li>

                <li><router-link class="dropdown-item" to="/tools/go-enrichment">{{ t('go_enrichment') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/kegg-enrichment">{{ t('kegg_enrichment') }}</router-link></li>

                
                <li><router-link class="dropdown-item" to="/tools/primer-design">{{ t('primer_design') }}</router-link></li>
              </ul>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                {{ t('Graphical Tools') }}
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/tools/clustergramme_heatmap">{{ t('clustergramme_heatmap') }}</router-link></li>
                 <li><router-link class="dropdown-item" to="/tools/canvaspress">{{ t('canvaspress') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/ppi">{{ t('ppi') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/phylotree">{{ t('phylotree') }}</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/circos">{{ t('circos') }}</router-link></li>            
              </ul>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                {{ t('Expression') }}
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/tools/gene-expression">{{ t('gene_expression') }}</router-link></li>
        
                <li><router-link class="dropdown-item" to="/tools/gene-expression-efp">{{ t('gene_expression_in_efp') }}</router-link></li>
              </ul>
          </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/download">{{ t('download') }}</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/about-us">{{ t('about') }}</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/contact-us">{{ t('contact_us') }}</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <!-- 主要内容 -->
    <main class="container">
      <router-view />
    </main>
    
    <el-dialog
      v-model="isLoading"
      width="280px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="search-loading-dialog"
      align-center
    >
      <div class="search-loading-content">
        <div class="search-loading-title">Search is running ...</div>
        <div class="search-loading-time">{{ formattedLoadingTime }}</div>
      </div>
    </el-dialog>
    
    <!-- 底部区域 -->
    <div class="footer-section">
      <!-- 页脚 -->
      <footer>
        <div class="container">
          <div class="footer-content">
            <!-- 左侧两列链接 -->
            <div class="footer-links-container">
              <div class="footer-column">
                <h4>{{ t('resources') }}</h4>
                <ul>
                  <li><a href="https://cotton.hzau.edu.cn/index.htm" target="_blank">GCGI</a></li>
                  <li><a href="https://planttfdb.gao-lab.org/" target="_blank">PlantTFDB</a></li>
                  <li><a href="https://static.pubmed.gov/portal/portal.fcgi/" target="_blank">NCBI</a></li>
                  <li><a href="https://plants.ensembl.org/index.html" target="_blank">Ensembl Plants</a></li>
                  <!--<li><a href="#" target="_blank">Phytozome</a></li>-->
                </ul>
              </div>
              <!--
              <div class="footer-column">
                <h4>Related Links</h4>
                <ul>
                  <li><a href="#" target="_blank">Cotton Research Institute</a></li>
                  <li><a href="#" target="_blank">Chinese Academy of Agricultural Sciences</a></li>
                  <li><a href="#" target="_blank">International Cotton Genome Initiative</a></li>
                  <li><a href="#" target="_blank">Plant Science Database</a></li>
                  <li><a href="#" target="_blank">Bioinformatics Resources</a></li>
                </ul>
              </div>-->
            </div>
            <!-- 右侧访问统计 -->
            <div class="footer-column visitor-map-container">
              <div id="visitor-map-placeholder"></div>
            </div>
          </div>
          <div class="footer-bottom">
            <p class="mb-0">© 2026 CottonOGD. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
    
    <!-- 回到顶部组件 -->
    <el-backtop
      :visibility-height="200"
      :right="40"
      :bottom="40"
      target=".app"
    >
      <template #default>
        <div class="backtop-content">
          <el-icon class="backtop-icon"><ArrowUp /></el-icon>
        </div>
      </template>
    </el-backtop>
  </div>
</template>

<script setup>
import { ref, provide, onMounted, computed, watch } from 'vue'
import { ArrowUp } from '@element-plus/icons-vue'
import httpInstance from './utils/http.js'
import { useRouter } from 'vue-router'
import { setLocale, getLocale } from './locales/i18n-config'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { t } = useI18n()

// 定义全局加载状态
const isLoading = ref(false)
const loadingRequestCount = ref(0)
const loadingSeconds = ref(0)
let loadingTimer = null
let loadingDelayTimer = null
const LOADING_DIALOG_DELAY_MS = 500

// 搜索相关
const searchQuery = ref('')

// 当前语言
const currentLanguage = computed({
  get: () => getLocale(),
  set: (value) => {
    setLocale(value)
    console.log('Switched to language:', value)
  }
})

// 定义加载状态管理方法
const showLoading = () => {
  loadingRequestCount.value += 1
  if (loadingRequestCount.value === 1) {
    if (loadingDelayTimer) {
      clearTimeout(loadingDelayTimer)
    }
    loadingDelayTimer = setTimeout(() => {
      loadingDelayTimer = null
      if (loadingRequestCount.value > 0) {
        loadingSeconds.value = 0
        isLoading.value = true
        if (loadingTimer) {
          clearInterval(loadingTimer)
        }
        loadingTimer = setInterval(() => {
          loadingSeconds.value += 1
        }, 1000)
      }
    }, LOADING_DIALOG_DELAY_MS)
  }
}

const hideLoading = () => {
  if (loadingRequestCount.value > 0) {
    loadingRequestCount.value -= 1
  }
  if (loadingRequestCount.value === 0) {
    if (loadingDelayTimer) {
      clearTimeout(loadingDelayTimer)
      loadingDelayTimer = null
    }
    isLoading.value = false
    if (loadingTimer) {
      clearInterval(loadingTimer)
      loadingTimer = null
    }
  }
}

const formattedLoadingTime = computed(() => {
  const hours = Math.floor(loadingSeconds.value / 3600)
  const minutes = Math.floor((loadingSeconds.value % 3600) / 60)
  const seconds = loadingSeconds.value % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

// 提供全局加载状态和方法
provide('isLoading', isLoading)
provide('showLoading', showLoading)
provide('hideLoading', hideLoading)

// 搜索方法
const performSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({
      path: '/tools/id-search',
      query: { query: searchQuery.value.trim() }
    })
  }
}

// 添加访问统计脚本
const addVisitorMapScript = () => {
  // 检查脚本是否已存在
  if (document.getElementById('mapmyvisitors')) {
    return
  }
  
  // 创建脚本标签
  const script = document.createElement('script')
  script.id = 'mapmyvisitors'
  script.type = 'text/javascript'
  script.src = '//mapmyvisitors.com/map.js?d=NEeGKeJYzuEK_tzwYqYTyDNOAHaX0_9xt6Z6e5wQyBo&cl=ffffff&w=a'
  
  // 添加错误处理
  script.onerror = () => {
    console.warn('Failed to load visitor map script, this will not affect other functionality')
    const placeholder = document.getElementById('visitor-map-placeholder')
    if (placeholder) {
      placeholder.innerHTML = '<p class="text-muted">Visitor statistics unavailable</p>'
    }
  }
  
  // 添加到页脚容器
  const placeholder = document.getElementById('visitor-map-placeholder')
  if (placeholder) {
    placeholder.appendChild(script)
  } else {
    // 如果容器不存在，添加到body
    document.body.appendChild(script)
  }
}

// 组件挂载时自动登录并添加访问统计脚本
onMounted(() => {
  httpInstance.post('/CottonOGD_api/login/')
  addVisitorMapScript()
})
</script>

<style>
/* 全局样式 */
/* 样式通过main.js引入，这里不再重复导入 */

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 顶部信息栏 */
.top-info-bar {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  padding: 8px 0;
  font-size: 14px;
  color: #6c757d;
}

.top-info-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.language-selector {
  display: flex;
  gap: 5px;
}

.language-select {
  background-color: white;
  border: 1px solid #ced4da;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
  min-width: 100px;
}

.language-select:hover {
  border-color: #466686;
}

.language-select:focus {
  outline: none;
  border-color: #466686;
  box-shadow: 0 0 0 0.2rem rgba(70, 102, 134, 0.25);
}

/* 头部样式 */
.header {
  background-color: #466686;
  padding: 20px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.header-inner {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  flex-wrap: wrap;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.logo {
  height: 60px;
  width: auto;
}

.brand-text {
  display: flex;
  flex-direction: column;
  text-align: left;
}

.brand-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: white;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.brand-subtitle {
  margin: 3px 0 0 0;
  font-size: 12px;
  color: rgba(255,255,255,0.9);
  font-weight: 400;
}

/* 导航栏样式 */
.main-nav {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.nav-menu {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 0;
  background-color: #f8f9fa;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.nav-item {
  position: relative;
}

.nav-link {
  display: block;
  color: #466686 !important;
  padding: 14px 18px !important;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
  border-radius: 0;
  border-right: 1px solid #e9ecef;
}

.nav-link:hover,
.nav-link.active {
  background-color: #e9ecef !important;
  color: #3a5470 !important;
}

/* 下拉菜单样式 */
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  background-color: white;
  border: 1px solid #e9ecef;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 4px 0;
  margin: 0;
  min-width: 200px;
  z-index: 1000;
}

.dropdown-header {
  color: #6c757d;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dropdown-divider {
  height: 1px;
  background-color: #e9ecef;
  margin: 4px 0;
}

.dropdown-item {
  color: #466686;
  padding: 8px 16px;
  text-decoration: none;
  display: block;
  transition: all 0.3s ease;
  font-size: 13px;
}

.dropdown-item:hover,
.dropdown-item:focus {
  background-color: #e9ecef;
  color: #3a5470;
}

/* 响应式导航 */
@media (max-width: 992px) {
  .header-inner {
    flex-direction: column;
    text-align: center;
  }

  .header-brand {
    flex-direction: column;
    gap: 15px;
  }

  .brand-text {
    text-align: center;
  }

  .nav-menu {
    justify-content: flex-start;
  }

  .nav-link {
    padding: 10px 14px !important;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .brand-title {
    font-size: 26px;
  }

  .brand-subtitle {
    font-size: 12px;
  }

  .logo-container {
    width: 60px;
    height: 60px;
  }

  .logo {
    height: 40px;
  }

  .header {
    padding: 20px 0;
  }

  .nav-menu {
    flex-direction: column;
    gap: 0;
  }

  .nav-link {
    border-right: none;
    border-bottom: 1px solid #e9ecef;
  }

  .dropdown-menu {
    position: static;
    border-radius: 0;
    box-shadow: none;
    border-left: 3px solid #e9ecef;
  }

  .dropdown-item {
    padding-left: 24px;
  }
}

/* 图片行样式 */
.image-row {
  display: flex;
  overflow-x: auto;
  white-space: nowrap;
}

.image-tile {
  flex: 0 0 auto;
  margin-right: 10px;
}

.image-tile img {
  max-width: 100%;
  height: auto;
}

/* 底部样式 */
.footer-section {
  margin-top: 50px;
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

footer {
  padding: 40px 0;
  color: #6c757d;
}

.footer-content {
  display: flex;
  gap: 30px;
  margin-bottom: 30px;
}

.footer-links-container {
  display: flex;
  gap: 40px;
  width: 66.67%; /* 左侧占三分之二 */
  flex-wrap: wrap;
}

.footer-links-container .footer-column {
  flex: 1;
  min-width: 200px;
}

.visitor-map-container {
  width: 33.33%; /* 右侧占三分之一 */
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px; /* 确保有足够的高度显示完整内容 */
}

#visitor-map-placeholder {
  width: 100%;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.footer-column h4 {
  color: #466686;
  margin-bottom: 15px;
  font-size: 16px;
  font-weight: 600;
}

.footer-column ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-column ul li {
  margin-bottom: 10px;
}

.footer-column ul li a {
  color: #6c757d;
  text-decoration: none;
  transition: color 0.3s ease;
}

.footer-column ul li a:hover {
  color: #466686;
}

.footer-column ul li i {
  margin-right: 8px;
  color: #7297bd;
}

.footer-bottom {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
  font-size: 14px;
}

/* 响应式容器 */
.container {
  width: 100%;
  max-width: 1400px;
  padding-right: 15px;
  padding-left: 15px;
  margin-right: auto;
  margin-left: auto;
}

/* 回到顶部按钮样式 */
.backtop-content {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #7297bd;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.backtop-content:hover {
  background-color: #5a81a8;
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.backtop-icon {
  font-size: 20px;
}

/* 检索计时弹窗 */
.search-loading-dialog .el-dialog {
  border: 1px solid #8fb8e8;
  border-radius: 0;
}

.search-loading-dialog .el-dialog__header {
  padding: 0;
}

.search-loading-dialog .el-dialog__body {
  padding: 18px 20px;
}

.search-loading-content {
  text-align: center;
}

.search-loading-title {
  color: #2f5f94;
  font-weight: 700;
  font-size: 24px;
  line-height: 1.1;
  margin-bottom: 10px;
}

.search-loading-time {
  color: #2f5f94;
  font-family: "Consolas", "Courier New", monospace;
  font-size: 28px;
  letter-spacing: 1px;
}

/* 统一 reset 按钮样式 */
.reset-action-btn {
  border: 1px solid #8aa3bf !important;
  color: #466686 !important;
  background-color: #f4f7fb !important;
  border-radius: 8px !important;
  transition: all 0.2s ease;
}

.reset-action-btn:hover,
.reset-action-btn:focus {
  border-color: #5d7e9f !important;
  background-color: #e9f0f8 !important;
  color: #355a80 !important;
}

/* 响应式设计 */
@media (max-width: 992px) {
  .head-content {
    flex-direction: column;
    text-align: center;
    gap: 20px;
  }

  .search-section {
    max-width: 100%;
    width: 100%;
  }

  .navbar-nav {
    gap: 0;
  }

  .nav-link {
    padding: 10px 15px !important;
  }
}

@media (max-width: 768px) {
  .top-info-content {
    flex-direction: column;
    gap: 10px;
    text-align: center;
  }

  .site-title h1 {
    font-size: 32px;
  }

  .site-title p {
    font-size: 16px;
  }

  .footer-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
</style>
