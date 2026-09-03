<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧边栏 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>{{ t('phylotree') }}</h3>
          <div class="mt-4">
            <h4 class="sidebar-title">
              <el-icon><VideoPlay /></el-icon> {{ t('select_genome') }}
            </h4>
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
          <div class="mt-4">
            <h4 class="sidebar-title">
              <el-icon><VideoPlay /></el-icon> {{ t('category') }}
            </h4>
            <el-radio-group
              v-model="treeCategory"
              class="mt-2"
              @change="handleCategoryChange"
            >
              <el-radio value="TF">{{ t('tf') }}</el-radio>
              <el-radio value="TR">{{ t('tr') }}</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>

      <!-- 主内容区域 -->
      <div class="col-md-9">
        <div class="main-content">
          <h2>{{ t('transcription_factor_phylotree') }}</h2>
          <PhyloTreeViewer
            v-if="selectedGenomeName"
            :key="treeKey"
            :genome="selectedGenomeName"
            :category="treeCategory"
          />
          <el-empty v-else :description="t('select_genome_first')" />
        </div>
      </div>
    </div>

    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<style scoped>
.container-fluid {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

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
  color: #3a6ea5;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: bold;
  color: #333;
  margin-bottom: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.main-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  min-height: 600px;
}

.main-content h2 {
  font-size: 1.5rem;
  font-weight: bold;
  color: #3a6ea5;
  margin-bottom: 20px;
}

.w-100 {
  width: 100%;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { VideoPlay } from '@element-plus/icons-vue'
import PhyloTreeViewer from '@/components/data-display/PhyloTreeViewer.vue'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'

const { t } = useI18n()

const {
  selectedGenome,
  genomeOptions,
  genomeLoading,
  cascaderProps,
  ensureGenomesLoaded,
  pickDefaultGenome,
  setSelectedGenome
} = useGenomeSelector('G.hirsutumAD1_TM-1_HAU_v1.1.pro')

const selectedGenomeName = computed(() => {
  if (!selectedGenome.value.length) return ''
  return selectedGenome.value[selectedGenome.value.length - 1]
})

const treeCategory = ref<'TF' | 'TR'>('TF')
const treeKey = ref(0)

function handleGenomeChange() {
  treeKey.value++
}

function handleCategoryChange() {
  treeKey.value++
}

onMounted(async () => {
  await ensureGenomesLoaded()
  setSelectedGenome(pickDefaultGenome())
})
</script>