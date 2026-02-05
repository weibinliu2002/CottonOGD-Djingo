<template>
  <div class="container mt-4">
    <h1>{{ t('primer_design') }}</h1>
    <el-row :gutter="10">
      <el-col :span="6">
        <!-- {{ t('primer_design') }} Form -->
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <h3>{{ t('design_parameters') }}</h3>
            </div>
          </template>
          <el-form @submit.prevent="designPrimers">
            <!-- {{ t('sequence') }} Input Method Selection -->
            <el-form-item label="{{ t('sequence') }} Input Method">
              <br>
              <el-select v-model="inputMethod" style="width: 100%">
                <br>
                <el-option value="geneId" label="{{ t('gene_id') }}" />
                <el-option value="genomePosition" label="{{ t('genome') }} Position" />
                <el-option value="directSequence" label="Direct {{ t('sequence') }} Input" />
              </el-select>
            </el-form-item>
            
            <!-- Dynamic Form Based on Input Method -->
            <el-form-item>
              <!-- {{ t('gene_id') }} Input Method -->
              <div v-if="inputMethod === 'geneId'">
                <el-row :gutter="10">
                  <el-col :span="12">
                    <el-form-item>
                      <el-input
                        v-model="sequenceId"
                        placeholder="Enter {{ t('gene_id') }} or Transcript ID"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item>
                      <el-select v-model="sequenceType" style="width: 100%">
                        <el-option value="mrna" label="{{ t('mrna') }}" />
                        <el-option value="cds" label="{{ t('cds') }}" />
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
                        Fetch {{ t('sequence') }}
                      </el-button>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>
              
              <!-- {{ t('genome') }} Position Input Method -->
              <div v-if="inputMethod === 'genomePosition'">
                <el-form-item label="Select {{ t('genome') }}">
                  <el-select v-model="genomeAssembly" style="width: 100%">
                    <el-option value="" label="{{ t('please_select') }} genome" />
                    <el-option value="G.hirsutum(AD1)TM-1_HAU_v1.1" label="Upland cotton (G. hirsutum)" />
                    <el-option value="G.arboreum(A2)Shixiya1_HAU_v1.0" label="Asian cotton (G. arboreum)" />
                    <el-option value="G.raimondii(D5)JGI_v2.0" label="Raymond's cotton (G. raimondii)" />
                  </el-select>
                </el-form-item>
                <el-row :gutter="10">
                  <el-col :span="8">
                    <el-form-item label="{{ t('chromosome') }}">
                      <el-input
                        v-model="genomePosition.chromosome"
                        placeholder="{{ t('chromosome') }} name (e.g: A01)"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="{{ t('start_position') }}">
                      <el-input
                        type="number"
                        v-model.number="genomePosition.start"
                        placeholder="Start position"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="{{ t('end_position') }}">
                      <el-input
                        type="number"
                        v-model.number="genomePosition.end"
                        placeholder="End position"
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
                    Fetch {{ t('sequence') }}
                  </el-button>
                </el-form-item>
              </div>
              
              <!-- Direct {{ t('sequence') }} Input Method -->
              <div v-if="inputMethod === 'directSequence'">
                <el-form-item label="Direct {{ t('sequence') }} Input">
                  <el-input
                    type="textarea"
                    :rows="4"
                    v-model="directSequence"
                    placeholder="Direct input DNA sequence (5'→3')"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="useDirectSequence"
                    style="width: 100%"
                  >
                    Use This {{ t('sequence') }}
                  </el-button>
                </el-form-item>
              </div>
            </el-form-item>
            
            <!-- {{ t('sequence') }} Display Area -->
            <el-form-item label="DNA {{ t('sequence') }}" v-if="sequenceTemplate.trim()">
              <el-input
                type="textarea"
                :rows="5"
                v-model="sequenceTemplate"
                placeholder="{{ t('sequence') }} will be displayed here"
              />
            </el-form-item>
            
            <!-- Product Size Range -->
            <el-form-item label="Product Size Range (bp)">
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
            
            <!-- {{ t('primer_length') }} Range -->
            <el-form-item label="{{ t('primer_length') }} Range (bp)">
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
            
            <!-- Primer Tm Range -->
            <el-form-item label="Primer Tm Range (°C)">
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
            
            <!-- Primer {{ t('gc_content') }} Range -->
            <el-form-item label="Primer {{ t('gc_content') }} Range (%)">
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
            
            <!-- {{ t('submit') }} Button -->
            <el-form-item>
              <el-button 
                type="primary" 
                native-type="submit"
                :loading="isLoading"
                :disabled="!sequenceTemplate.trim()"
                style="width: 100%"
                size="large"
              >
                Design Primers
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- {{ t('results') }} Display -->
      <el-col :span="18">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <h3>Design {{ t('results') }}</h3>
            </div>
          </template>
          <div v-if="isLoading" class="text-center py-4">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p class="mt-2">Designing primers...</p>
          </div>
          
          <el-alert
            v-else-if="error"
            type="error"
            :title="error"
            show-icon
            class="mb-4"
          />
          
          <div v-else-if="designResults.length > 0">
            <h5>{{ t('primer_design') }} {{ t('results') }}</h5>
            <el-table :data="designTableData" style="width: 100%" border>
              <el-table-column prop="oligos" label="Oligos" width="120" />
              <el-table-column prop="startPosition" label="Start position" width="120" />
              <el-table-column prop="length" label="Length" width="80" />
              <el-table-column prop="tm" label="Tm" width="80" />
              <el-table-column prop="gcPercent" label="GC percent" width="100" />
              <el-table-column prop="selfAny" label="Self any" width="80" />
              <el-table-column prop="selfEnd" label="Self end" width="80" />
              <el-table-column prop="hairpin" label="{{ t('hairpin') }}" width="80" />
              <el-table-column prop="sequence" label="{{ t('sequence') }}" min-width="200" />
              <el-table-column prop="penalty" label="Penalty" width="80" />
            </el-table>
          </div>
          
          <div v-else class="text-center py-4">
            <p>Please input DNA sequence and set parameters, then click "Design Primers" button</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, reactive, computed } from 'vue'
import axios from '../utils/http'
import { usePrimerDesignStore } from '../stores/primerDesign'
import { Loading } from '@element-plus/icons-vue'

// 初始化store
const primerDesignStore = usePrimerDesignStore()

// 表单数据
const sequenceId = ref('')
const sequenceType = ref('mrna') // 默认t('mrna')
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

// Fetch sequence by gene ID
const fetchSequence = async () => {
  if (!sequenceId.value.trim()) {
    error.value = t('please_enter') + ' sequence ID'
    return
  }
  
  isFetching.value = true
  error.value = null
  
  try {
    // Call sequence fetch API
    const response = await axios.get('/tools/id-search/api/sequence/', {
      params: {
        gene_id: sequenceId.value.trim(),
        type: sequenceType.value
      }
    })
    
    if (response.status === 'success' && response.sequence) {
      // Fill sequence into template
      sequenceTemplate.value = response.sequence
      // Directly update store state
      primerDesignStore.sequenceId = sequenceId.value.trim()
      primerDesignStore.sequenceTemplate = response.sequence
    } else {
      error.value = t('sequence') + ' not found or empty'
    }
  } catch (err) {
    error.value = 'Failed to fetch sequence: ' + (err.message || 'Unknown error')
    console.error('Failed to fetch sequence:', err)
  } finally {
    isFetching.value = false
  }
}

// Fetch sequence by genome position
const fetchSequenceByPosition = async () => {
  if (!genomeAssembly.value || !genomePosition.chromosome.trim() || !genomePosition.start || !genomePosition.end) {
    error.value = 'Please fill in complete genome position information'
    return
  }
  
  isFetching.value = true
  error.value = null
  
  try {
    // Call genome position sequence fetch API
    const response = await axios.get('/tools/id-search/api/sequence/position/', {
      params: {
        genome: genomeAssembly.value,
        chromosome: genomePosition.chromosome.trim(),
        start: genomePosition.start,
        end: genomePosition.end
      }
    })
    
    if (response.status === 'success' && response.sequence) {
      // Fill sequence into template
      sequenceTemplate.value = response.sequence
      // t('update') store
      primerDesignStore.sequenceTemplate = response.sequence
    } else {
      error.value = t('sequence') + ' not found at this position or empty'
    }
  } catch (err) {
    error.value = 'Failed to fetch sequence: ' + (err.message || 'Unknown error')
    console.error('Failed to fetch sequence by genome position:', err)
  } finally {
    isFetching.value = false
  }
}

// Use directly input sequence
const useDirectSequence = () => {
  if (!directSequence.value.trim()) {
    error.value = t('please_enter') + ' sequence'
    return
  }
  
  // Remove possible spaces
  sequenceTemplate.value = directSequence.value.trim().replace(/\s/g, '')
  // t('update') store
  primerDesignStore.sequenceTemplate = sequenceTemplate.value
}

// Design primers function
const designPrimers = async () => {
  // Validate form
  if (!sequenceTemplate.value.trim()) {
    error.value = t('please_enter') + ' DNA sequence'
    return
  }
  
  // Set loading state
  isLoading.value = true
  error.value = null
  designResults.value = []
  
  try {
    // Build request data
    const requestData = {
      sequence_id: sequenceId.value.trim(),
      sequence_template: sequenceTemplate.value.trim().replace(/\s/g, ''), // Remove spaces
      parameters: parameters
    }
    
    // Call API
    const response = await axios.post('/tools/primer_design/api/primers/', requestData)
    
    if (response.status === 'success') {
      // t('save') results to store
      primerDesignStore.setDesignResults(response.results)
      designResults.value = response.results
    } else {
      error.value = response.error || 'Design failed'
    }
  } catch (err) {
    error.value = 'API request failed: ' + (err.message || 'Unknown error')
    console.error('Failed to design primers:', err)
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