<template>
  <div class="container mt-4">
    <h2>{{ t('kegg_pathway_enrichment_analysis') }}</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('kegg_pathway_enrichment_analysis') }}</span>
        </div>
      </template>
      
      <el-form @submit.prevent="submitForm" label-width="250px">
        <el-form-item :label="t('input_gene_ids_one_per_line_or_separated_by_spaces_commas')">
          <el-input
            type="textarea"
            :rows="10"
            v-model="geneList"
            :placeholder="t('please_enter_gene_ids_here')"
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
        
        <el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="t('p_value_threshold')">
                <el-input
                  type="number"
                  v-model.number="pValueThreshold"
                  :min="0"
                  :max="1"
                  :step="0.001"
                  :placeholder="t('p_value_threshold')"
                  :disabled="isLoading"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('q_value_threshold')">
                <el-input
                  type="number"
                  v-model.number="qValueThreshold"
                  :min="0"
                  :max="1"
                  :step="0.001"
                  :placeholder="t('q_value_threshold')"
                  :disabled="isLoading"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form-item>
        
        <el-form-item>
          <div class="d-flex justify-content-end">
            <el-button 
              type="primary" 
              native-type="submit"
              :loading="isLoading"
            >
              {{ t('submit') }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import axios from '@/utils/http'
import { ElMessage } from 'element-plus'

const { t } = useI18n()
const geneList = ref('')
const pValueThreshold = ref(0.05)
const qValueThreshold = ref(0.05)
const isLoading = ref(false)
const router = useRouter()

const fillExample = () => {
  const exampleIDs = `Kirkii_Juiced.00g000010
Kirkii_Juiced.00g000020
Kirkii_Juiced.00g000030
Kirkii_Juiced.00g000040
Kirkii_Juiced.00g000050
Kirkii_Juiced.00g000060
Kirkii_Juiced.00g000070
Kirkii_Juiced.00g000080
Kirkii_Juiced.00g000090
Kirkii_Juiced.00g000100
Kirkii_Juiced.00g000110
Kirkii_Juiced.00g000120
Kirkii_Juiced.00g000130
Kirkii_Juiced.00g000140
Kirkii_Juiced.00g000150
Kirkii_Juiced.00g000160
Kirkii_Juiced.00g000170
Kirkii_Juiced.00g000180
Kirkii_Juiced.00g000190
Kirkii_Juiced.00g000200
Kirkii_Juiced.00g000210
Kirkii_Juiced.00g000220
Kirkii_Juiced.00g000230
Kirkii_Juiced.00g000240
Kirkii_Juiced.00g000250
Kirkii_Juiced.00g000260
Kirkii_Juiced.00g000270
Kirkii_Juiced.00g000280
Kirkii_Juiced.00g000290
Kirkii_Juiced.00g000300`;
  geneList.value = exampleIDs;
}

const submitForm = async () => {
  if (!geneList.value.trim()) {
    ElMessage.error(t('please_enter_gene_ids'));
    return;
  }

  if (pValueThreshold.value < 0 || pValueThreshold.value > 1) {
    ElMessage.error(t('p_value_threshold_must_be_between_0_and_1'));
    return;
  }

  if (qValueThreshold.value < 0 || qValueThreshold.value > 1) {
    ElMessage.error(t('q_value_threshold_must_be_between_0_and_1'));
    return;
  }

  isLoading.value = true
  try {
    // 直接跳转到结果页面，并传递参数
    router.push({
      path: '/tools/kegg-enrichment/results',
      query: {
        gene_id: geneList.value,
        p_value_threshold: pValueThreshold.value
      }
    })
  } catch (error: any) {
    ElMessage.error(t('error') + ': ' + (error.message || 'Unknown error'));
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