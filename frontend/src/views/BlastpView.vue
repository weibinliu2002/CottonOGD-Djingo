<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { onMounted, computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Delete, Search } from '@element-plus/icons-vue'
import { useGenomeStore } from '@/stores/genome_info'
import { useBlastStore } from '@/stores/blastStore'

// 使用Pinia store
const genomeStore = useGenomeStore()
const blastStore = useBlastStore()

// 文件上传相关
const fileName = ref('')

// 从blastStore中获取状态和action
// 使用storeToRefs来确保解构出的属性保持响应性
const {
  sequence,
  evalue,
  maxTargetSeqs,
  selectedBlastType,
  selectedDatabaseType,
  selectedGenomes,
  error,
  loading,
  blastTypes,
  databaseTypes,
  wordSize,
  matchScore,
  gapOpen,
  gapExtend,
  lowComplexityFilter,
  showAdvancedParams,
} = storeToRefs(blastStore)

const { submitBlast, resetForm, setDefaultGenomes, fillExample } = blastStore

// 获取当前选中blast类型的介绍
const currentBlastDescription = computed(() => {
  const currentType = blastTypes.value.find(type => type.value === selectedBlastType.value)
  return currentType ? currentType.description : ''
})

// 文件上传处理函数
const handleFileChange = (file: any) => {
  const selectedFile = file.raw
  if (selectedFile) {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        if (content) {
          sequence.value = content.trim()
          fileName.value = selectedFile.name
          ElMessage.success('File loaded successfully')
        }
      } catch (err: any) {
        ElMessage.error('Failed to read file: ' + err.message)
      }
    }
    reader.onerror = () => {
      ElMessage.error('Failed to read file')
    }
    reader.readAsText(selectedFile)
  }
}

onMounted(() => {
  // 加载基因组数据并设置默认值
  if (genomeStore.genomeOptions.length === 0) {
    genomeStore.fetchGenomes().then(() => {
      setDefaultGenomes(genomeStore.genomeOptions)
    })
  } else {
    setDefaultGenomes(genomeStore.genomeOptions)
  }
})
</script>

<template>
  <div class="blastp-view">
    <!-- 页面标题和简介 -->
    <div class="page-header">
      <h1>{{ t('blast_search') }}</h1>
      <p class="page-description">
        {{ t('blast_description') }} using BLAST algorithms.
        Choose from different BLAST types and customize your search parameters.
      </p>
    </div>
    
    <!-- 错误提示 -->
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      show-icon
      class="error-alert"
    />
    
    <!-- 主要内容卡片 -->
    <el-card class="main-card">
      <!-- Blast类型选择 -->
      <el-tabs v-model="selectedBlastType" class="blast-type-tabs">
        <el-tab-pane
          v-for="type in blastTypes"
          :key="type.value"
          :label="type.label"
          :name="type.value"
        />
      </el-tabs>
      
      <!-- Blast类型介绍 -->
      <el-card type="info" shadow="never" class="blast-info-card">
        <div class="blast-info-content">
          <h3 class="info-title">{{ blastTypes.find(type => type.value === selectedBlastType)?.label }} {{ t('description') }}</h3>
          <p>{{ currentBlastDescription }}</p>
        </div>
      </el-card>
      
      <!-- BLAST表单 -->
      <el-form label-width="180px" class="blast-form">
        <!-- 提交按钮（顶部固定） -->
        <div class="form-header-actions">
          <el-button 
            type="primary" 
            native-type="button" 
            size="large" 
            class="submit-button"
            :loading="loading"
            :disabled="loading"
            @click="submitBlast"
          >
            <el-icon><Search /></el-icon>
            Run {{ t('blast_search') }}
          </el-button>
          <el-button type="default" @click="resetForm" size="large" class="reset-button">
            <el-icon><Refresh /></el-icon>
            {{ t('reset') }} Form
          </el-button>
        </div>
        
        <div class="form-layout">
          <!-- 序列输入区域 -->
          <div class="form-section">
            <h3 class="section-title">{{ t('sequence') }} Input</h3>
            
            <!-- 序列输入 -->
            <el-form-item :label="t('query_sequence')">
              <el-input
                type="textarea"
                :rows="10"
                v-model="sequence"
                :placeholder="selectedBlastType === 'blastp' || selectedBlastType === 'blastx' ? t('please_enter') + ' a protein sequence in FASTA or plain text format' : t('please_enter') + ' a nucleotide sequence in FASTA or plain text format'"
                class="sequence-textarea"
              />
              <div class="form-actions mt-2">
                <el-button type="info" size="small" @click="fillExample">
                  <el-icon><DocumentCopy /></el-icon>
                  {{ t('load_example_sequence') }}
                </el-button>
                <el-upload
                  action="#"
                  :auto-upload="false"
                  :on-change="handleFileChange"
                  :show-file-list="false"
                  accept=".fasta,.fa,.txt"
                  class="upload-inline"
                >
                  <template #default>
                    <el-button type="success" size="small">
                      <el-icon><Upload /></el-icon>
                     {{ t('upload_file') }}
                    </el-button>
                  </template>
                </el-upload>
                <el-button type="warning" size="small" @click="sequence = ''">
                  <el-icon><Delete /></el-icon>
                  {{ t('clear') }} {{ t('sequence') }}
                </el-button>
              </div>
              <div class="help-text mt-2">
                <i class="fas fa-info-circle"></i>
                <span>{{ t('enter_your_sequence_in_fasta_or_plain_text_format') }}</span>
              </div>
            </el-form-item>
          </div>
          
          <!-- 搜索参数区域 -->
          <div class="form-section">
            <h3 class="section-title">{{ t('search') }} Parameters</h3>
            
            <!-- 基因组选择 -->
            <el-form-item :label="t('select_genomes')">
              <el-select
                v-model="selectedGenomes"
                filterable
                allow-create
                default-first-option
                :placeholder="t('select_genome_or_genome_category')"
                :loading="genomeStore.loading"
                class="w-full genome-select"
              >
                <!-- 直接显示所有选项，包括大类和单个基因组 -->
                <template v-for="group in genomeStore.genomeOptions" :key="group.value">
                  <!-- 基因组大类作为可选择选项 -->
                  <el-option
                    :label="group.label"
                    :value="group.value"
                    class="category-option"
                  />
                  <!-- 单个基因组选项，添加缩进样式 -->
                  <el-option
                    v-for="item in group.children"
                    :key="item.value"
                    :label="`  ${item.label}`"
                    :value="item.value"
                    class="genome-option"
                  />
                </template>
              </el-select>
              <div class="help-text mt-2">
                <i class="fas fa-info-circle"></i>
                <span>{{ t('select_one_or_more_genomes_to_search_against') }}</span>
              </div>
            </el-form-item>
            
            <!-- 数据库类型选择 -->
            <el-form-item :label="t('database_type')">
              <el-select
                v-model="selectedDatabaseType"
                :placeholder="t('select_database_type')"
                class="w-full"
              >
                <el-option
                  v-for="type in databaseTypes[selectedBlastType]"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
              <div class="help-text mt-2">
                <i class="fas fa-info-circle"></i>
                <span>{{ t('choose_the_type_of_sequence_database_to_search_against') }}</span>
              </div>
            </el-form-item>
            
            <!-- 参数设置 -->
            <div class="parameter-grid">
              <!-- {{ t('e_value') }}阈值 -->
              <el-form-item :label="t('e_value') + ' Threshold'">
                <el-input
                  type="number"
                  v-model.number="evalue"
                  :step="0.01"
                  :min="0"
                  :placeholder="t('e_value')"
                  class="w-full"
                />
                <div class="help-text mt-1">
                  <i class="fas fa-info-circle"></i>
                  <span>{{ t('the_expectation_value_threshold_for_saving_hits') }}</span>
                </div>
              </el-form-item>
              
              <!-- 最大目标序列数 -->
              <el-form-item :label="t('max_target_sequences')">
                <el-input
                  type="number"
                  v-model.number="maxTargetSeqs"
                  :min="1"
                  :max="50"
                  :placeholder="t('max_sequences')"
                  class="w-full"
                />
                <div class="help-text mt-1">
                  <i class="fas fa-info-circle"></i>
                  <span>{{ t('maximum_number_of_aligned_sequences_to_keep') }}</span>
                </div>
              </el-form-item>
            </div>
          </div>
        </div>

        <!-- 高级参数区域 -->
        <div class="advanced-params-section">
          <el-button 
            type="primary" 
            text 
            @click="showAdvancedParams = !showAdvancedParams"
            class="advanced-toggle-button"
          >
            <el-icon><component :is="showAdvancedParams ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
            {{ showAdvancedParams ? t('hide_advanced_parameters') : t('show_advanced_parameters') }}
          </el-button>
          
          <el-collapse-transition>
            <div v-show="showAdvancedParams" class="advanced-params-content">
              <div class="advanced-params-grid">
                <!-- Word Size -->
                <el-form-item :label="t('word_size')">
                  <el-input
                    type="number"
                    v-model.number="wordSize"
                    :min="3"
                    :max="28"
                    :placeholder="t('word_size')"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>{{ t('word_size_description') }}</span>
                  </div>
                </el-form-item>
                
                <!-- Match Score -->
                <el-form-item :label="t('match_score')">
                  <el-input
                    type="number"
                    v-model.number="matchScore"
                    :min="0"
                    :placeholder="t('match_score')"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>{{ t('match_score_description') }}</span>
                  </div>
                </el-form-item>
                
                <!-- Gap Open -->
                <el-form-item :label="t('gap_open')">
                  <el-input
                    type="number"
                    v-model.number="gapOpen"
                    :min="0"
                    :placeholder="t('gap_open_penalty')"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>{{ t('gap_open_description') }}</span>
                  </div>
                </el-form-item>
                
                <!-- Gap Extend -->
                <el-form-item :label="t('gap_extend')">
                  <el-input
                    type="number"
                    v-model.number="gapExtend"
                    :min="0"
                    :placeholder="t('gap_extend_penalty')"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>{{ t('gap_extend_description') }}</span>
                  </div>
                </el-form-item>
                
                <!-- Low Complexity Filter -->
                <el-form-item :label="t('low_complexity_filter')">
                  <el-switch v-model="lowComplexityFilter" />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>{{ t('low_complexity_filter_description') }}</span>
                  </div>
                </el-form-item>
              </div>
            </div>
          </el-collapse-transition>
        </div>
      </el-form>
    </el-card>
    
    <!-- 帮助信息卡片 -->
    <el-card class="help-card">
      <template #header>
        <div class="help-header">
          <h3><i class="fas fa-question-circle"></i> {{ t('blast_search') }} {{ t('help') }}</h3>
        </div>
      </template>
      <div class="help-content">
        <div class="help-section">
          <h4>{{ t('what_is_blast') }}</h4>
          <p>{{ t('blast_description_long') }}</p>
        </div>
        <div class="help-section">
          <h4>{{ t('blast_types_available') }}</h4>
          <ul>
            <li><strong>{{ t('blastp') }}</strong>: {{ t('protein') }}-protein BLAST</li>
            <li><strong>BLASTN</strong>: Nucleotide-nucleotide BLAST</li>
            <li><strong>BLASTX</strong>: Translated nucleotide-protein BLAST</li>
            <li><strong>TBLASTN</strong>: {{ t('protein') }}-translated nucleotide BLAST</li>
            <li><strong>TBLASTX</strong>: Translated nucleotide-translated nucleotide BLAST</li>
          </ul>
        </div>
        <div class="help-section">
          <h4>{{ t('tips_for_better_results') }}</h4>
          <ul>
            <li>{{ t('use_fasta_format_for_best_results') }}</li>
            <li>{{ t('keep_sequences_between_50_10000_characters') }}</li>
            <li>{{ t('adjust_e_value_based_on_sequence_length') }}</li>
            <li>{{ t('select_appropriate_databases_for_research') }}</li>
          </ul>
        </div>
      </div>
    </el-card>
  </div>
</template>



<style scoped>
/* 页面容器 */
.blastp-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

/* 页面标题 */
.page-header {
  text-align: left;
  margin-bottom: 30px;
}

.page-header h1 {
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

/* 错误提示 */
.error-alert {
  margin-bottom: 24px;
  border-radius: 8px;
}

/* 主要内容卡片 */
.main-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
  overflow: hidden;
}

/* BLAST类型标签页 */
.blast-type-tabs {
  margin-bottom: 24px;
  border-bottom: 2px solid #e9ecef;
}

.blast-type-tabs .el-tabs__header {
  border-bottom: none;
}

.blast-type-tabs .el-tabs__item {
  color: #666;
  font-weight: 500;
  padding: 12px 24px;
  margin-right: 20px;
  transition: all 0.3s ease;
}

.blast-type-tabs .el-tabs__item.is-active {
  color: #3a6ea5;
  font-weight: 600;
}

.blast-type-tabs .el-tabs__item.is-active::after {
  background-color: #3a6ea5;
  height: 3px;
  border-radius: 2px;
}

/* BLAST信息卡片 */
.blast-info-card {
  margin-bottom: 24px;
  border-radius: 8px;
  border-left: 4px solid #3a6ea5;
  padding: 16px 20px;
  background-color: #f0f7ff;
  border: 1px solid #d9ecff;
}

.blast-info-content .info-title {
  font-size: 18px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 8px;
}

.blast-info-content p {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin: 0;
}

/* BLAST表单 */
.blast-form {
  padding: 20px;
}

/* 表单顶部操作按钮 */
.form-header-actions {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e9ecef;
}

/* 表单弹性布局 */
.form-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
  margin-bottom: 30px;
}

.form-layout > .form-section {
  min-width: 0;
}

/* 表单区域 */
.form-section {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 20px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e9ecef;
}

/* 序列输入区域 */
.sequence-textarea {
  border-radius: 8px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
}

/* 表单操作按钮 */
.form-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.form-actions .el-upload {
  display: inline-block;
}

.form-actions .el-upload .el-upload-dragger {
  display: none;
}

/* 帮助文本 */
.help-text {
  font-size: 13px;
  color: #666;
  background-color: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #17a2b8;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.help-text i {
  color: #17a2b8;
  font-size: 14px;
  margin-top: 2px;
}

.help-text code {
  background-color: #e9ecef;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  color: #dc3545;
}

/* 参数网格 */
.parameter-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 25px;
}

.parameter-grid .el-form-item {
  min-width: 0;
}

/* 高级参数区域 */
.advanced-params-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.advanced-toggle-button {
  width: 100%;
  margin-bottom: 15px;
  justify-content: center;
}

.advanced-params-content {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.advanced-params-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 25px;
}

/* 基因组选择器 */
.genome-select {
  border-radius: 8px;
}

.submit-button,
.reset-button {
  padding: 12px 30px;
  font-size: 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.submit-button {
  background-color: #3a6ea5;
  border-color: #3a6ea5;
}

.submit-button:hover {
  background-color: #2d5582;
  border-color: #2d5582;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(58, 110, 165, 0.3);
}

/* 帮助卡片 */
.help-card {
  margin-top: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
}

.help-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.help-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #3a6ea5;
  margin: 0;
}

.help-content {
  padding: 20px;
}

.help-section {
  margin-bottom: 24px;
}

.help-section:last-child {
  margin-bottom: 0;
}

.help-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.help-section p {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 12px;
}

.help-section ul {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  padding-left: 20px;
  margin: 0;
}

.help-section li {
  margin-bottom: 8px;
}

.help-section li:last-child {
  margin-bottom: 0;
}

.help-section strong {
  color: #333;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .form-layout {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .parameter-grid {
    grid-template-columns: 1fr;
  }
  
  .advanced-params-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .blastp-view {
    padding: 10px;
  }
  
  .page-header h1 {
    font-size: 28px;
  }
  
  .blast-form {
    padding: 0 10px 10px;
  }
  
  .form-section {
    padding: 15px;
  }
  
  .form-header-actions {
    flex-direction: column;
    gap: 10px;
  }
  
  .submit-button,
  .reset-button {
    width: 100%;
  }
  
  .blast-type-tabs .el-tabs__item {
    padding: 10px 16px;
    margin-right: 10px;
    font-size: 14px;
  }
  
  .advanced-params-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 576px) {
  .sequence-textarea {
    min-height: 200px;
  }
  
  .el-form {
    .el-form-item {
      margin-bottom: 15px;
    }
  }
}
</style>