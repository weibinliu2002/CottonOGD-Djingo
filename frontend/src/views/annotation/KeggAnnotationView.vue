<template>
  <div class="container mt-4">
    <h2>{{ t('kegg_annotation') }} {{ t('search') }}</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('kegg_annotation') }} {{ t('search') }}</span>
        </div>
      </template>
      
      <el-form @submit.prevent="submitForm" label-width="250px">
        <el-form-item label="Enter Gene IDs (one per line or space/comma separated)">
          <el-input
            type="textarea"
            :rows="5"
            v-model="geneIds"
            placeholder="please_enter gene IDs"
            :disabled="isLoading"
          />
          <div class="mt-2">
            <el-button 
              type="info" 
              size="small" 
              @click="fillExample"
              :disabled="isLoading"
            >
              {{ t('load_example') }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item :label="t('select_genome')">
          <el-select
            v-model="selectedGenome"
            :placeholder="t('select_genome')"
            style="width: 100%"
            :loading="genomeLoading"
            filterable
          >
            <el-option
              v-for="genome in genomeOptions"
              :key="genome.value"
              :label="genome.label"
              :value="genome.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <div class="d-flex justify-content-end">
            <el-button 
              type="primary" 
              native-type="submit"
              :loading="isLoading"
            >
              {{ t('search') }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from '@/utils/http.js'
import { ElMessage } from 'element-plus'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { useEnrichmentStore } from '@/stores/modules/enrichment'

const geneIds = ref('')
const isLoading = ref(false)
const router = useRouter()
const route = useRoute()

// 基因组选择
const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome, allGenomes } = useGenomeSelector()
const selectedGenome = ref('')

onMounted(async () => {
  await ensureGenomesLoaded()
  const queryGenome = typeof route.query.genome === 'string' ? route.query.genome : ''
  const defaultGenome = queryGenome && allGenomes.value.includes(queryGenome)
    ? queryGenome
    : pickDefaultGenome()
  if (defaultGenome) {
    selectedGenome.value = defaultGenome
  }
})

const fillExample = () => {
  const exampleIDs = `Ghir_A01G000040.1
Ghir_A01G000060
Ghir_A01G000290.1
Ghir_A01G000120.2`;
  geneIds.value = exampleIDs;
}

const submitForm = async () => {
  if (!geneIds.value.trim()) {
    ElMessage.error(t('please_enter') + ' gene IDs');
    return;
  }

  if (!selectedGenome.value) {
    ElMessage.error(t('please_select_genome'));
    return;
  }

  isLoading.value = true
  try {
    // 使用 Pinia store 存储基因组信息
    const enrichmentStore = useEnrichmentStore()
    enrichmentStore.selectedGenome = selectedGenome.value
    
    // 直接跳转到结果页面，并传递参数
    router.push({
      path: '/tools/kegg-annotation/results',
      query: {
        gene_id: geneIds.value
      }
    })
  } catch (error: any) {
    console.error(t('error') + ' submitting form:', error)
    ElMessage.error(t('error') + ' submitting form: ' + (error.message || 'Unknown error'));
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.container {
  max-width: 900px;
  margin: 0 auto;
}

.mt-4 {
  margin-top: 1.5rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.mt-2 {
  margin-top: 0.5rem;
}

.d-flex {
  display: flex;
}

.justify-content-end {
  justify-content: flex-end;
}

.card-header {
  font-size: 16px;
  font-weight: 500;
}
</style>