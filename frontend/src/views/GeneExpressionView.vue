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
            <!-- 直接显示所有选项，包括大类和单个基因组 -->
            <template v-for="group in genomeStore.genomeOptions" :key="group.value">
              <!-- 基因组大类作为可选择选项 -->
              <el-option
                :label="group.label"
                :value="group.value"
              />
              <!-- 单个基因组选项，添加缩进样式 -->
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
          >
            <el-option value="" :label="t('all_tissues')" />
            <!-- Top tissues -->
            <el-option value="Root" label="Root" />
            <el-option value="Stem" label="Stem" />
            <el-option value="Cotyledon" label="Cotyledon" />
            <el-option value="Leaf" label="Leaf" />
            <el-option value="Pholem" label="Pholem" />
            <el-option value="Sepal" label="Sepal" />
            <el-option value="Bract" label="Bract" />
            <el-option value="Petal" label="Petal" />
            <el-option value="Anther" label="Anther" />
            <el-option value="Stigma" label="Stigma" />
            <!-- Bottom left tissues -->
            <el-option value="0_DPA_ovules" label="0_DPA_ovules" />
            <el-option value="3_DPA_fibers" label="3_DPA_fibers" />
            <el-option value="6_DPA_fibers" label="6_DPA_fibers" />
            <el-option value="9_DPA_fibers" label="9_DPA_fibers" />
            <el-option value="12_DPA_fibers" label="12_DPA_fibers" />
            <el-option value="15_DPA_fibers" label="15_DPA_fibers" />
            <el-option value="18_DPA_fibers" label="18_DPA_fibers" />
            <el-option value="21_DPA_fibers" label="21_DPA_fibers" />
            <el-option value="24_DPA_fibers" label="24_DPA_fibers" />
            <!-- Bottom right tissues -->
            <el-option value="DPA0" label="DPA0" />
            <el-option value="5_DPA_ovules" label="5_DPA_ovules" />
            <el-option value="10_DPA_ovules" label="10_DPA_ovules" />
            <el-option value="20_DPA_ovules" label="20_DPA_ovules" />
            <el-option value="Seed" label="Seed" />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import httpInstance from '../utils/http'
import { Search } from '@element-plus/icons-vue'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import { useGeneExpressionStore } from '@/stores/geneExpressionStore'

const { t } = useI18n()

const router = useRouter()
const { genomeStore, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector('G.hirsutumAD1_Jin668_HAU_v1T2T')
const geneExpressionStore = useGeneExpressionStore()

// 表单数据
const geneList = ref('')
const selectedTissue = ref('')
const selectedGenome = ref('')
const error = ref('')

// 组件挂载时加载基因组数据
onMounted(async () => {
  await ensureGenomesLoaded()
  selectedGenome.value = pickDefaultGenome()
})

// 填充示例数据
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

// 提交表单
const handleSubmit = async () => {
  error.value = ''
  
  // 验证表单
  if (!geneList.value.trim()) {
    error.value = t('please_enter_gene_list')
    return
  }
  
  try {
    // 构建查询参数
    const params = {
      gene_id: geneList.value,
      tissue: selectedTissue.value,
      genome_id: selectedGenome.value,
    }
    console.log('params:', params)
    
    // 存储查询参数到 store
    geneExpressionStore.setQueryParams({
      geneList: geneList.value,
      tissue: selectedTissue.value,
      genome: selectedGenome.value
    })
    
    // 设置加载状态
    geneExpressionStore.setLoading(true)
    geneExpressionStore.setError(null)
    
    // 直接调用后端API获取数据
    const response = await httpInstance.post('/CottonOGD_api/extract_expression/', params)
    console.log('Gene expression response:', response)
    
    // 处理响应数据
    if (response) {
      // 添加类型断言，告诉 TypeScript 响应是任意类型
      const data = response as any
      
      // 检查响应是否包含 expression 属性
      if (data.expression) {
        // 存储结果到 store
        geneExpressionStore.setResults(data.expression)
        
        // 检查并存储热图图像
        if (data.heatmap_image) {
          geneExpressionStore.setHeatmapImage(data.heatmap_image)
        }
        
        // 跳转到结果页面
        router.push({
          path: '/tools/gene-expression/results'
        })
      } else {
        // 如果响应不包含 expression 属性，尝试直接使用响应
        geneExpressionStore.setResults(Array.isArray(data) ? data : [data])
        
        // 检查并存储热图图像
        if (data.heatmap_image) {
          geneExpressionStore.setHeatmapImage(data.heatmap_image)
        }
        
        // 跳转到结果页面
        router.push({
          path: '/tools/gene-expression/results'
        })
      }
    } else {
      error.value = t('invalid_response_from_server')
      console.error('Invalid response:', response)
      geneExpressionStore.setError(t('invalid_response_from_server'))
    }
  } catch (err: any) {
    error.value = t('submission_failed_please_try_again')
    console.error('Submission failed:', err)
    geneExpressionStore.setError(t('submission_failed_please_try_again'))
  } finally {
    geneExpressionStore.setLoading(false)
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
