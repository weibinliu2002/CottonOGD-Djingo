<template>
  <div class="container mt-4">
    <h1>引物设计</h1>
    <el-row :gutter="20">
      <el-col :span="6">
        <!-- 引物设计表单 -->
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <h3>设计参数</h3>
            </div>
          </template>
          <el-form @submit.prevent="designPrimers">
            <!-- 序列输入方式选择框 -->
            <el-form-item label="序列输入方式">
              <el-select v-model="inputMethod" style="width: 100%">
                <el-option value="geneId" label="基因ID" />
                <el-option value="genomePosition" label="基因组位置" />
                <el-option value="directSequence" label="直接输入序列" />
              </el-select>
            </el-form-item>
            
            <!-- 根据选择的输入方式动态显示对应的表单 -->
            <el-form-item>
              <!-- 基因ID输入方式 -->
              <div v-if="inputMethod === 'geneId'">
                <el-row :gutter="10">
                  <el-col :span="12">
                    <el-form-item>
                      <el-input
                        v-model="sequenceId"
                        placeholder="输入基因ID或转录本ID"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item>
                      <el-select v-model="sequenceType" style="width: 100%">
                        <el-option value="mrna" label="mRNA" />
                        <el-option value="cds" label="CDS" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item>
                      <el-button 
                        type="primary" 
                        @click="fetchSequence" 
                        :loading="isFetching"
                        :disabled="!sequenceId.trim()"
                      >
                        获取序列
                      </el-button>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>
              
              <!-- 基因组位置输入方式 -->
              <div v-if="inputMethod === 'genomePosition'">
                <el-form-item label="选择基因组">
                  <el-select v-model="genomeAssembly" style="width: 100%">
                    <el-option value="" label="请选择基因组" />
                    <el-option value="G.hirsutum(AD1)TM-1_HAU_v1.1" label="陆地棉 (G. hirsutum)" />
                    <el-option value="G.arboreum(A2)Shixiya1_HAU_v1.0" label="亚洲棉 (G. arboreum)" />
                    <el-option value="G.raimondii(D5)JGI_v2.0" label="雷蒙德氏棉 (G. raimondii)" />
                  </el-select>
                </el-form-item>
                <el-row :gutter="10">
                  <el-col :span="8">
                    <el-form-item label="染色体">
                      <el-input
                        v-model="genomePosition.chromosome"
                        placeholder="染色体名称 (如: A01)"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="起始位置">
                      <el-input
                        type="number"
                        v-model.number="genomePosition.start"
                        placeholder="起始位置"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="结束位置">
                      <el-input
                        type="number"
                        v-model.number="genomePosition.end"
                        placeholder="结束位置"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="fetchSequenceByPosition" 
                    :loading="isFetching"
                    :disabled="!genomeAssembly || !genomePosition.chromosome.trim() || !genomePosition.start || !genomePosition.end"
                    style="width: 100%"
                  >
                    获取序列
                  </el-button>
                </el-form-item>
              </div>
              
              <!-- 直接输入序列方式 -->
              <div v-if="inputMethod === 'directSequence'">
                <el-form-item label="直接输入序列">
                  <el-input
                    type="textarea"
                    :rows="4"
                    v-model="directSequence"
                    placeholder="直接输入DNA序列 (5'→3')"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="useDirectSequence"
                    style="width: 100%"
                  >
                    使用该序列
                  </el-button>
                </el-form-item>
              </div>
            </el-form-item>
            
            <!-- 序列显示区域 -->
            <el-form-item label="DNA序列" v-if="sequenceTemplate.trim()">
              <el-input
                type="textarea"
                :rows="5"
                v-model="sequenceTemplate"
                placeholder="序列将显示在这里"
              />
            </el-form-item>
            
            <!-- 产物大小范围 -->
            <el-form-item label="产物大小范围 (bp)">
              <el-row :gutter="10">
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.productSizeMin"
                    :min="50"
                    :max="2000"
                  />
                </el-col>
                <el-col :span="4" class="text-center pt-2">
                  -
                </el-col>
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.productSizeMax"
                    :min="50"
                    :max="2000"
                  />
                </el-col>
              </el-row>
            </el-form-item>
            
            <!-- 引物长度范围 -->
            <el-form-item label="引物长度范围 (bp)">
              <el-row :gutter="10">
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.primerSizeMin"
                    :min="15"
                    :max="35"
                  />
                </el-col>
                <el-col :span="4" class="text-center pt-2">
                  -
                </el-col>
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.primerSizeMax"
                    :min="15"
                    :max="35"
                  />
                </el-col>
              </el-row>
            </el-form-item>
            
            <!-- 引物Tm范围 -->
            <el-form-item label="引物Tm范围 (°C)">
              <el-row :gutter="10">
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.primerTmMin"
                    :min="50"
                    :max="75"
                    :step="0.1"
                  />
                </el-col>
                <el-col :span="4" class="text-center pt-2">
                  -
                </el-col>
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.primerTmMax"
                    :min="50"
                    :max="75"
                    :step="0.1"
                  />
                </el-col>
              </el-row>
            </el-form-item>
            
            <!-- 引物GC含量范围 -->
            <el-form-item label="引物GC含量范围 (%)">
              <el-row :gutter="10">
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.primerGCMin"
                    :min="20"
                    :max="80"
                  />
                </el-col>
                <el-col :span="4" class="text-center pt-2">
                  -
                </el-col>
                <el-col :span="10">
                  <el-input
                    type="number"
                    v-model.number="parameters.primerGCMax"
                    :min="20"
                    :max="80"
                  />
                </el-col>
              </el-row>
            </el-form-item>
            
            <!-- 提交按钮 -->
            <el-form-item>
              <el-button 
                type="primary" 
                native-type="submit"
                :loading="isLoading"
                :disabled="!sequenceTemplate.trim()"
                style="width: 100%"
                size="large"
              >
                设计引物
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 结果显示 -->
      <el-col :span="18">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <h3>设计结果</h3>
            </div>
          </template>
          <div v-if="isLoading" class="text-center py-4">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p class="mt-2">正在设计引物...</p>
          </div>
          
          <el-alert
            v-else-if="error"
            type="error"
            :title="error"
            show-icon
            class="mb-4"
          />
          
          <div v-else-if="designResults.length > 0">
            <h5>引物设计结果</h5>
            <el-table :data="designTableData" style="width: 100%" border>
              <el-table-column prop="oligos" label="Oligos" width="120" />
              <el-table-column prop="startPosition" label="Start position" width="120" />
              <el-table-column prop="length" label="Length" width="80" />
              <el-table-column prop="tm" label="Tm" width="80" />
              <el-table-column prop="gcPercent" label="GC percent" width="100" />
              <el-table-column prop="selfAny" label="Self any" width="80" />
              <el-table-column prop="selfEnd" label="Self end" width="80" />
              <el-table-column prop="hairpin" label="Hairpin" width="80" />
              <el-table-column prop="sequence" label="Sequence" min-width="200" />
              <el-table-column prop="penalty" label="Penalty" width="80" />
            </el-table>
          </div>
          
          <div v-else class="text-center py-4">
            <p>请输入DNA序列并设置参数，然后点击"设计引物"按钮</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import axios from '../utils/http'
import { usePrimerDesignStore } from '../stores/primerDesign'
import { Loading } from '@element-plus/icons-vue'

// 初始化store
const primerDesignStore = usePrimerDesignStore()

// 表单数据
const sequenceId = ref('')
const sequenceType = ref('mrna') // 默认mRNA
const inputMethod = ref('geneId') // 默认使用基因ID输入方式
const genomeAssembly = ref('') // 选择的基因组
const genomePosition = reactive({
  chromosome: '',
  start: null,
  end: null
})
const directSequence = ref('')
const sequenceTemplate = ref('')
const parameters = reactive({
  productSizeMin: 100,
  productSizeMax: 250,
  primerSizeMin: 18,
  primerSizeMax: 27,
  primerTmMin: 57,
  primerTmMax: 63,
  primerGCMin: 20,
  primerGCMax: 80
})

// 状态
const isLoading = ref(false)
const isFetching = ref(false)
const error = ref(null)
const designResults = ref([])

// 计算表格数据
const designTableData = computed(() => {
  const tableData = []
  designResults.value.forEach((result, index) => {
    // 上游引物
    tableData.push({
      oligos: 'Forward primer',
      startPosition: result.forward.START,
      length: result.forward.SIZE,
      tm: result.forward.TM,
      gcPercent: result.forward.GC_PERCENT,
      selfAny: result.forward.SELF_ANY || 0,
      selfEnd: result.forward.SELF_END || 0,
      hairpin: result.forward.HAIRPIN || 0,
      sequence: result.forward.SEQUENCE,
      penalty: result.penalty
    })
    // 下游引物
    tableData.push({
      oligos: 'Reverse primer',
      startPosition: result.reverse.START,
      length: result.reverse.SIZE,
      tm: result.reverse.TM,
      gcPercent: result.reverse.GC_PERCENT,
      selfAny: result.reverse.SELF_ANY || 0,
      selfEnd: result.reverse.SELF_END || 0,
      hairpin: result.reverse.HAIRPIN || 0,
      sequence: result.reverse.SEQUENCE,
      penalty: result.penalty
    })
  })
  return tableData
})

// 通过基因ID获取序列
const fetchSequence = async () => {
  if (!sequenceId.value.trim()) {
    error.value = '请输入序列ID'
    return
  }
  
  isFetching.value = true
  error.value = null
  
  try {
    // 调用序列获取API
    const response = await axios.get('/tools/id-search/api/sequence/', {
      params: {
        gene_id: sequenceId.value.trim(),
        type: sequenceType.value
      }
    })
    
    if (response.status === 'success' && response.sequence) {
      // 填充序列到模板中
      sequenceTemplate.value = response.sequence
      // 直接更新store的state
      primerDesignStore.sequenceId = sequenceId.value.trim()
      primerDesignStore.sequenceTemplate = response.sequence
    } else {
      error.value = '未找到该序列或序列为空'
    }
  } catch (err) {
    error.value = '获取序列失败: ' + (err.message || '未知错误')
    console.error('获取序列失败:', err)
  } finally {
    isFetching.value = false
  }
}

// 通过基因组位置获取序列
const fetchSequenceByPosition = async () => {
  if (!genomeAssembly.value || !genomePosition.chromosome.trim() || !genomePosition.start || !genomePosition.end) {
    error.value = '请填写完整的基因组位置信息'
    return
  }
  
  isFetching.value = true
  error.value = null
  
  try {
    // 调用基因组位置获取序列API
    const response = await axios.get('/tools/id-search/api/sequence/position/', {
      params: {
        genome: genomeAssembly.value,
        chromosome: genomePosition.chromosome.trim(),
        start: genomePosition.start,
        end: genomePosition.end
      }
    })
    
    if (response.status === 'success' && response.sequence) {
      // 填充序列到模板中
      sequenceTemplate.value = response.sequence
      // 更新store
      primerDesignStore.sequenceTemplate = response.sequence
    } else {
      error.value = '未找到该位置的序列或序列为空'
    }
  } catch (err) {
    error.value = '获取序列失败: ' + (err.message || '未知错误')
    console.error('通过基因组位置获取序列失败:', err)
  } finally {
    isFetching.value = false
  }
}

// 使用直接输入的序列
const useDirectSequence = () => {
  if (!directSequence.value.trim()) {
    error.value = '请输入序列'
    return
  }
  
  // 去除可能的空格
  sequenceTemplate.value = directSequence.value.trim().replace(/\s/g, '')
  // 更新store
  primerDesignStore.sequenceTemplate = sequenceTemplate.value
}

// 设计引物函数
const designPrimers = async () => {
  // 验证表单
  if (!sequenceTemplate.value.trim()) {
    error.value = '请输入DNA序列'
    return
  }
  
  // 设置加载状态
  isLoading.value = true
  error.value = null
  designResults.value = []
  
  try {
    // 构建请求数据
    const requestData = {
      sequence_id: sequenceId.value.trim(),
      sequence_template: sequenceTemplate.value.trim().replace(/\s/g, ''), // 去除空格
      parameters: parameters
    }
    
    // 调用API
    const response = await axios.post('/tools/primer_design/api/primers/', requestData)
    
    if (response.status === 'success') {
      // 保存结果到store
      primerDesignStore.setDesignResults(response.results)
      designResults.value = response.results
    } else {
      error.value = response.error || '设计失败'
    }
  } catch (err) {
    error.value = 'API请求失败: ' + (err.message || '未知错误')
    console.error('设计引物失败:', err)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.mt-4 {
  margin-top: 1.5rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.card-header {
  font-size: 18px;
  font-weight: 500;
}

.text-center {
  text-align: center;
}

.py-4 {
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.pt-2 {
  padding-top: 0.5rem;
}

.is-loading {
  font-size: 24px;
  color: #409EFF;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>