<template>
  <div class="container mt-6">
    <h1 class="page-title">{{ t('primer_design') }}</h1>
    <el-row :gutter="20">
      <el-col :span="8">
        <!-- Primer Design Form -->
        <el-card class="mb-6">
          <template #header>
            <div class="card-header">
              <h3>{{ t('design_parameters') }}</h3>
            </div>
          </template>
          <el-form @submit.prevent="designPrimers" label-width="180px">
            <!-- Sequence Input Method Selection -->
            <el-form-item :label="t('sequence_input_method')" class="form-item-spacing">
              
              <el-select v-model="inputMethod" style="width: 100%">
                <el-option value="geneId" :label="t('gene_id')" />
                <el-option value="genomePosition" :label="t('genome_position')" />
                <el-option value="directSequence" :label="t('direct_sequence_input')" />
              </el-select>
            </el-form-item>
            
            <!-- Dynamic Form Based on Input Method -->
            <div class="form-item-spacing">
              <!-- Gene ID Input Method -->
              <div v-if="inputMethod === 'geneId'">
                <el-form-item :label="t('select_genome')">
                  <el-select v-model="genomeAssembly" style="width: 100%">
                    <el-option value="" :label="t('please_select_genome')" />
                    <el-option
                      v-for="option in computedGenomeOptions"
                      :key="option.value"
                      :value="option.value"
                      :label="option.label"
                    />
                  </el-select>
                </el-form-item>
                <el-row :gutter="10">
                  <el-col :span="24">
                    <el-form-item>
                      <el-input
                        v-model="sequenceId"
                        :placeholder="t('enter_gene_id_or_transcript_id')"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="18">
                    <el-form-item>
                      <el-select v-model="sequenceType" style="width: 100%">
                        <el-option value="mrna" label="mRNA" />
                        <el-option value="cds" label="CDS" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="18">
                    <el-form-item>
                      <el-button 
                        type="primary" 
                        @click="fetchSequence" 
                        :disabled="!sequenceId.trim() || !genomeAssembly"
                        style="width: 100%"
                      >
                        {{ t('fetch_sequence') }}
                      </el-button>
                    </el-form-item>
                  </el-col>
                  <el-col :span="18">
                    <el-form-item>
                      <el-button 
                        type="info" 
                        @click="loadExample"
                        style="width: 100%"
                      >
                        {{ t('load_example') }}
                      </el-button>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>
              
              <!-- Genome Position Input Method -->
              <div v-if="inputMethod === 'genomePosition'">
                <el-form-item :label="t('select_genome')">
                  <el-select v-model="genomeAssembly" style="width: 100%">
                    <el-option value="" :label="t('please_select_genome')" />
                    <el-option
                      v-for="option in computedGenomeOptions"
                      :key="option.value"
                      :value="option.value"
                      :label="option.label"
                    />
                  </el-select>
                </el-form-item>
                <el-row :gutter="10">
                  <el-col :span="24">
                    <el-form-item :label="t('chromosome')">
                      <el-select
                        v-model="genomePosition.chromosome"
                        :placeholder="t('select_chromosome')"
                        style="width: 100%"
                      >
                        <el-option
                          v-for="chromosome in chromosomeList"
                          :key="chromosome"
                          :value="chromosome"
                          :label="chromosome"
                        />
                      </el-select>
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="10" class="mt-2">
                  <el-col :span="24">
                    <el-form-item :label="t('start_position')">
                      <el-input
                        type="number"
                        v-model.number="genomePosition.start"
                        :placeholder="t('start_position')"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="10" class="mt-2">
                  <el-col :span="24">
                    <el-form-item :label="t('end_position')">
                      <el-input
                        type="number"
                        v-model.number="genomePosition.end"
                        :placeholder="t('end_position')"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="fetchSequenceByPosition" 
                    :disabled="!genomeAssembly || !genomePosition.chromosome.trim() || !genomePosition.start || !genomePosition.end"
                    style="width: 100%"
                  >
                    {{ t('fetch_sequence') }}
                  </el-button>
                </el-form-item>
              </div>
              
              <!-- Direct Sequence Input Method -->
              <div v-if="inputMethod === 'directSequence'">
                <el-form-item :label="t('direct_sequence_input')">
                  <el-input
                    type="textarea"
                    :rows="6"
                    v-model="directSequence"
                    :placeholder="t('direct_input_dna_sequence_5_3')"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="useDirectSequence"
                    style="width: 100%"
                  >
                    {{ t('use_this_sequence') }}
                  </el-button>
                </el-form-item>
              </div>
            </div>
            
            <!-- Sequence Display Area -->
            <el-form-item :label="t('dna_sequence')" v-if="sequenceTemplate.trim()" class="form-item-spacing">
              <el-input
                type="textarea"
                :rows="6"
                v-model="sequenceTemplate"
                :placeholder="t('sequence_will_be_displayed_here')"
              />
            </el-form-item>
            
            <!-- Product Size Range -->
            <el-form-item :label="t('product_size_range_bp')" class="form-item-spacing">
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
            
            <!-- Primer Length Range -->
            <el-form-item :label="t('primer_length_range_bp')" class="form-item-spacing">
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
            <el-form-item :label="t('primer_tm_range_c')" class="form-item-spacing">
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
            
            <!-- Primer GC Content Range -->
            <el-form-item :label="t('primer_gc_content_range')" class="form-item-spacing">
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
            
            <!-- Submit Button -->
            <el-form-item class="form-item-spacing">
              <el-button 
                type="primary" 
                native-type="submit"
                :disabled="isSequenceEmpty"
                @click="console.log('Button clicked, isSequenceEmpty:', isSequenceEmpty, 'sequenceTemplate:', sequenceTemplate)"
                style="width: 100%"
                size="large"
              >
                {{ t('design_primers') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- Results Display -->
      <el-col :span="16">
        <el-card class="mb-6">
          <template #header>
            <div class="card-header">
              <h3>{{ t('design_results') }}</h3>
            </div>
          </template>
          <div v-if="isLoading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p class="mt-3">{{ t('designing_primers') }}...</p>
          </div>
          
          <el-alert
            v-else-if="error"
            type="error"
            :title="error"
            show-icon
            class="mb-6"
          />
          
          <div v-else-if="designResults.length > 0" class="results-container">
            <div class="flex justify-between items-center mb-4">
              <h5 class="results-title">{{ t('primer_design_results') }}</h5>
              <el-button 
                type="success" 
                icon="Download"
                @click="downloadResults"
              >
                {{ t('download_excel') }}
              </el-button>
            </div>
            <el-table :data="designTableData" style="width: 100%" border size="medium">
              <el-table-column prop="oligos" :label="t('oligos')" width="140" />
              <!--<el-table-column prop="startPosition" :label="t('start_position')" width="140" />
              <el-table-column prop="length" :label="t('length')" width="100" />-->
              <el-table-column prop="tm" label="Tm" width="100" />
              <el-table-column prop="gcPercent" :label="t('gc_percent')" width="120" />
              <el-table-column prop="selfAny" :label="t('self_any')" width="100" />
              <el-table-column prop="selfEnd" :label="t('self_end')" width="100" />
              <el-table-column prop="hairpin" :label="t('hairpin')" width="100" />
              <el-table-column prop="sequence" :label="t('sequence')" min-width="250" />
              <el-table-column prop="penalty" :label="t('penalty')" width="100" />
            </el-table>
          </div>
          
          <div v-else class="empty-container">
            <p>{{ t('please_input_dna_sequence_and_set_parameters') }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 鍥炲埌椤堕儴 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePrimerDesignStore } from '@/stores/primerDesign'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import { Loading } from '@element-plus/icons-vue'
import httpInstance from '@/utils/http'
import { treemapResquarify } from 'd3'

const { t } = useI18n()

// 閸掓繂顫愰崠鏉漷ore
const primerDesignStore = usePrimerDesignStore()
const { genomeOptions: groupedGenomeOptions, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()

const sequenceId = computed({
  get: () => primerDesignStore.sequenceId,
  set: (val) => primerDesignStore.setSequence(val, primerDesignStore.sequenceTemplate)
})
const sequenceType = computed({
  get: () => primerDesignStore.sequenceType,
  set: (val) => primerDesignStore.setSequenceType(val)
})
const inputMethod = ref('geneId') // 姒涙顓绘担璺ㄦ暏閸╁搫娲淚D鏉堟挸鍙嗛弬鐟扮础
const genomeAssembly = ref('G.hirsutumAD1_TM-1_HAU_v1.1')
const genomePosition = reactive({
  chromosome: '',
  start: null,
  end: null
})
const chromosomeList = ref([])
const isLoadingChromosomes = ref(false)
const directSequence = ref('')
const sequenceTemplate = computed({
  get: () => primerDesignStore.sequenceTemplate,
  set: (val) => primerDesignStore.setSequence(primerDesignStore.sequenceId, val)
})
const parameters = computed({
  get: () => primerDesignStore.parameters,
  set: (val) => primerDesignStore.setParameters(val)
})

const isLoading = computed({
  get: () => primerDesignStore.isLoading,
  set: (val) => primerDesignStore.setLoading(val)
})
const isFetching = computed({
  get: () => primerDesignStore.isFetching,
  set: (val) => primerDesignStore.setFetching(val)
})
const error = computed({
  get: () => primerDesignStore.error,
  set: (val) => primerDesignStore.setError(val)
})
const designResults = computed({
  get: () => primerDesignStore.designResults,
  set: (val) => primerDesignStore.setDesignResults(val)
})

const isSequenceEmpty = computed(() => {
  return !sequenceTemplate.value || sequenceTemplate.value.trim() === ''
})

const designTableData = computed(() => {
  const tableData = []
  designResults.value.forEach((result, index) => {
    // 娑撳﹥鐖跺鏇犲⒖
    tableData.push({
      oligos: t('forward_primer'),
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
    // 娑撳鐖跺鏇犲⒖
    tableData.push({
      oligos: t('reverse_primer'),
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

const computedGenomeOptions = computed(() => {
  const allGenomes = groupedGenomeOptions.value.flatMap((option) =>
    option.children?.map((child) => ({
      value: child.value,
      label: child.label
    })) || []
  )
  return allGenomes
})

const fetchChromosomes = async (genome) => {
  if (!genome) {
    chromosomeList.value = []
    return
  }
  
  isLoadingChromosomes.value = true
  
  try {
    const faiUrl = `/data/genome/${genome}/${genome}.genome.fa.gz.fai`
    console.log('Fetching .fai file:', faiUrl)
    
    const response = await fetch(faiUrl)
    if (!response.ok) {
      throw new Error(`Failed to fetch .fai file: ${response.statusText}`)
    }
    
    const text = await response.text()
    
    if (text.includes('<html')) {
      throw new Error('Received HTML instead of .fai file content')
    }
    
    const lines = text.trim().split('\n')
    const chromosomes = []
    
    for (const line of lines) {
      const parts = line.split('\t')
      if (parts.length > 0) {
        const chromosomeName = parts[0]
        if (chromosomeName && !chromosomeName.includes('<')) {
          chromosomes.push(chromosomeName)
        }
      }
    }
    
    chromosomeList.value = chromosomes
    console.log('Extracted chromosomes:', chromosomes)
  } catch (error) {
    console.error('Failed to fetch chromosomes:', error)
    chromosomeList.value = []
  } finally {
    isLoadingChromosomes.value = false
  }
}

watch(genomeAssembly, async (newGenome) => {
  await fetchChromosomes(newGenome)
  genomePosition.chromosome = ''
})

// 缂佸嫪娆㈤幐鍌濇祰閺冩儼骞忛崣鏍х唨閸ョ姷绮嶉弫鐗堝祦
onMounted(async () => {
  await ensureGenomesLoaded()
  if (!genomeAssembly.value) {
    genomeAssembly.value = pickDefaultGenome()
  }
  if (genomeAssembly.value) {
    await fetchChromosomes(genomeAssembly.value)
  }
})

const loadExample = () => {
  // 鐠佸墽鐤嗙粈杞扮伐閸╁搫娲淚D
  sequenceId.value = 'Ghir_A01G000120.2'
  genomeAssembly.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  // 鐠佸墽鐤嗘妯款吇鎼村繐鍨猾璇茬€?  sequenceType.value = 'mrna'
}

// Fetch sequence by gene ID
const fetchSequence = async () => {
  if (!sequenceId.value.trim()) {
    error.value = t('please_enter_sequence_id')
    return
  }
  
  if (!genomeAssembly.value) {
    error.value = t('please_select_genome')
    return
  }
  
  isFetching.value = true
  error.value = null
  let sequence = ''
  
  try {
    // 閻╁瓨甯寸拫鍐暏 extract_seq閿涘奔绱堕柅?gene_id 閸?genome_id
    const seqResponse = await httpInstance.post('/CottonOGD_api/extract_seq/', {
      gene_id: sequenceId.value.trim(),
      genome_id: genomeAssembly.value
    })
    
    if (seqResponse.seq) {
      if (sequenceType.value === 'mrna') {
        sequence = seqResponse.seq.mrna_seq?.[0]?.seq || ''
      } else if (sequenceType.value === 'cds') {
        sequence = seqResponse.seq.cds_seq?.[0]?.seq || ''
      }
      
      if (sequence) {
        sequenceTemplate.value = sequence
        primerDesignStore.setSequence(sequenceId.value.trim(), sequence)
      } else {
        error.value = t('sequence_not_found_or_empty')
      }
    } else {
      error.value = seqResponse.error || t('sequence_not_found_or_empty')
    }
  } catch (err) {
    error.value = t('failed_to_fetch_sequence') + ': ' + (err.message || t('unknown_error'))
    console.error('Failed to fetch sequence:', err)
  } finally {
    isFetching.value = false
  }
}

// Fetch sequence by genome position
const fetchSequenceByPosition = async () => {
  if (!genomeAssembly.value || !genomePosition.chromosome.trim() || !genomePosition.start || !genomePosition.end) {
    error.value = t('please_fill_in_complete_genome_position_information')
    return
  }
  
  isFetching.value = true
  error.value = null
  
  try {
    // Call genome position sequence fetch API - 娴ｈ法鏁ゅ鍙夋箒閻?extract_seq_gff API
    const response = await httpInstance.post('/CottonOGD_api/extract_seq_gff/', {
      genome_id: genomeAssembly.value,
      seqid: genomePosition.chromosome.trim(),
      start: genomePosition.start,
      end: genomePosition.end,
      strand: '+' // 姒涙顓绘稉鐑橆劀闁?
    })
    
    if (response.sequence) {
      // Fill sequence into template
      sequenceTemplate.value = response.sequence
      // Update store
      primerDesignStore.setSequence('', response.sequence)
    } else {
      error.value = response.error || t('sequence_not_found_at_this_position_or_empty')
    }
  } catch (err) {
    error.value = t('failed_to_fetch_sequence') + ': ' + (err.message || t('unknown_error'))
    console.error('Failed to fetch sequence by genome position:', err)
  } finally {
    isFetching.value = false
  }
}

// Use directly input sequence
const useDirectSequence = () => {
  if (!directSequence.value.trim()) {
    error.value = t('please_enter_sequence')
    return
  }
  
  // Remove possible spaces
  sequenceTemplate.value = directSequence.value.trim().replace(/\s/g, '')
  // Update store
  primerDesignStore.sequenceTemplate = sequenceTemplate.value
}

// Design primers function
const designPrimers = async () => {
  console.log('designPrimers called')
  console.log('sequenceTemplate.value:', sequenceTemplate.value)
  console.log('sequenceTemplate.value.trim():', sequenceTemplate.value.trim())
  
  // Validate form
  if (!sequenceTemplate.value.trim()) {
    console.log('Sequence is empty, showing error')
    error.value = t('please_enter_dna_sequence')
    return
  }
  
  // Validate sequence length (max 5000 characters)
  const processedSequence = sequenceTemplate.value.trim().replace(/\s/g, '').toUpperCase().replace(/[^ACTG]/g, '')
  if (processedSequence.length > 5000) {
    console.log('Sequence is too long')
    error.value = `Sequence is too long (max 5000 characters, got ${processedSequence.length})`
    return
  }
  
  console.log('Starting primer design...')
  console.log('Processed sequence length:', processedSequence.length)
  
  // Clear previous results before starting new design
  designResults.value = []
  error.value = null
  
  // Set loading state
  isLoading.value = true
  
  try {
    const requestData = {
      sequence_id: sequenceId.value.trim() || 'default_id',
      sequence: processedSequence,
      parameters: {
        productSizeMin: parameters.value.productSizeMin,
        productSizeMax: parameters.value.productSizeMax,
        primerSizeMin: parameters.value.primerSizeMin,
        primerSizeMax: parameters.value.primerSizeMax,
        primerTmMin: parameters.value.primerTmMin,
        primerTmMax: parameters.value.primerTmMax,
        primerGCMin: parameters.value.primerGCMin,
        primerGCMax: parameters.value.primerGCMax
      }
    }
    
    console.log('requestData:', requestData)
    const response = await httpInstance.post('/CottonOGD_api/primer_design/', requestData)
    console.log('response:', response)
    if (response.status === 'success') {
      // Save results to store
      primerDesignStore.setDesignResults(response.results)
      designResults.value = response.results
    } else {
      error.value = response.error || t('design_failed')
    }
  } catch (err) {
    error.value = t('api_request_failed') + ': ' + (err.message || t('unknown_error'))
    console.error('Failed to design primers:', err)
  } finally {
    isLoading.value = false
  }
}

// Download results as Excel
const downloadResults = () => {
  console.log('Downloading results...')
  
  if (designResults.value.length === 0) {
    error.value = t('no_data_available_for_download')
    return
  }
  
  // Create CSV content
  let csvContent = 'Oligos,TM,GC%,Self any,Self end,Hairpin,Sequence,Penalty\n'
  
  // Add data rows
  designTableData.value.forEach(item => {
    csvContent += `${item.oligos},${item.tm},${item.gcPercent},${item.selfAny},${item.selfEnd},${item.hairpin},${item.sequence},${item.penalty}\n`
  })
  
  // Add BOM鏍囪锛岃В鍐矱xcel鎵撳紑涓枃涔辩爜闂
  const bom = new Uint8Array([0xEF, 0xBB, 0xBF])
  const blob = new Blob([bom, csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `primer_design_results_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}
</script>

<style scoped>
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.mt-6 {
  margin-top: 2.5rem;
}

.mb-6 {
  margin-bottom: 2.5rem;
}

.page-title {
  font-size: 32px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e9ecef;
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  padding: 15px 0;
}

.form-item-spacing {
  margin-bottom: 20px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  min-height: 300px;
}

.results-container {
  padding: 20px 0;
}

.results-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 20px;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  min-height: 300px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #dee2e6;
}

.empty-container p {
  font-size: 16px;
  color: #666;
  text-align: center;
  max-width: 500px;
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

.mt-3 {
  margin-top: 1rem;
}

.is-loading {
  font-size: 32px;
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

/* 閸濆秴绨插蹇氼啎鐠?*/
@media (max-width: 1200px) {
  .container {
    max-width: 100%;
  }
}

@media (max-width: 992px) {
  .el-row {
    flex-direction: column;
  }
  
  .el-col {
    width: 100% !important;
    margin-bottom: 20px;
  }
  
  .page-title {
    font-size: 28px;
  }
}

@media (max-width: 768px) {
  .mt-6 {
    margin-top: 1.5rem;
  }
  
  .mb-6 {
    margin-bottom: 1.5rem;
  }
  
  .page-title {
    font-size: 24px;
    margin-bottom: 20px;
  }
  
  .card-header {
    font-size: 18px;
  }
  
  .form-item-spacing {
    margin-bottom: 15px;
  }
  
  .loading-container,
  .empty-container {
    padding: 40px 15px;
    min-height: 200px;
  }
}
</style>

