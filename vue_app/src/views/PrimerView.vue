<template>
  <div class="container mt-4">
    <h1>引物设计</h1>
    <div class="row">
      <div class="col-md-3">
        <!-- 引物设计表单 -->
        <div class="card mb-4">
          <div class="card-header">
            <h3>设计参数</h3>
          </div>
          <div class="card-body">
            <form @submit.prevent="designPrimers">
              <!-- 序列输入方式选择框 -->
              <div class="form-group mb-3">
                <label for="inputMethod">序列输入方式</label>
                <select 
                  id="inputMethod" 
                  class="form-control" 
                  v-model="inputMethod"
                >
                  <option value="geneId">基因ID</option>
                  <option value="genomePosition">基因组位置</option>
                  <option value="directSequence">直接输入序列</option>
                </select>
              </div>
              
              <!-- 根据选择的输入方式动态显示对应的表单 -->
              <div class="form-group mb-3">
                <!-- 基因ID输入方式 -->
                <div v-if="inputMethod === 'geneId'">
                  <div class="input-group">
                    <input 
                      type="text" 
                      class="form-control" 
                      id="sequenceId" 
                      v-model="sequenceId" 
                      placeholder="输入基因ID或转录本ID"
                    >
                    <select class="form-control col-md-3" v-model="sequenceType">
                      <option value="mrna">mRNA</option>
                      <option value="cds">CDS</option>
                    </select>
                    <button 
                      type="button" 
                      class="btn btn-secondary" 
                      @click="fetchSequence" 
                      :disabled="!sequenceId.trim() || isFetching"
                    >
                      <span v-if="isFetching" class="spinner-border spinner-border-sm mr-2"></span>
                      获取序列
                    </button>
                  </div>
                </div>
                
                <!-- 基因组位置输入方式 -->
                <div v-if="inputMethod === 'genomePosition'">
                  <div class="form-group mb-2">
                    <label for="genomeAssembly">选择基因组</label>
                    <select 
                      id="genomeAssembly" 
                      class="form-control" 
                      v-model="genomeAssembly"
                    >
                      <option value="">请选择基因组</option>
                      <!-- 这里可以动态加载基因组列表，暂时使用静态选项 -->
                      <option value="G.hirsutum(AD1)TM-1_HAU_v1.1">陆地棉 (G. hirsutum)</option>
                      <option value="G.arboreum(A2)Shixiya1_HAU_v1.0">亚洲棉 (G. arboreum)</option>
                      <option value="G.raimondii(D5)JGI_v2.0">雷蒙德氏棉 (G. raimondii)</option>
                    </select>
                  </div>
                  <div class="row">
                    <div class="col-md-6 mb-2">
                      <input 
                        type="text" 
                        class="form-control" 
                        id="chromosome" 
                        v-model="genomePosition.chromosome" 
                        placeholder="染色体名称 (如: A01)"
                      >
                    </div>
                    <div class="col-md-3 mb-2">
                      <input 
                        type="number" 
                        class="form-control" 
                        id="startPos" 
                        v-model="genomePosition.start" 
                        placeholder="起始位置"
                      >
                    </div>
                    <div class="col-md-3 mb-2">
                      <input 
                        type="number" 
                        class="form-control" 
                        id="endPos" 
                        v-model="genomePosition.end" 
                        placeholder="结束位置"
                      >
                    </div>
                  </div>
                  <button 
                    type="button" 
                    class="btn btn-secondary w-100" 
                    @click="fetchSequenceByPosition" 
                    :disabled="!genomeAssembly || !genomePosition.chromosome.trim() || !genomePosition.start || !genomePosition.end || isFetching"
                  >
                    <span v-if="isFetching" class="spinner-border spinner-border-sm mr-2"></span>
                    获取序列
                  </button>
                </div>
                
                <!-- 直接输入序列方式 -->
                <div v-if="inputMethod === 'directSequence'">
                  <textarea 
                    class="form-control" 
                    id="directSequence" 
                    rows="4" 
                    v-model="directSequence" 
                    placeholder="直接输入DNA序列 (5'→3')"
                  ></textarea>
                  <button 
                    type="button" 
                    class="btn btn-secondary w-100 mt-2" 
                    @click="useDirectSequence"
                  >
                    使用该序列
                  </button>
                </div>
              </div>
              
              <!-- 序列显示区域 -->
              <div class="form-group mb-3" v-if="sequenceTemplate.trim()">
                <label for="sequenceTemplate">DNA序列</label>
                <textarea 
                  class="form-control" 
                  id="sequenceTemplate" 
                  rows="5"
                  v-model="sequenceTemplate"
                  placeholder="序列将显示在这里"
                  required
                ></textarea>
              </div>
              
              <!-- 产物大小范围 -->
              <div class="form-group mb-3">
                <label>产物大小范围 (bp)</label>
                <div class="input-group">
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.productSizeMin"
                    min="50"
                    max="2000"
                  >
                  <span class="input-group-text">-</span>
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.productSizeMax"
                    min="50"
                    max="2000"
                  >
                </div>
              </div>
              
              <!-- 引物长度范围 -->
              <div class="form-group mb-3">
                <label>引物长度范围 (bp)</label>
                <div class="input-group">
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.primerSizeMin"
                    min="15"
                    max="35"
                  >
                  <span class="input-group-text">-</span>
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.primerSizeMax"
                    min="15"
                    max="35"
                  >
                </div>
              </div>
              
              <!-- 引物Tm范围 -->
              <div class="form-group mb-3">
                <label>引物Tm范围 (°C)</label>
                <div class="input-group">
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.primerTmMin"
                    min="50"
                    max="75"
                    step="0.1"
                  >
                  <span class="input-group-text">-</span>
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.primerTmMax"
                    min="50"
                    max="75"
                    step="0.1"
                  >
                </div>
              </div>
              
              <!-- 引物GC含量范围 -->
              <div class="form-group mb-3">
                <label>引物GC含量范围 (%)</label>
                <div class="input-group">
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.primerGCMin"
                    min="20"
                    max="80"
                  >
                  <span class="input-group-text">-</span>
                  <input 
                    type="number" 
                    class="form-control"
                    v-model.number="parameters.primerGCMax"
                    min="20"
                    max="80"
                  >
                </div>
              </div>
              
              <!-- 提交按钮 -->
              <button 
                type="submit" 
                class="btn btn-primary btn-lg w-100"
                :disabled="isLoading || !sequenceTemplate.trim()"
              >
                <span v-if="isLoading" class="spinner-border spinner-border-sm mr-2"></span>
                设计引物
              </button>
            </form>
          </div>
        </div>
      </div>
      
      <!-- 结果显示 -->
      <div class="col-md-9">
        <div class="card mb-4">
          <div class="card-header">
            <h3>设计结果</h3>
          </div>
          <div class="card-body">
            <div v-if="isLoading" class="text-center">
              <div class="spinner-border" role="status">
                <span class="sr-only">Loading...</span>
              </div>
              <p class="mt-2">正在设计引物...</p>
            </div>
            
            <div v-else-if="error" class="alert alert-danger">
              {{ error }}
            </div>
            
            <div v-else-if="designResults.length > 0">
              <h5>引物设计结果</h5>
              <div class="table-responsive">
                <table class="table table-striped table-bordered">
                  <thead class="thead-dark">
                    <tr>
                      <th>Oligos</th>
                      <th>Start position</th>
                      <th>Length</th>
                      <th>Tm</th>
                      <th>GC percent</th>
                      <th>Self any</th>
                      <th>Self end</th>
                      <th>Hairpin</th>
                      <th>Sequence</th>
                      <th>Penalty</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="(result, index) in designResults" :key="index">
                      <!-- 上游引物 -->
                      <tr class="table-info">
                        <td>Forward primer</td>
                        <td>{{ result.forward.START }}</td>
                        <td>{{ result.forward.SIZE }}</td>
                        <td>{{ result.forward.TM }}</td>
                        <td>{{ result.forward.GC_PERCENT }}</td>
                        <td>{{ result.forward.SELF_ANY || 0 }}</td>
                        <td>{{ result.forward.SELF_END || 0 }}</td>
                        <td>{{ result.forward.HAIRPIN || 0 }}</td>
                        <td>{{ result.forward.SEQUENCE }}</td>
                        <td>{{ result.penalty }}</td>
                      </tr>
                      <!-- 下游引物 -->
                      <tr class="table-info">
                        <td>Reverse primer</td>
                        <td>{{ result.reverse.START }}</td>
                        <td>{{ result.reverse.SIZE }}</td>
                        <td>{{ result.reverse.TM }}</td>
                        <td>{{ result.reverse.GC_PERCENT }}</td>
                        <td>{{ result.reverse.SELF_ANY || 0 }}</td>
                        <td>{{ result.reverse.SELF_END || 0 }}</td>
                        <td>{{ result.reverse.HAIRPIN || 0 }}</td>
                        <td>{{ result.reverse.SEQUENCE }}</td>
                        <td>{{ result.penalty }}</td>
                      </tr>
                    </template>
                  </tbody>
                </table>
              </div>
            </div>
            
            <div v-else class="text-center">
              <p>请输入DNA序列并设置参数，然后点击"设计引物"按钮</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from '../utils/http'
import { usePrimerDesignStore } from '../stores/primerDesign'

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
.form-group label {
  font-weight: bold;
}

.card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.card-body {
  padding: 1.5rem;
}

.input-group {
  display: flex;
}
</style>