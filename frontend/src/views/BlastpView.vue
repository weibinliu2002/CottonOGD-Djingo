<script setup lang="ts">
import { ref, inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Refresh } from '@element-plus/icons-vue'
import { v4 as uuidv4 } from 'uuid'
import { useGenomeStore } from '@/stores/genome_info'
import  httpInstance  from '@/utils/http'
// 注入全局loading状态管理方法
const showLoading = inject('showLoading') as () => void
const hideLoading = inject('hideLoading') as () => void

const router = useRouter()
const sequence = ref('')
const evalue = ref(0.01)
const maxTargetSeqs = ref(30)
const error = ref('')

// Blast类型选项
type BlastType = 'blastp' | 'blastn' | 'blastx' | 'tblastn' | 'tblastx'
const blastTypes = [
  { value: 'blastp', label: 'BLASTP', description: 'Protein-protein BLAST: Compares an amino acid query sequence against a protein sequence database.' },
  { value: 'blastn', label: 'BLASTN', description: 'Nucleotide-nucleotide BLAST: Compares a nucleotide query sequence against a nucleotide sequence database.' },
  { value: 'blastx', label: 'BLASTX', description: 'Translated query protein-nucleotide BLAST: Compares a nucleotide query sequence translated in all reading frames against a protein sequence database.' },
  { value: 'tblastn', label: 'TBLASTN', description: 'Protein-nucleotide translated BLAST: Compares a protein query sequence against a nucleotide sequence database dynamically translated in all reading frames.' },
  { value: 'tblastx', label: 'TBLASTX', description: 'Translated query-translated database BLAST: Compares a nucleotide query sequence translated in all reading frames against a nucleotide sequence database dynamically translated in all reading frames.' }
]
const selectedBlastType = ref<BlastType>('blastp')

// 数据库类型选项
type DatabaseType = 'genome' | 'cds' | 'mrna' | 'protein'
const databaseTypes = {
  blastp: [{ value: 'protein', label: 'Protein' }],
  blastn: [
    { value: 'genome', label: 'Genome' },
    { value: 'cds', label: 'CDS' },
    { value: 'mrna', label: 'mRNA' }
  ],
  blastx: [
    { value: 'protein', label: 'Protein' }
  ],
  tblastn: [
    { value: 'genome', label: 'Genome' },
    { value: 'cds', label: 'CDS' },
    { value: 'mrna', label: 'mRNA' }
  ],
  tblastx: [
    { value: 'genome', label: 'Genome' },
    { value: 'cds', label: 'CDS' },
    { value: 'mrna', label: 'mRNA' }
  ]
}
const selectedDatabaseType = ref<DatabaseType>('genome')

// 获取当前选中blast类型的介绍
const getCurrentBlastDescription = () => {
  const currentType = blastTypes.find(type => type.value === selectedBlastType.value)
  return currentType ? currentType.description : ''
}

// 基因组选择
const genomeStore = useGenomeStore()
const selectedGenomes = ref<string[]>([])

onMounted(() => {
  // 加载基因组数据
  genomeStore.fetchGenomes().then(() => {
    // 设置默认基因组 - 直接指定为G.hirsutumAD1_TM-1_HAU_v1.1
    const defaultGenome = 'G.hirsutumAD1_TM-1_HAU_v1.1'
    let found = false
    
    // 遍历所有基因组组
    for (const group of genomeStore.genomeOptions) {
      if (group && group.children) {
        // 遍历组内的所有基因组
        for (const genome of group.children) {
          if (genome && genome.value === defaultGenome) {
            selectedGenomes.value = [defaultGenome]
            found = true
            break
          }
        }
        if (found) break
      }
    }
    
    // 如果没有找到指定的基因组，选择第一个可用的基因组
    if (!found && genomeStore.genomeOptions.length > 0) {
      const firstGroup = genomeStore.genomeOptions[0]
      if (firstGroup && firstGroup.children && firstGroup.children.length > 0) {
        const firstChild = firstGroup.children[0] as { value: string }
        if (firstChild && firstChild.value) {
          selectedGenomes.value = [firstChild.value]
        }
      }
    }
  })
})

const exampleSequence = "MGEAIKKQEGVSTVKEDNKLIDSKKKKANNSNLAKKTSWRRIDLMATKNQRNDDSSTRKRKSSEGEFDMCGIEVAYEDELKRLKQEGKEDRDECKVKNPDKSLISAYIHDIQQLLVKYRKCRFEYIPPMENNLAHILATETLKNKKEFYLVGSVPKSAEKKEERDRVREPD"

const fillExample = () => {
  sequence.value = exampleSequence
}
console.log('exampleSequence:', exampleSequence);

const handleSubmit = async () => {
  if (!sequence.value.trim()) {
    error.value = 'Please enter a sequence'
    return
  }
  
  error.value = ''
  console.log('Submitting BLAST search:', {
    sequence: sequence.value,
    evalue: evalue.value,
    maxTargetSeqs: maxTargetSeqs.value,
    blastType: selectedBlastType.value,
    selectedGenomes: selectedGenomes.value,
    databaseType: selectedDatabaseType.value
  })
  
  // 显示全局加载状态
  showLoading()
  
  try {
    // 创建FormData对象来发送表单数据
    const formData = new FormData()
    formData.append('sequence', sequence.value)
    formData.append('evalue', evalue.value.toString())
    formData.append('max_target_seqs', maxTargetSeqs.value.toString())
    formData.append('blast_type', selectedBlastType.value)
    formData.append('selected_genomes', selectedGenomes.value.join(','))
    formData.append('database_type', selectedDatabaseType.value)
    
    // 构建完整的API URL
    const apiUrl = `/tools/${selectedBlastType.value}/api/${selectedBlastType.value}/`
    console.log('API URL:', apiUrl)
    
    // 添加详细的请求日志
    console.log('FormData entries:')
    for (const [key, value] of formData.entries()) {
      console.log(`${key}: ${value}`)
    }
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      body: formData,
      headers: {
        'Accept': 'application/json'
      }
    })
    
    // 添加响应日志
    console.log('Response status:', response.status)
    console.log('Response statusText:', response.statusText)
    console.log('Response headers:', Object.fromEntries(response.headers.entries()))
    
    // 检查响应是否成功
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Response error text:', errorText)
      throw new Error(`HTTP error! status: ${response.status}, text: ${errorText}`)
    }
    
    const results = await response.json()
    
    // 将结果传递给结果页面
    router.push({
      name: 'blastpResults',
      query: {
        results: encodeURIComponent(JSON.stringify(results))
      }
    })
    
  } catch (err) {
    error.value = 'BLAST search failed. Please try again. ' + (err as Error).message
    console.error('BLAST error:', err)
    console.error('Error details:', JSON.stringify(err, Object.getOwnPropertyNames(err)))
  } finally {
    // 隐藏全局加载状态
    hideLoading()
  }
}

const handleReset = () => {
  sequence.value = ''
  evalue.value = 0.01
  maxTargetSeqs.value = 30
  error.value = ''
  selectedBlastType.value = 'blastp'
  selectedGenomes.value = ['G.hirsutumAD1_TM-1_HAU_v1.1']
  selectedDatabaseType.value = 'genome'
}
</script>

<template>
  <div class="container mt-4">
    <h2 class="mb-4">BLAST Search</h2>
    
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      show-icon
      class="mb-4"
    />
    
    <el-card class="mb-4">
      <!-- Blast类型选择 -->
      <el-tabs v-model="selectedBlastType" class="mb-4">
        <el-tab-pane
          v-for="type in blastTypes"
          :key="type.value"
          :label="type.label"
          :name="type.value"
        />
      </el-tabs>
      
      <!-- Blast类型介绍 -->
      <el-card type="info" shadow="never" class="mb-4">
        {{ getCurrentBlastDescription() }}
      </el-card>
      
      <el-form @submit.prevent="handleSubmit" label-width="160px">
        <!-- 序列输入 -->
        <el-form-item label="Sequence">
          <el-input
            type="textarea"
            :rows="10"
            v-model="sequence"
            :placeholder="selectedBlastType === 'blastp' || selectedBlastType === 'blastx' ? 'Please enter a protein sequence' : 'Please enter a nucleotide sequence'"
          />
          <div class="mt-2">
            <el-button type="info" size="small" @click="fillExample">
              Load Example
            </el-button>
          </div>
        </el-form-item>
        
        <!-- 基因组选择 -->
        <el-form-item label="Select Genomes">
          <el-select
            v-model="selectedGenomes"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="Select genomes or genome categories"
            :loading="genomeStore.loading"
            class="w-full"
            :collapse-tags="true"
            :collapse-tags-tooltip="true"
            max-collapse-tags="3"
          >
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
        </el-form-item>
        
        <!-- 参数设置 -->
        <el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="E-value threshold">
                <el-input
                  type="number"
                  v-model.number="evalue"
                  :step="0.01"
                  :min="0"
                  placeholder="E-value"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Maximum target sequences">
                <el-input
                  type="number"
                  v-model.number="maxTargetSeqs"
                  :min="1"
                  :max="50"
                  placeholder="Max sequences"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form-item>
        
        <!-- 提交按钮 -->
        <el-form-item>
          <el-button type="primary" native-type="submit">
            <el-icon><Search /></el-icon>
            Search
          </el-button>
          <el-button type="default" @click="handleReset" class="ml-2">
            <el-icon><Refresh /></el-icon>
            Reset
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>



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

.ml-2 {
  margin-left: 0.5rem;
}

.card-header {
  font-size: 16px;
  font-weight: 500;
}
</style>