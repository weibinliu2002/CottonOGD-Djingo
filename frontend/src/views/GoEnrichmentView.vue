<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('go_enrichment_analysis') }}</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('go_enrichment_analysis') }}</span>
        </div>
      </template>
      
      <el-form @submit.prevent="handleSubmit" label-width="250px">
        <el-form-item label="Input gene list (one gene per line or space-separated)">
          <el-input
            type="textarea"
            :rows="10"
            v-model="geneList"
            placeholder="Please enter gene list"
          />
          <div class="mt-2">
            <el-button type="info" size="small" @click="fillExample">
              Load example
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="P-value Threshold">
                <el-input
                  type="number"
                  v-model.number="pValue"
                  :min="0.0001"
                  :max="1"
                  :step="0.0001"
                  placeholder="P-value threshold"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Q-value Threshold">
                <el-input
                  type="number"
                  v-model.number="qValue"
                  :min="0.0001"
                  :max="1"
                  :step="0.0001"
                  placeholder="Q-value threshold"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form-item>
        
        <el-form-item label="Results per page">
          <el-select
            v-model="perPage"
            placeholder="Results per page"
            style="width: 120px"
          >
            <el-option value="5" label="5" />
            <el-option value="10" label="10" />
            <el-option value="25" label="25" />
            <el-option value="50" label="50" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" native-type="submit">
            <el-icon><Search /></el-icon>
            Submit Analysis
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
import { ref, getCurrentInstance } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

const router = useRouter()

// 获取全局属性
const app = getCurrentInstance()
const $http = app?.appContext.config.globalProperties.$http

// 表单数据
const geneList = ref('')
const pValue = ref(0.05)
const qValue = ref(0.05)
const perPage = ref(10)
const error = ref('')

// 填充示例数据
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
Kirkii_Juiced.00g000230`
  geneList.value = exampleIDs
}

// 提交表单
const handleSubmit = async () => {
  error.value = ''
  
  // 验证表单
  if (!geneList.value.trim()) {
    error.value = 'Please enter gene list'
    return
  }
  
  try {
    if (!$http) {
      throw new Error('Global axios instance not found')
    }
    
    // 使用全局的axios实例提交数据到正确的API端点
    const response = await $http.post('/tools/go_enrichment/api/start/', {
      gene_list: geneList.value,
      p_value: pValue.value,
      q_value: qValue.value,
      per_page: perPage.value
    })
    
    const data = response.data
    
    if (data.status === 'success') {
      // 使用后端返回的task_id跳转到结果页面
      router.push({
        path: '/tools/go-enrichment/results',
        query: { task_id: data.task_id }
      })
    } else {
      error.value = data.error || 'Submission failed'
    }
  } catch (err: any) {
    error.value = 'Submission failed, please try again'
    console.error('Submission failed:', err)
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
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