<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGenomeStore } from '../stores/genome_info'
import { Download, RefreshLeft, Folder, Files, Loading } from '@element-plus/icons-vue'
import axios from '../utils/http'

const { t } = useI18n()

const genomeStore = useGenomeStore()
const isLoading = ref(false)
const errorMessage = ref('')
const selectedCategory = ref('')

// 下载类型定义
const downloadTypes = [
  { value: 'genome', label: 'Genome', icon: 'File' },
  { value: 'cds', label: 'CDS', icon: 'File' },
  { value: 'protein', label: 'Protein', icon: 'File' },
  { value: 'upstream2000', label: 'Upstream 2000', icon: 'File' },
  { value: 'gff3', label: 'GFF3', icon: 'File' }
]

// Type映射定义（用户可自行填写映射内容）
const typeMapping: Record<string, string> = {
  // 示例：'genome': '基因组',
  // 请根据需要添加映射内容
  'genome': '.genome.fa.gz',
  'cds': '.cds.fa.gz',
  'protein': '.pro.fa.gz',
  'upstream2000': '.upstream.fa.gz',
  'gff3': '.gff.gz'
}

// 计算属性：按基因组类型分组的数据
const groupedGenomes = computed(() => {
  return genomeStore.genomeOptions
})

// 计算属性：获取所有分类
const categories = computed(() => {
  return groupedGenomes.value.map(group => ({
    value: group.value,
    label: group.label
  }))
})

// 初始化数据
onMounted(async () => {
  if (genomeStore.genomeOptions.length === 0) {
    await loadGenomes()
  }
})

// 加载基因组数据
const loadGenomes = async () => {
  isLoading.value = true
  try {
    await genomeStore.fetchGenomes()
  } catch (error: any) {
    errorMessage.value = error.message || 'Failed to load genome data'
  } finally {
    isLoading.value = false
  }
}

// 下载文件
const downloadFile = async (genomeId: string, type: string) => {
  try {
    // 使用type映射获取文件扩展名
    const fileExtension = typeMapping[type] || type
    
    // 构建文件路径（根据实际文件路径格式）
    const fileUrl = `/data/genome/${genomeId}/${genomeId}${fileExtension}`
    console.log('Download URL:', fileUrl)
    
    // 创建下载链接
    const link = document.createElement('a')
    link.href = fileUrl
    link.download = `${genomeId}${fileExtension}`
    link.click()
  } catch (error: any) {
    errorMessage.value = `Download failed: ${error.message || 'Unknown error'}`
  }
}

// Expanded Items
const activeNames = ref<string[]>([])
</script>

<template>
  <div class="download-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="container">
        <h1 class="page-title">{{ t('download_data') }}</h1>
        <p class="page-subtitle">{{ t('download_genome_files') }}</p>
      </div>
    </div>
    
    <!-- 主要内容 -->
    <div class="container">
      <!-- 操作栏 -->
      <div class="action-bar mb-6">
        <el-row :gutter="20" align="middle">
          <el-col :span="8">
            <el-select
              v-model="selectedCategory"
              :placeholder="t('select_genome_category')"
              clearable
              class="w-full"
            >
              <el-option
                v-for="category in categories"
                :key="category.value"
                :label="category.label"
                :value="category.value"
              />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button
              type="primary"
              @click="loadGenomes"
              :loading="isLoading"
              class="w-full"
            >
              <el-icon><RefreshLeft /></el-icon>
              {{ t('refresh_data') }}
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 错误信息 -->
      <el-alert
        v-if="errorMessage"
        type="error"
        :title="errorMessage"
        show-icon
        class="mb-6"
        closable
        @close="errorMessage = ''"
      />
      
      <!-- 加载状态 -->
      <div v-if="isLoading" class="mb-6">
        <el-skeleton :rows="10" animated />
      </div>
      
      <!-- No Data Alert -->
      <el-alert
        v-else-if="groupedGenomes.length === 0"
        type="warning"
        :title="t('no_genome_data_available')"
        show-icon
        class="mb-6"
      />
      
      <!-- Genome Data Display -->
      <div v-else class="genome-cards">
        <el-collapse v-model="activeNames" class="collapse-container">
          <el-collapse-item
            v-for="genomeGroup in groupedGenomes"
            :key="genomeGroup.value"
            :name="genomeGroup.value"
            class="genome-collapse-item"
          >
            <template #title>
              <div class="card-header">
                <el-icon class="mr-2"><Folder /></el-icon>
                <span class="category-name">{{ genomeGroup.label }}</span>
                <el-tag type="info" size="small" class="ml-2">{{ genomeGroup.children?.length || 0 }} {{ t('genome') }}</el-tag>
              </div>
            </template>
            
            <div class="genome-list">
              <el-card
                v-for="genome in genomeGroup.children"
                :key="genome.value"
                shadow="hover"
                class="genome-item mb-4"
              >
                <div class="genome-info">
                  <h4 class="genome-name">{{ genome.label }}</h4>
                  <p class="genome-id">ID: {{ genome.value }}</p>
                </div>
                
                <div class="download-options">
                  <el-divider content-position="center">{{ t('download_options') }}</el-divider>
                  <el-row :gutter="15" class="download-buttons">
                    <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="type in downloadTypes" :key="type.value">
                      <el-button
                        type="primary"
                        @click="downloadFile(genome.value, type.value)"
                        class="download-btn w-full"
                        :class="`btn-${type.value}`"
                      >
                        <el-icon><Download /></el-icon>
                        {{ type.label }}
                      </el-button>
                    </el-col>
                  </el-row>
                </div>
              </el-card>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<style scoped>
.download-page {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.page-header {
  text-align: left;
  margin-bottom: 30px;
  padding-top: 20px;
}

.page-title {
  font-size: 36px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.page-subtitle {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  max-width: 800px;
  margin: 0;
}

.action-bar {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
}

.collapse-container {
  border-radius: 10px;
  overflow: hidden;
}

.genome-collapse-item {
  margin-bottom: 10px;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
}

.genome-collapse-item .el-collapse-item__header {
  border-radius: 10px;
  background-color: white;
  font-size: 1.1rem;
  font-weight: 500;
  padding: 16px 20px;
  transition: all 0.3s ease;
}

.genome-collapse-item .el-collapse-item__header:hover {
  background-color: #f8f9fa;
}

.genome-collapse-item .el-collapse-item__content {
  padding: 20px;
  background-color: white;
  border-top: 1px solid #ebeef5;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 1.1rem;
  font-weight: 500;
  color: #333;
}

.category-name {
  font-weight: 600;
}

.genome-item {
  border-radius: 8px;
}

.genome-info {
  margin-bottom: 20px;
}

.genome-name {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 5px;
  color: #333;
}

.genome-id {
  font-size: 0.9rem;
  color: #666;
  margin: 0;
}

.download-options {
  margin-top: 20px;
}

.download-buttons {
  margin-top: 20px;
}

.download-btn {
  transition: all 0.3s ease;
  border-radius: 6px;
}

.download-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 110, 245, 0.3);
}

.btn-genome {
  background-color: #4c6ef5;
  border-color: #4c6ef5;
}

.btn-cds {
  background-color: #20c997;
  border-color: #20c997;
}

.btn-protein {
  background-color: #fa5252;
  border-color: #fa5252;
}

.btn-upstream2000 {
  background-color: #ff922b;
  border-color: #ff922b;
}

.btn-gff3 {
  background-color: #9775fa;
  border-color: #9775fa;
}

@media (max-width: 768px) {
  .page-title {
    font-size: 2rem;
  }
  
  .genome-card {
    margin-bottom: 30px;
  }
}
</style>