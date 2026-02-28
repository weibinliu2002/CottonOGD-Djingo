<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

const searchQuery = ref('')
const router = useRouter()

const performSearch = () => {
  if (searchQuery.value.trim()) {
    // 跳转到搜索结果页面并传递搜索参数
    router.push({
      path: '/tools/id-search/results',
      query: { q: searchQuery.value.trim() }
    })
  }
}

const fillExample = () => {
  // 默认填充第一个示例基因ID
  searchQuery.value = 'Ghir_A01G000100'
}
</script>
<template>
  <div class="home">
    <!-- 英雄区域 -->
    <section class="hero-section">
      <div class="container">
        <div class="hero-content">
          <h1>{{ t('welcome_to_cottonogd') }}</h1>
          <p class="hero-subtitle">{{ t('a_comprehensive_cotton_orthogroups_database') }}</p>
          <p class="hero-description">
            CottonOGD provides integrated genomic, transcriptomic, and functional annotation resources for cotton research, 
            enabling researchers to explore orthogroups, gene families, and evolutionary relationships across cotton species.
          </p>
          
          <!-- 主要搜索框 -->
          <!--<div class="search-box-container">
            <el-input
              v-model="searchQuery"
              placeholder="enter_gene_id_symbol_keyword_or_sequence"
              clearable
              size="large"
              @keyup.enter="performSearch"
              class="search-input"
            >
              <template #append>
                <el-button type="primary" size="large" @click="performSearch">
                  <el-icon><Search /></el-icon>
                  {{ t('search') }}
                </el-button>
              </template>
            </el-input>
            <div class="search-tips">
              <span class="tip-label">{{ t('example') }}:</span>
              <el-tag size="small" class="tip-tag" @click="fillExample">Ghir_A01G000100</el-tag>
              <el-tag size="small" class="tip-tag" @click="fillExample">Transcription Factor</el-tag>
              <el-tag size="small" class="tip-tag" @click="fillExample">ABC transporter</el-tag>
            </div>
          </div>-->
        </div>
      </div>
    </section>
    
    <!-- 核心功能区域 -->
    <section class="features-section">
      <div class="container">
        <h2 class="section-title">{{ t('core_features') }}</h2>
        <el-row :gutter="24">
          <!-- 浏览功能 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="feature-icon">
                <i class="fas fa-database"></i>
              </div>
              <h3 class="feature-title">{{ t('browse') }}</h3>
              <p class="feature-description">
                Explore cotton genome data, species information, transcription factors, and transposable elements 
                through intuitive browsing interfaces.
              </p>
              <div class="feature-actions">
                <router-link to="/browse/tf">
                  <el-button type="primary" plain size="medium">TF Database</el-button>
                </router-link>
                <router-link to="/browse/tr">
                  <el-button type="primary" plain size="medium" class="ml-2">TR Database</el-button>
                </router-link>
              </div>
            </el-card>
          </el-col>
          
          <!-- 分析工具 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="feature-icon">
                <i class="fas fa-tools"></i>
              </div>
              <h3 class="feature-title">Analysis {{ t('tools') }}</h3>
              <p class="feature-description">
                Utilize a suite of powerful tools for sequence analysis, functional annotation, 
                expression analysis, and pathway enrichment.
              </p>
              <div class="feature-actions">
                <router-link to="/tools/blastp">
                  <el-button type="primary" plain size="medium">BLAST</el-button>
                </router-link>
                <router-link to="/tools/go-enrichment">
                  <el-button type="primary" plain size="medium" class="ml-2">{{ t('go_enrichment') }}</el-button>
                </router-link>
              </div>
            </el-card>
          </el-col>
          
          <!-- 可视化功能 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="feature-icon">
                <i class="fas fa-chart-pie"></i>
              </div>
              <h3 class="feature-title">Visualization</h3>
              <p class="feature-description">
                {{ t('view') }} genomic data interactively with {{ t('jbrowse') }}, explore gene expression patterns, 
                and visualize pathway networks.
              </p>
              <div class="feature-actions">
                <router-link to="/jbrowse">
                  <el-button type="primary" plain size="medium">{{ t('jbrowse') }}</el-button>
                </router-link>
                <router-link to="/tools/gene-expression">
                  <el-button type="primary" plain size="medium" class="ml-2">Expression</el-button>
                </router-link>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </section>
    
    <!-- 数据库统计区域 -->
    <section class="stats-section bg-light">
      <div class="container">
        <h2 class="section-title">{{ t('database_statistics') }}</h2>
        <el-row :gutter="30">
          <el-col :span="6">
            <div class="stats-card">
              <div class="stats-icon">
                <i class="fas fa-dna"></i>
              </div>
              <div class="stats-content">
                <div class="stats-value">200+</div>
                <div class="stats-label">Genomes</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stats-card">
              <div class="stats-icon">
                <i class="fas fa-gene"></i>
              </div>
              <div class="stats-content">
                <div class="stats-value">200,000+</div>
                <div class="stats-label">Annotated Genes</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stats-card">
              <div class="stats-icon">
                <i class="fas fa-users"></i>
              </div>
              <div class="stats-content">
                <div class="stats-value">15,000+</div>
                <div class="stats-label">Orthogroups</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stats-card">
              <div class="stats-icon">
                <i class="fas fa-book"></i>
              </div>
              <div class="stats-content">
                <div class="stats-value">5,000+</div>
                <div class="stats-label">Literature References</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </section>
    
    <!-- 快速访问区域 -->
    <section class="quick-access-section">
      <div class="container">
        <h2 class="section-title">{{ t('quick_access') }}</h2>
        <el-row :gutter="24">
          <el-col :span="6">
            <router-link to="/jbrowse" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-chromosome"></i>
                </div>
                <h4 class="quick-link-title">{{ t('genome') }} Browser</h4>
                <p class="quick-link-description">Interactive genome visualization with {{ t('jbrowse') }}</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/blastp" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-search"></i>
                </div>
                <h4 class="quick-link-title">{{ t('blast_search') }}</h4>
                <p class="quick-link-description">{{ t('sequence') }} similarity search across genomes</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/go-enrichment" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-project-diagram"></i>
                </div>
                <h4 class="quick-link-title">{{ t('go_enrichment') }}</h4>
                <p class="quick-link-description">Gene ontology enrichment analysis</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/gene-expression" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-chart-line"></i>
                </div>
                <h4 class="quick-link-title">{{ t('gene_expression') }}</h4>
                <p class="quick-link-description">Explore gene expression patterns</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/download" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-download"></i>
                </div>
                <h4 class="quick-link-title">Data {{ t('download') }}</h4>
                <p class="quick-link-description">{{ t('download') }} genome assemblies and annotations</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/primer-design" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-dna"></i>
                </div>
                <h4 class="quick-link-title">{{ t('primer_design') }}</h4>
                <p class="quick-link-description">Design PCR primers for gene amplification</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/browse/tf" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-user-tie"></i>
                </div>
                <h4 class="quick-link-title">TF Database</h4>
                <p class="quick-link-description">Transcription factor families and functions</p>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/id-search" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="quick-link-icon">
                  <i class="fas fa-id-card"></i>
                </div>
                <h4 class="quick-link-title">ID {{ t('search') }}</h4>
                <p class="quick-link-description">{{ t('search') }} genes by ID or symbol</p>
              </el-card>
            </router-link>
          </el-col>
        </el-row>
      </div>
    </section>
    <!--
    
    <section class="news-research-section bg-light">
      <div class="container">
        <div class="row">
         
          <div class="col-md-6">
            <h2 class="section-title">{{ t('latest') }} Research</h2>
            <el-card shadow="hover" class="research-card">
              <template #header>
                <div class="card-header">
                  <span>{{ t('genome') }}-Wide Analysis of Cotton Transcription Factors</span>
                  <el-tag type="success" size="small">{{ t('featured') }}</el-tag>
                </div>
              </template>
              <div class="research-content">
                <p>
                  Identification and characterization of transcription factor families across cotton species, 
                  revealing their evolutionary dynamics and functional diversification.
                </p>
                <div class="research-meta">
                  <span class="meta-item">
                    <i class="fas fa-user"></i> Cotton Research Team
                  </span>
                  <span class="meta-item">
                    <i class="fas fa-calendar-alt"></i> 2025-01-15
                  </span>
                </div>
                <div class="text-right mt-2">
                  <el-button type="primary" size="small">Read Article</el-button>
                </div>
              </div>
            </el-card>
          </div>
          
      
          <div class="col-md-6">
            <h2 class="section-title">{{ t('news') }} & Updates</h2>
            <el-timeline>
              <el-timeline-item timestamp="2025-01-20" placement="top">
                <div class="timeline-content">
                  <h4 class="timeline-title">Database {{ t('update') }} v1.2 Released</h4>
                  <p>Updated with latest cotton genome annotations and new analysis tools.</p>
                  <el-button type="text" size="small">Read more</el-button>
                </div>
              </el-timeline-item>
              <el-timeline-item timestamp="2024-12-15" placement="top">
                <div class="timeline-content">
                  <h4 class="timeline-title">New Publication</h4>
                  <p>New research paper published on cotton orthogroups using CottonOGD data.</p>
                  <el-button type="text" size="small">Read more</el-button>
                </div>
              </el-timeline-item>
              <el-timeline-item timestamp="2024-11-30" placement="top">
                <div class="timeline-content">
                  <h4 class="timeline-title">Upcoming Features</h4>
                  <p>Enhanced gene expression analysis tools and integrated pathway viewer coming soon.</p>
                  <el-button type="text" size="small">Read more</el-button>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>
      </div>
    </section>-->
    
    <!-- 合作伙伴与引用区域 -->
     <!--
    <section class="partners-section">
      <div class="container">
        <h2 class="section-title">{{ t('partners_citations') }}</h2>
        <div class="partners-content">
          <div class="citation-info">
            <div class="citation-icon">
              <i class="fas fa-quote-left"></i>
            </div>
            <div class="citation-text">
              <p>
                "CottonOGD has become an essential resource for our cotton research, providing comprehensive 
                orthogroup information and powerful analysis tools that have accelerated our discoveries."
              </p>
              <div class="citation-author">- Dr. XXXX, Professor of Plant Genomics</div>
            </div>
          </div>
          <div class="partners-logos">
            <h3>Collaborating Institutions</h3>
            <div class="logos-grid">
              <div class="logo-item">
                <i class="fas fa-university" style="font-size: 48px; color: #666;"></i>
                <span>University A</span>
              </div>
              <div class="logo-item">
                <i class="fas fa-university" style="font-size: 48px; color: #666;"></i>
                <span>Institute B</span>
              </div>
              <div class="logo-item">
                <i class="fas fa-university" style="font-size: 48px; color: #666;"></i>
                <span>Research Center C</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>-->
  </div>
</template>

<style scoped>
.home {
  padding-bottom: 0;
}

/* 英雄区域 */
.hero-section {
  background: linear-gradient(135deg, #3a6ea5 0%, #7297bd 100%);
  color: #ffffff;
  padding: 60px 0;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%25%22 height=%22100%25%22%3E%3Cdefs%3E%3Cpattern id=%22grid%22 width=%2240%22 height=%2240%22 patternUnits=%22userSpaceOnUse%22%3E%3Cpath d=%22M 40 0 L 0 0 0 40%22 fill=%22none%22 stroke=%22rgba(255,255,255,0.1)%22 stroke-width=%221%22/%3E%3C/pattern%3E%3C/defs%3E%3Crect width=%22100%25%22 height=%22100%25%22 fill=%22url(%23grid)%22/%3E%3C/svg%3E');
  opacity: 0.3;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 0 auto;
}

.hero-section h1 {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #ffffff;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.hero-subtitle {
  font-size: 24px;
  font-weight: 500;
  margin-bottom: 24px;
  color: rgba(255, 255, 255, 0.9);
}

.hero-description {
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 32px;
  color: rgba(255, 255, 255, 0.85);
}

/* 搜索框 */
.search-box-container {
  max-width: 700px;
  margin: 0 auto;
  background-color: rgba(255, 255, 255, 0.95);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.search-input {
  width: 100%;
  border-radius: 8px;
}

.search-tips {
  margin-top: 12px;
  text-align: left;
  font-size: 14px;
  color: #666;
}

.tip-label {
  font-weight: 500;
  margin-right: 10px;
}

.tip-tag {
  cursor: pointer;
  margin-right: 8px;
  transition: all 0.3s ease;
}

.tip-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* 通用 section 样式 */
.features-section,
.quick-access-section,
.partners-section {
  padding: 60px 0;
  background-color: #ffffff;
}

.stats-section,
.news-research-section {
  padding: 60px 0;
  background-color: #f8f9fa;
}

.section-title {
  font-size: 32px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 40px;
  text-align: center;
  position: relative;
  padding-bottom: 16px;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 3px;
  background-color: #3a6ea5;
  border-radius: 2px;
}

/* 功能卡片 */
.feature-card {
  text-align: center;
  padding: 30px 20px;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e9ecef;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  border-color: #3a6ea5;
}

.feature-icon {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60px; /* Fixed height for consistency */
}

.feature-icon i {
  font-size: 48px;
  color: #3a6ea5;
}

.feature-title {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.feature-description {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 24px;
  min-height: 80px;
}

.feature-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* 统计卡片 */
.stats-card {
  background-color: #ffffff;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  text-align: center;
  border: 1px solid #e9ecef;
}

.stats-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
}

.stats-icon {
  font-size: 48px;
  color: #3a6ea5;
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60px;
}

.stats-value {
  font-size: 36px;
  font-weight: 700;
  color: #333;
  margin-bottom: 8px;
}

.stats-label {
  font-size: 14px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 快速访问卡片 */
.quick-link {
  text-decoration: none;
  color: inherit;
  display: block;
}

.quick-link-card {
  padding: 24px;
  border-radius: 12px;
  transition: all 0.3s ease;
  text-align: center;
  border: 1px solid #e9ecef;
  background-color: #ffffff;
}

.quick-link-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
  border-color: #3a6ea5;
}

.feature-icon, .stats-icon, .quick-link-icon {
  font-size: 48px;
  color: #3a6ea5;
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  height: 60px;
}

.quick-link-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.quick-link-description {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

/* 研究与新闻区域 */
.row {
  display: flex;
  flex-wrap: wrap;
  margin: 0 -15px;
}

.col-md-6 {
  flex: 0 0 50%;
  max-width: 50%;
  padding: 0 15px;
}

.research-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e9ecef;
}

.research-card:hover {
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background-color: #f8f9fa;
  border-radius: 12px 12px 0 0;
  font-weight: 600;
  color: #333;
}

.research-content {
  padding: 20px;
}

.research-content p {
  font-size: 14px;
  line-height: 1.6;
  color: #666;
  margin-bottom: 16px;
}

.research-meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #999;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 时间线样式 */
.timeline-content {
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
}

.timeline-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.timeline-content p {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 8px;
}

/* 合作伙伴与引用区域 */
.partners-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  align-items: center;
}

.citation-info {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  background-color: #ffffff;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-left: 4px solid #3a6ea5;
}

.citation-icon {
  font-size: 40px;
  color: #3a6ea5;
  opacity: 0.7;
}

.citation-text p {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  font-style: italic;
  margin-bottom: 16px;
}

.citation-author {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  text-align: right;
}

.partners-logos {
  text-align: center;
}

.partners-logos h3 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 24px;
}

.logos-grid {
  display: flex;
  justify-content: center;
  gap: 40px;
  flex-wrap: wrap;
}

.logo-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
  transition: all 0.3s ease;
  min-width: 150px;
}

.logo-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
}

.logo-item span {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 992px) {
  .partners-content {
    grid-template-columns: 1fr;
    gap: 30px;
  }
  
  .hero-section h1 {
    font-size: 36px;
  }
  
  .hero-subtitle {
    font-size: 20px;
  }
}

@media (max-width: 768px) {
  .col-md-6 {
    flex: 0 0 100%;
    max-width: 100%;
    margin-bottom: 30px;
  }
  
  .hero-section {
    padding: 40px 0;
  }
  
  .hero-section h1 {
    font-size: 28px;
  }
  
  .hero-subtitle {
    font-size: 18px;
  }
  
  .features-section,
  .stats-section,
  .quick-access-section,
  .news-research-section,
  .partners-section {
    padding: 40px 0;
  }
  
  .section-title {
    font-size: 24px;
    margin-bottom: 30px;
  }
  
  .logos-grid {
    gap: 20px;
  }
  
  .logo-item {
    min-width: 120px;
    padding: 15px;
  }
}

@media (max-width: 576px) {
  .search-box-container {
    padding: 15px;
  }
  
  .research-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .citation-info {
    flex-direction: column;
    text-align: center;
  }
  
  .citation-text p {
    text-align: left;
  }
}
</style>