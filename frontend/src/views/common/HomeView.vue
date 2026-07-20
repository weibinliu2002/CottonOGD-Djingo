<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ArrowDown, Setting } from '@element-plus/icons-vue'
import { searchGenes } from '@/utils/meilisearch'

const searchQuery = ref('')
const selectedDatabase = ref('all')
const router = useRouter()
const showAdvancedSearch = ref(false)

// 高级搜索选项
const advancedOptions = reactive({
  genomeId: '',
  geneFamily: '',
  chromosome: '',
  startPosition: null as number | null,
  endPosition: null as number | null,
  exactMatch: false
})

// 数据库选项
const databaseOptions = [
  { label: 'All Databases', value: 'all' },
  { label: 'Gene', value: 'gene' },
  { label: 'Protein', value: 'protein' },
  { label: 'Genome', value: 'genome' },
  { label: 'Orthogroup', value: 'orthogroup' },
  { label: 'Expression', value: 'expression' }
]

// 基因组选项
const genomeOptions = [
  { label: 'All Genomes', value: '' },
  { label: 'G. hirsutum (AD1)', value: 'Ghirsutum' },
  { label: 'G. barbadense (AD2)', value: 'Gbarbadense' },
  { label: 'G. arboreum (A2)', value: 'Garboreum' },
  { label: 'G. raimondii (D5)', value: 'Graimondii' }
]

// 基因家族选项
const geneFamilyOptions = [
  { label: 'All Families', value: '' },
  { label: 'Transcription Factors', value: 'TF' },
  { label: 'Transposable Elements', value: 'TE' },
  { label: 'Kinase', value: 'kinase' },
  { label: 'Transporter', value: 'transporter' }
]

const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    return
  }

  // 构建搜索参数
  const searchParams: any = {
    q: searchQuery.value.trim(),
    database: selectedDatabase.value,
    limit: 20
  }

  // 添加高级搜索参数
  if (showAdvancedSearch.value) {
    if (advancedOptions.genomeId) {
      searchParams.genome_id = advancedOptions.genomeId
    }
    if (advancedOptions.geneFamily) {
      searchParams.gene_family = advancedOptions.geneFamily
    }
    if (advancedOptions.chromosome) {
      searchParams.chromosome = advancedOptions.chromosome
    }
    if (advancedOptions.startPosition !== null) {
      searchParams.start = advancedOptions.startPosition
    }
    if (advancedOptions.endPosition !== null) {
      searchParams.end = advancedOptions.endPosition
    }
    searchParams.exact_match = advancedOptions.exactMatch
  }

  // 如果使用 Meilisearch 搜索基因
  if (selectedDatabase.value === 'all' || selectedDatabase.value === 'gene') {
    try {
      const results = await searchGenes(searchQuery.value.trim(), {
        limit: 20,
        genome_id: advancedOptions.genomeId || undefined
      })
      console.log('results:', results)
          if (results.success && results.total > 0) {
        // 跳转到搜索结果页面
        router.push({
          path: '/tools/id-search/results',
          query: {
            q: searchQuery.value.trim(),
            source: 'meilisearch',
            ...searchParams
          }
        })
        return
      }
    } catch (error) {
      console.error('Meilisearch search failed:', error)
    }
  }

  // 回退到原有的搜索方式
  router.push({
    path: '/tools/id-search/results',
    query: searchParams
  })
}

const fillExample = (example: string) => {
  searchQuery.value = example
}

const toggleAdvancedSearch = () => {
  showAdvancedSearch.value = !showAdvancedSearch.value
}

const clearAdvancedOptions = () => {
  advancedOptions.genomeId = ''
  advancedOptions.geneFamily = ''
  advancedOptions.chromosome = ''
  advancedOptions.startPosition = null
  advancedOptions.endPosition = null
  advancedOptions.exactMatch = false
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
          <p class="hero-description">{{ t('cottonogd_description') }}</p>
         
          
          <!-- 水平布局搜索框 -->
          <div class="search-box-container">
            <!-- 水平排列：数据库选择 + 输入框 + 搜索按钮 -->
            <div class="search-row">
              <el-select
                v-model="selectedDatabase"
                class="database-select"
                size="large"
                placeholder="Select database"
              >
                <el-option
                  v-for="option in databaseOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              
              <el-input
                v-model="searchQuery"
                placeholder="Enter gene ID, symbol, keyword, or sequence"
                clearable
                size="large"
                @keyup.enter="performSearch"
                class="search-input"
              />
              
              <el-button 
                type="primary" 
                size="large" 
                @click="performSearch"
                class="search-btn"
              >
                <el-icon><Search /></el-icon>
                {{ t('search') }}
              </el-button>
            </div>
            
            <!-- 高级搜索按钮 -->
            <div class="advanced-search-toggle">
              <el-button
                type="text"
                size="small"
                @click="toggleAdvancedSearch"
                class="advanced-btn"
              >
                <el-icon><Setting /></el-icon>
                Advanced Search
                <el-icon class="arrow-icon" :class="{ 'is-open': showAdvancedSearch }">
                  <ArrowDown />
                </el-icon>
              </el-button>
            </div>
            
            <!-- 高级搜索面板 - NCBI风格 -->
            <el-collapse-transition>
              <div v-show="showAdvancedSearch" class="advanced-search-panel">
                <el-divider />
                <div class="advanced-options">
                  <!-- 搜索历史/构建器区域 -->
                  <div class="search-builder">
                    <div class="builder-label">Search Builder</div>
                    <div class="builder-content">
                      <div v-if="searchQuery" class="search-term">
                        <span class="term-text">"{{ searchQuery }}"</span>
                        <span class="term-field">[All Fields]</span>
                      </div>
                      <div v-else class="search-term-placeholder">
                        Enter search terms above...
                      </div>
                    </div>
                  </div>

                  <!-- 过滤器网格 -->
                  <div class="filters-grid">
                    <!-- 第一行过滤器 -->
                    <div class="filter-row">
                      <div class="filter-item">
                        <label class="filter-label">Genome</label>
                        <el-select
                          v-model="advancedOptions.genomeId"
                          placeholder="All Genomes"
                          clearable
                          size="default"
                          class="filter-select"
                        >
                          <el-option
                            v-for="option in genomeOptions"
                            :key="option.value"
                            :label="option.label"
                            :value="option.value"
                          />
                        </el-select>
                      </div>
                      
                      <div class="filter-item">
                        <label class="filter-label">Gene Family</label>
                        <el-select
                          v-model="advancedOptions.geneFamily"
                          placeholder="All Families"
                          clearable
                          size="default"
                          class="filter-select"
                        >
                          <el-option
                            v-for="option in geneFamilyOptions"
                            :key="option.value"
                            :label="option.label"
                            :value="option.value"
                          />
                        </el-select>
                      </div>
                      
                      <div class="filter-item">
                        <label class="filter-label">Chromosome</label>
                        <el-input
                          v-model="advancedOptions.chromosome"
                          placeholder="e.g., A01"
                          clearable
                          size="default"
                          class="filter-input"
                        />
                      </div>
                    </div>

                    <!-- 第二行过滤器 - 位置范围 -->
                    <div class="filter-row">
                      <div class="filter-item position-range">
                        <label class="filter-label">Position Range</label>
                        <div class="position-inputs">
                          <el-input-number
                            v-model="advancedOptions.startPosition"
                            :min="0"
                            placeholder="Start"
                            size="default"
                            :controls="false"
                            class="position-input"
                          />
                          <span class="range-separator">to</span>
                          <el-input-number
                            v-model="advancedOptions.endPosition"
                            :min="0"
                            placeholder="End"
                            size="default"
                            :controls="false"
                            class="position-input"
                          />
                        </div>
                      </div>
                      
                      <div class="filter-item">
                        <label class="filter-label">Match Type</label>
                        <el-radio-group v-model="advancedOptions.exactMatch" size="default">
                          <el-radio :label="false">Partial</el-radio>
                          <el-radio :label="true">Exact</el-radio>
                        </el-radio-group>
                      </div>
                    </div>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="advanced-actions">
                    <el-button
                      type="primary"
                      size="default"
                      @click="performSearch"
                      class="action-btn search-action-btn"
                    >
                      <el-icon><Search /></el-icon>
                      Search
                    </el-button>
                    <el-button
                      size="default"
                      @click="clearAdvancedOptions"
                      class="action-btn"
                    >
                      Clear All
                    </el-button>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
            
            <!-- 搜索提示 -->
            <div class="search-tips">
              <span class="tip-label">{{ t('example') }}:</span>
              <el-tag size="small" class="tip-tag" @click="fillExample('Ghir_A01G000100')">Ghir_A01G000100</el-tag>
              <el-tag size="small" class="tip-tag" @click="fillExample('Transcription Factor')">Transcription Factor</el-tag>
              <el-tag size="small" class="tip-tag" @click="fillExample('ABC transporter')">ABC transporter</el-tag>
            </div>
          </div>
        </div>
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
    
    
    
    <!-- 快速访问区域 -->
    <!--<section class="quick-access-section">
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
    </section>-->
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
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
  max-width: 900px;
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

/* 水平布局搜索框 */
.search-box-container {
  max-width: 800px;
  margin: 0 auto;
  background-color: rgba(255, 255, 255, 0.95);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 水平排列的搜索行 */
.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

/* 数据库选择器 */
.database-select {
  width: 160px;
  flex-shrink: 0;
}

.database-select :deep(.el-input__wrapper) {
  background-color: #f5f7fa;
  border-radius: 6px;
}

/* 搜索输入框 */
.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 6px;
}

/* 搜索按钮 */
.search-btn {
  flex-shrink: 0;
  background-color: #3a6ea5;
  border-color: #3a6ea5;
  border-radius: 6px;
  padding: 0 24px;
}

.search-btn:hover {
  background-color: #2c5282;
  border-color: #2c5282;
}

/* 高级搜索按钮 */
.advanced-search-toggle {
  text-align: left;
  margin-bottom: 8px;
}

.advanced-btn {
  color: #3a6ea5;
  font-size: 13px;
}

.advanced-btn:hover {
  color: #2c5282;
}

.arrow-icon {
  margin-left: 4px;
  transition: transform 0.3s ease;
}

.arrow-icon.is-open {
  transform: rotate(180deg);
}

.advanced-search-panel {
  text-align: left;
  margin-top: 16px;
}

.advanced-options {
  padding: 0;
}

/* 搜索构建器 - NCBI风格 */
.search-builder {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.builder-label {
  font-size: 12px;
  font-weight: 600;
  color: #495057;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.builder-content {
  min-height: 24px;
}

.search-term {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.term-text {
  font-weight: 500;
  color: #3a6ea5;
}

.term-field {
  color: #6c757d;
  font-size: 13px;
}

.search-term-placeholder {
  color: #adb5bd;
  font-style: italic;
  font-size: 13px;
}

/* 过滤器网格 */
.filters-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  flex: 1;
  min-width: 160px;
}

.filter-item.position-range {
  flex: 2;
  min-width: 300px;
}

.filter-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #495057;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.filter-select,
.filter-input {
  width: 100%;
}

/* 位置范围输入 */
.position-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.position-input {
  flex: 1;
}

.position-input :deep(.el-input__wrapper) {
  padding-left: 12px;
  padding-right: 12px;
}

.range-separator {
  color: #6c757d;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

/* 操作按钮 */
.advanced-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e9ecef;
}

.action-btn {
  min-width: 100px;
}

.search-action-btn {
  background-color: #3a6ea5;
  border-color: #3a6ea5;
}

.search-action-btn:hover {
  background-color: #2c5282;
  border-color: #2c5282;
}

/* 单选按钮组样式 */
.filter-item :deep(.el-radio-group) {
  display: flex;
  gap: 16px;
  padding-top: 8px;
}

.filter-item :deep(.el-radio) {
  margin-right: 0;
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
  height: 60px;
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
}

.stats-value {
  font-size: 32px;
  font-weight: 700;
  color: #3a6ea5;
  margin-bottom: 8px;
}

.stats-label {
  font-size: 14px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* 快速访问卡片 */
.quick-link {
  text-decoration: none;
  display: block;
}

.quick-link-card {
  text-align: center;
  padding: 24px 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e9ecef;
  height: 100%;
}

.quick-link-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  border-color: #3a6ea5;
}

.quick-link-icon {
  font-size: 40px;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.quick-link-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.quick-link-description {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin: 0;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .hero-section h1 {
    font-size: 32px;
  }
  
  .hero-subtitle {
    font-size: 18px;
  }
  
  /* 移动端垂直布局 */
  .search-row {
    flex-direction: column;
    gap: 12px;
  }
  
  .database-select {
    width: 100%;
  }
  
  .search-btn {
    width: 100%;
  }
  
  .search-box-container {
    padding: 16px;
  }
  
  /* 高级搜索移动端适配 */
  .filter-row {
    flex-direction: column;
    gap: 12px;
  }
  
  .filter-item {
    min-width: 100%;
  }
  
  .filter-item.position-range {
    min-width: 100%;
  }
  
  .position-inputs {
    flex-direction: column;
    align-items: stretch;
  }
  
  .range-separator {
    text-align: center;
    padding: 4px 0;
  }
  
  .advanced-actions {
    flex-direction: column;
  }
  
  .action-btn {
    width: 100%;
  }
}
</style>
