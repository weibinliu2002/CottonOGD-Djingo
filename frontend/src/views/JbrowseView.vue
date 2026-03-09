<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧边栏 - 选择基因组 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>{{ t('jbrowse_views') }} <el-icon class="info-icon"><QuestionFilled /></el-icon></h3>
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><VideoPlay /></el-icon> {{ t('genome') }}</h4>
            <el-cascader
              v-model="selectedGenome"
              :options="genomeOptions"
              :props="cascaderProps"
              :placeholder="t('select_genome')"
              class="w-100 mt-2"
              @change="handleGenomeChange"
              :loading="genomeLoading"
            />
          </div>

          <div class="text-muted">{{ t('please_select_a_genomic') }}</div>

          <div class="mt-4">
            <div class="d-grid gap-2">
              <button @click="refreshIframe" class="btn btn-secondary">
                {{ t('refresh_view') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 主内容区域 - 展示JBrowse -->
      <div class="col-md-9">
        <div class="main-content">
          <h2>{{ t('jbrowse_visualization') }}</h2>
          <div v-if="selectedGenomeInfo" class="genome-info">
            <p><strong>{{ t('genome') }}:</strong> {{ selectedGenomeInfo.name }}</p>
            <p><strong>{{ t('version') }}:</strong> {{ selectedGenomeInfo.assembly }}</p>
          </div>
          <div class="embed-container">
            <iframe :key="iframeKey" :src="currentIframeUrl" width="100%" height="800px" frameborder="0"></iframe>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { QuestionFilled, VideoPlay } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { createDefaultLocus, useGenomeSelector } from '@/composables/useGenomeBrowser'

const { t } = useI18n()
const {
  selectedGenome,
  genomeOptions,
  genomeLoading,
  cascaderProps,
  ensureGenomesLoaded,
  pickDefaultGenome,
  setSelectedGenome,
  extractGenomeName
} = useGenomeSelector()

const currentIframeUrl = ref(
  '/assets/jbrowse/index.html?assembly=Ghirsutum_genome_HAU_v1.0&tracks=Ghirsutum_genome_HAU_v1.0.gff&loc=Ghir_A01:1-1000000'
)
const iframeKey = ref(0)
const selectedGenomeInfo = ref(null)

const refreshIframe = () => {
  iframeKey.value++
}

const buildJbrowseUrl = async (genomeName) => {
  const defaultLocus = await createDefaultLocus(genomeName, '1-1000000', 'Ghir_A01')
  return `/assets/jbrowse/index.html?config=data/${genomeName}/config.json&assembly=${genomeName}&tracks=GFF&loc=${defaultLocus}`
}

const handleGenomeChange = async (value) => {
  const genomeName = extractGenomeName(value)
  if (!genomeName) return

  selectedGenomeInfo.value = {
    name: genomeName,
    assembly: genomeName
  }

  currentIframeUrl.value = await buildJbrowseUrl(genomeName)
  refreshIframe()
}

onMounted(async () => {
  await ensureGenomesLoaded()
  const defaultGenome = pickDefaultGenome()
  if (!defaultGenome) return

  setSelectedGenome(defaultGenome)
  await handleGenomeChange([defaultGenome])
})
</script>

<style scoped>
.container-fluid {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

/* 左侧边栏样式 */
.sidebar {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  height: fit-content;
}

.sidebar h3 {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.info-icon {
  font-size: 1rem;
  margin-left: 5px;
  color: #409eff;
  cursor: pointer;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: bold;
  color: #333;
  margin-bottom: 0;
}

.play-icon {
  font-size: 0.8rem;
  margin-right: 5px;
  color: #e6a23c;
}

/* 基因组信息样式 */
.genome-info {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
  font-size: 0.9rem;
}

/* 主内容区域样式 */
.main-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.main-content h2 {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}

/* 嵌入容器样式 */
.embed-container {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container-fluid {
    padding: 10px;
  }

  .sidebar,
  .main-content {
    padding: 15px;
    margin-bottom: 20px;
  }
}
</style>
