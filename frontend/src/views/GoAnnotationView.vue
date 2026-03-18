<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('go_annotation') }}</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('go_annotation_analysis') }}</span>
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
              Load Example
            </el-button>
          </div>
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
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" target=".container" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'

const router = useRouter()
const { t } = useI18n()

const geneList = ref('')
const perPage = ref(20)
const error = ref('')
const isLoading = ref(false)

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
Kirkii_Juiced.00g000100`
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
    // 处理基因列表，将换行符替换为空格，确保URL参数正确传递
    const processedGeneList = geneList.value.trim().replace(/\n/g, ' ').replace(/\s+/g, ' ')
    
    // 直接跳转到结果页面，并传递参数
    router.push({
      path: '/tools/go-annotation/results',
      query: {
        gene_id: processedGeneList,
        per_page: perPage.value
      }
    })
  } catch (err) {
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