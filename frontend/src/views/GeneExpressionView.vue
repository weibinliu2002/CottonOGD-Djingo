<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('gene_expression_analysis') }}</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('gene_expression_analysis') }}</span>
        </div>
      </template>
      
      <el-form @submit.prevent="handleSubmit" label-width="300px">
        <el-form-item :label="t('enter_gene_list')">
          <el-input
            type="textarea"
            :rows="10"
            v-model="geneList"
            :placeholder="t('please_enter_gene_list')"
          />
          <div class="mt-2">
            <el-button type="info" size="small" @click="fillExample">
              {{ t('load_example') }}
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item :label="t('select_genome')">
          <el-select
            v-model="selectedGenome"
            :placeholder="t('select_genome_placeholder')"
            style="width: 100%"
            :loading="genomeStore.loading"
          >
            <el-option value="" :label="t('all_genomes')" />
            <!-- 鐩存帴鏄剧ず鎵€鏈夐€夐」锛屽寘鎷ぇ绫诲拰鍗曚釜鍩哄洜缁?-->
            <template v-for="group in genomeStore.genomeOptions" :key="group.value">
              <!-- 鍩哄洜缁勫ぇ绫讳綔涓哄彲閫夋嫨閫夐」 -->
              <el-option
                :label="group.label"
                :value="group.value"
              />
              <!-- 鍗曚釜鍩哄洜缁勯€夐」锛屾坊鍔犵缉杩涙牱寮?-->
              <el-option
                v-for="item in group.children"
                :key="item.value"
                :label="`  ${item.label}`"
                :value="item.value"
              />
            </template>
          </el-select>
        </el-form-item>
        
        <el-form-item :label="t('select_tissue')">
          <el-select
            v-model="selectedTissue"
            :placeholder="t('select_tissue_placeholder')"
            style="width: 100%"
            :loading="loadingTissues"
            multiple
            filterable
            allow-create
            default-first-option
          >
            <el-option value="" :label="t('all_tissues')" />
            <el-option
              v-for="tissue in tissueOptions"
              :key="tissue"
              :value="tissue"
              :label="tissue"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" native-type="submit">
            <el-icon><Search /></el-icon>
            {{ t('submit_analysis') }}
          </el-button>
        </el-form-item>
        
        <el-form-item>
          <el-alert
            v-if="error"
            type="error"
            :title="error"
            show-icon
          />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import httpInstance from '../utils/http'
import { Search } from '@element-plus/icons-vue'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import { useGeneExpressionStore } from '@/stores/geneExpressionStore'

const { t } = useI18n()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

const router = useRouter()
const { genomeStore, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector('G.hirsutumAD1_Jin668_HAU_v1T2T')
const geneExpressionStore = useGeneExpressionStore()

// 琛ㄥ崟鏁版嵁
const geneList = ref('')
const selectedTissue = ref<string[]>([])
const selectedGenome = ref('')
const error = ref('')
const tissueOptions = ref<string[]>([])
const loadingTissues = ref(false)

// 从后端获取tissue列表
const fetchTissues = async (genomeId?: string) => {
  try {
    loadingTissues.value = true
    const params = genomeId ? { genome_id: genomeId } : {}
    console.log('params:', params)
    const response = await httpInstance.get('/CottonOGD_api/extract_expression/tissues/', { params })
    if (response && Array.isArray(response)) {
      tissueOptions.value = response
    }
  } catch (err) {
    console.error('Failed to fetch tissues:', err)
  } finally {
    loadingTissues.value = false
  }
}

// 缁勪欢鎸傝浇鏃跺姞杞藉熀鍥犵粍鏁版嵁
onMounted(async () => {
  await ensureGenomesLoaded()
  selectedGenome.value = pickDefaultGenome()
  await fetchTissues(selectedGenome.value)
})

// 监听基因组选择变化，重新获取tissue数据
watch(selectedGenome, async (newGenome) => {
  await fetchTissues(newGenome)
})

// 濉厖绀轰緥鏁版嵁
const fillExample = () => {
  const exampleIDs = `Ghjin_A01g000110
Ghjin_A01g000120
Ghjin_A01g000130
Ghjin_A01g000140
Ghjin_A01g000150
Ghjin_A01g000160
Ghjin_A01g000170
Ghjin_A01g000180
Ghjin_A01g000190
`
  geneList.value = exampleIDs
}

// Submit form.
const handleSubmit = async () => {
  showLoading?.()
  error.value = ''

  if (!geneList.value.trim()) {
    error.value = t('please_enter_gene_list')
    return
  }

  try {
    // 处理多选的tissue值
    const tissueValue = selectedTissue.value.length > 0 ? selectedTissue.value.join(',') : ''
    
    const params = {
      gene_id: geneList.value,
      tissue: tissueValue,
      genome_id: selectedGenome.value
    }
    console.log('params:', params)

    geneExpressionStore.setQueryParams({
      geneList: geneList.value,
      tissue: tissueValue,
      genome: selectedGenome.value
    })

    geneExpressionStore.setLoading(true)
    geneExpressionStore.setError(null)

    const response = await httpInstance.post('/CottonOGD_api/extract_expression/', params)
    console.log('Gene expression response:', response)

    if (!response) {
      error.value = t('invalid_response_from_server')
      geneExpressionStore.setError(t('invalid_response_from_server'))
      return
    }

    const data = response as any
    if (data.expression) {
      // Save full payload so results page can read expression/tissues/clustergrammer_data.
      geneExpressionStore.setResults(data)
    } else {
      // Backward compatibility with old array-style response.
      geneExpressionStore.setResults(Array.isArray(data) ? data : [data])
    }

    if (data.heatmap_image) {
      geneExpressionStore.setHeatmapImage(data.heatmap_image)
    }

    router.push({
      path: '/tools/gene-expression/results'
    })
  } catch (err: any) {
    error.value = t('submission_failed_please_try_again')
    console.error('Submission failed:', err)
    geneExpressionStore.setError(t('submission_failed_please_try_again'))
  } finally {
    geneExpressionStore.setLoading(false)
    hideLoading?.()
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.page-header {
  text-align: left;
  margin-bottom: 30px;
}

.page-title {
  font-size: 36px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.page-description {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  max-width: 800px;
  margin: 0;
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

.card-header {
  font-size: 16px;
  font-weight: 500;
}
</style>

