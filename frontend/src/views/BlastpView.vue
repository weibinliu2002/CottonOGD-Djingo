<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Search, Refresh, DocumentCopy, Delete, ArrowUp, ArrowDown, Upload } from '@element-plus/icons-vue'
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
      <h1>BLAST Search</h1>
      <p class="page-description">
        Perform sequence similarity searches against cotton genome databases using BLAST algorithms.
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
          <h3 class="info-title">{{ blastTypes.find(type => type.value === selectedBlastType)?.label }} Description</h3>
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
            Run BLAST Search
          </el-button>
          <el-button type="default" @click="resetForm" size="large" class="reset-button">
            <el-icon><Refresh /></el-icon>
            Reset Form
          </el-button>
        </div>
        
        <div class="form-layout">
          <!-- 序列输入区域 -->
          <div class="form-section">
            <h3 class="section-title">Sequence Input</h3>
            
            <!-- 序列输入 -->
            <el-form-item label="Query Sequence">
              <el-input
                type="textarea"
                :rows="10"
                v-model="sequence"
                :placeholder="selectedBlastType === 'blastp' || selectedBlastType === 'blastx' ? 'Please enter a protein sequence in FASTA or plain text format' : 'Please enter a nucleotide sequence in FASTA or plain text format'"
                class="sequence-textarea"
              />
              <div class="form-actions mt-2">
                <el-button type="info" size="small" @click="fillExample">
                  <el-icon><DocumentCopy /></el-icon>
                  Load Example Sequence
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
                      Upload File
                    </el-button>
                  </template>
                </el-upload>
                <el-button type="warning" size="small" @click="sequence = ''">
                  <el-icon><Delete /></el-icon>
                  Clear Sequence
                </el-button>
              </div>
              <div class="help-text mt-2">
                <i class="fas fa-info-circle"></i>
                <span>Enter your sequence in FASTA or plain text format. The example will be loaded based on the selected BLAST type.</span>
              </div>
            </el-form-item>
          </div>
          
          <!-- 搜索参数区域 -->
          <div class="form-section">
            <h3 class="section-title">Search Parameters</h3>
            
            <!-- 基因组选择 -->
            <el-form-item label="Select Genomes">
              <el-select
                v-model="selectedGenomes"
                filterable
                allow-create
                default-first-option
                placeholder="Select genome or genome category"
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
                <span>Select one or more genomes to search against. You can also select entire genome categories.</span>
              </div>
            </el-form-item>
            
            <!-- 数据库类型选择 -->
            <el-form-item label="Database Type">
              <el-select
                v-model="selectedDatabaseType"
                placeholder="Select database type"
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
                <span>Choose the type of sequence database to search against.</span>
              </div>
            </el-form-item>
            
            <!-- 参数设置 -->
            <div class="parameter-grid">
              <!-- E-value阈值 -->
              <el-form-item label="E-value Threshold">
                <el-input
                  type="number"
                  v-model.number="evalue"
                  :step="0.01"
                  :min="0"
                  placeholder="E-value"
                  class="w-full"
                />
                <div class="help-text mt-1">
                  <i class="fas fa-info-circle"></i>
                  <span>The expectation value threshold for saving hits (default: 0.01)</span>
                </div>
              </el-form-item>
              
              <!-- 最大目标序列数 -->
              <el-form-item label="Max Target Sequences">
                <el-input
                  type="number"
                  v-model.number="maxTargetSeqs"
                  :min="1"
                  :max="50"
                  placeholder="Max sequences"
                  class="w-full"
                />
                <div class="help-text mt-1">
                  <i class="fas fa-info-circle"></i>
                  <span>Maximum number of aligned sequences to keep (default: 30)</span>
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
            {{ showAdvancedParams ? 'Hide Advanced Parameters' : 'Show Advanced Parameters' }}
          </el-button>
          
          <el-collapse-transition>
            <div v-show="showAdvancedParams" class="advanced-params-content">
              <div class="advanced-params-grid">
                <!-- Word Size -->
                <el-form-item label="Word Size">
                  <el-input
                    type="number"
                    v-model.number="wordSize"
                    :min="3"
                    :max="28"
                    placeholder="Word size"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>Word size for wordfinder algorithm (default: 11)</span>
                  </div>
                </el-form-item>
                
                <!-- Match Score -->
                <el-form-item label="Match Score">
                  <el-input
                    type="number"
                    v-model.number="matchScore"
                    :min="0"
                    placeholder="Match score"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>Match score threshold (default: 0)</span>
                  </div>
                </el-form-item>
                
                <!-- Gap Open -->
                <el-form-item label="Gap Open">
                  <el-input
                    type="number"
                    v-model.number="gapOpen"
                    :min="0"
                    placeholder="Gap open penalty"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>Gap open penalty (default: 11)</span>
                  </div>
                </el-form-item>
                
                <!-- Gap Extend -->
                <el-form-item label="Gap Extend">
                  <el-input
                    type="number"
                    v-model.number="gapExtend"
                    :min="0"
                    placeholder="Gap extend penalty"
                    class="w-full"
                  />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>Gap extend penalty (default: 1)</span>
                  </div>
                </el-form-item>
                
                <!-- Low Complexity Filter -->
                <el-form-item label="Low Complexity Filter">
                  <el-switch v-model="lowComplexityFilter" />
                  <div class="help-text mt-1">
                    <i class="fas fa-info-circle"></i>
                    <span>Filter out low complexity regions (default: true)</span>
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
          <h3><i class="fas fa-question-circle"></i> BLAST Search Help</h3>
        </div>
      </template>
      <div class="help-content">
        <div class="help-section">
          <h4>What is BLAST?</h4>
          <p>BLAST (Basic Local Alignment Search Tool) is an algorithm for comparing primary biological sequence information, such as the amino-acid sequences of proteins or the nucleotides of DNA and/or RNA sequences.</p>
        </div>
        <div class="help-section">
          <h4>BLAST Types Available</h4>
          <ul>
            <li><strong>BLASTP</strong>: Protein-protein BLAST</li>
            <li><strong>BLASTN</strong>: Nucleotide-nucleotide BLAST</li>
            <li><strong>BLASTX</strong>: Translated nucleotide-protein BLAST</li>
            <li><strong>TBLASTN</strong>: Protein-translated nucleotide BLAST</li>
            <li><strong>TBLASTX</strong>: Translated nucleotide-translated nucleotide BLAST</li>
          </ul>
        </div>
        <div class="help-section">
          <h4>Tips for Better Results</h4>
          <ul>
            <li>Use FASTA format for best results</li>
            <li>Keep sequences between 50-10,000 characters</li>
            <li>Adjust E-value based on your sequence length and complexity</li>
            <li>Select appropriate databases for your research question</li>
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
  text-align: center;
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
  margin: 0 auto;
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