<template>
  <div class="container">
    <h1>{{ t('gene_expression_in_efp') }}</h1>

    <div class="input-group">
      <input 
        type="text" 
        id="gene_id" 
        v-model="geneId"
        :placeholder="t('please_enter_gene_id')" 
        autocomplete="off"
      >
      <select 
        v-model="selectedGenome" 
        class="genome-select"
        :disabled="loadingGenomes"
      >
        <template v-for="genomeType in filteredGenomeOptions" :key="genomeType.value">
          <optgroup 
            v-if="genomeType.children && genomeType.children.length > 0"
            :label="genomeType.label"
          >
            <option 
              v-for="genome in genomeType.children" 
              :key="genome.value"
              :value="genome.value"
            >
              {{ genome.label }}
            </option>
          </optgroup>
        </template>
      </select>
      <button 
        type="button" 
        class="btn btn-sm btn-outline-secondary mt-2" 
        id="fillExample"
        @click="fillExample"
      >
        {{ t('load_example') }}
      </button>
      <button 
        @click="generateImage" 
        id="generate-btn"
        :disabled="isLoading"
      >
        {{ t('generate_heatmap') }}
      </button>
      <span class="loading" id="loading" v-if="isLoading">{{ t('generating_heatmap') }}</span>
    </div>

    <!-- Color Picker -->
    <div class="color-picker-group">
      <div class="color-picker">
        <label for="low-color">{{ t('low_value') }}:</label>
        <input 
          type="color" 
          id="low-color" 
          v-model="lowColor" 
          class="color-input"
          @change="updateColorBox"
          data-type="low"
        >
        <div 
          class="color-box" 
          :style="{ backgroundColor: lowColor }"
          @click="triggerColorInput('low')"
        ></div>
      </div>
      <div class="color-picker">
        <label for="mid-color">{{ t('middle_value') }}:</label>
        <input 
          type="color" 
          id="mid-color" 
          v-model="midColor" 
          class="color-input"
          @change="updateColorBox"
          data-type="mid"
        >
        <div 
          class="color-box" 
          :style="{ backgroundColor: midColor }"
          @click="triggerColorInput('mid')"
        ></div>
      </div>
      <div class="color-picker">
        <label for="high-color">{{ t('high_value') }}:</label>
        <input 
          type="color" 
          id="high-color" 
          v-model="highColor" 
          class="color-input"
          @change="updateColorBox"
          data-type="high"
        >
        <div 
          class="color-box" 
          :style="{ backgroundColor: highColor }"
          @click="triggerColorInput('high')"
        ></div>
      </div>
    </div>

    <div id="result">
      <img 
        v-if="showResultImage" 
        :src="resultImage" 
        alt="Heatmap" 
        id="result-image"
        @load="onImageLoad"
      >
      <img 
        v-else
        src="/src/assets/images/egg.jpg" 
        alt="Initial" 
        id="initial-image"
      >
      
      <!-- 图像映射 -->
      <map name="result-map" v-if="mappedRegions.length > 0">
        <area 
          v-for="(region, index) in mappedRegions" 
          :key="index"
          shape="poly"
          :coords="region.coords"
          :title="region.title"
          @mouseenter="(e) => showTooltip(e, region)"
          @mousemove="moveTooltip"
          @mouseleave="hideTooltip"
        >
      </map>
      
      <!-- Tooltip -->
      <div 
        v-if="tooltipVisible" 
        class="tooltip"
        :style="{ left: tooltipStyle.left, top: tooltipStyle.top }"
      >
        <div class="tooltip-title">{{ tooltipContent.name }}</div>
        <div class="tooltip-value">{{ tooltipContent.value }}</div>
      </div>
    </div>

    <div v-if="message" :class="messageType" id="message">
      {{ message }}
    </div>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" target=".container" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, inject, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import httpInstance from '../utils/http'

const { t } = useI18n()
const route = useRoute()
const showLoading = inject<(() => void) | undefined>('showLoading', undefined)
const hideLoading = inject<(() => void) | undefined>('hideLoading', undefined)
const { genomeStore, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector('G.hirsutumAD1_Jin668_HAU_v1T2T')

const geneId = ref('')
const selectedGenome = ref('')
const lowColor = ref('#0000FF')
const midColor = ref('#00FF00')
const highColor = ref('#FF0000')
const isLoading = ref(false)
const resultImage = ref('')
const showResultImage = ref(false)
const message = ref('')
const messageType = ref('')
const currentRegionsInfo = ref<any[]>([])
const currentImageSize = ref({ width: 0, height: 0 })
const mappedRegions = ref<any[]>([])
const tooltipVisible = ref(false)
const tooltipContent = ref({ name: '', value: '' })
const tooltipStyle = ref({ left: '0px', top: '0px' })
const genomesWithTissue = ref<string[]>([])
const loadingGenomes = ref(false)

// 从后端获取有tissue数据的基因组列表
const fetchGenomesWithTissue = async () => {
  try {
    loadingGenomes.value = true
    const response = await httpInstance.get('/CottonOGD_api/extract_expression/genomes/')
    if (response && Array.isArray(response)) {
      genomesWithTissue.value = response
    }
  } catch (err) {
    console.error('Failed to fetch genomes with tissue:', err)
  } finally {
    loadingGenomes.value = false
  }
}

// 计算属性：筛选后的基因组选项
const filteredGenomeOptions = computed(() => {
  if (!genomesWithTissue.value.length) return genomeStore.genomeOptions
  
  return genomeStore.genomeOptions.map((group: any) => {
    // 筛选有tissue数据的子选项
    const filteredChildren = group.children?.filter((child: any) => 
      genomesWithTissue.value.includes(child.value)
    ) || []
    
    // 如果该组有子选项被筛选出来，返回该组
    if (filteredChildren.length > 0) {
      return {
        ...group,
        children: filteredChildren
      }
    }
    return null
  }).filter(Boolean)
})

// 填充示例基因ID
const fillExample = () => {
  const exampleIDs = 'Ghjin_A01g000040'
  geneId.value = exampleIDs
}

// Generate heatmap
const generateImage = () => {
  showLoading?.()
  if (!geneId.value.trim()) {
    showMessage('Please enter gene ID', 'error')
    hideLoading?.()
    return
  }
  
  isLoading.value = true
  showResultImage.value = false
  hideMessage()
  
  const data = {
    'gene_id': geneId.value.trim(),
    'genome_id': selectedGenome.value,
    'low_color': lowColor.value,
    'mid_color': midColor.value,
    'high_color': highColor.value
  }
  console.log('Request data:', data)
  console.log('selectedGenome.value:', selectedGenome.value)
  console.log('typeof selectedGenome.value:', typeof selectedGenome.value)
  
  const csrfToken = getCookie('csrftoken')
  fetch('/CottonOGD_api/expression_EFP_image/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken || ''
    },
    body: JSON.stringify(data)
  })
  .then(response => {
    if (!response.ok) {
      return response.text().then(text => {
        throw new Error(`HTTP error ${response.status}`)
      })
    }
    return response.json()
  })
  .then(data => {
    console.log('Response data:', data)
    console.log('typeof data:', typeof data)
    // Try to get image field directly, not dependent on success field
    if (data.image) {
      console.log('Found image in response:', data.image)
      currentRegionsInfo.value = data.regions_info || []
      currentImageSize.value = {
        width: data.image_width || 0,
        height: data.image_height || 0
      }
      
      resultImage.value = data.image
      showResultImage.value = true
    } else if (data.error) {
      console.log('Error response:', data.error)
      showMessage('Error: ' + data.error, 'error')
    } else {
      console.log('Unexpected response format:', data)
      showMessage('Error: Invalid response format', 'error')
    }
  })
  .catch(error => {
    showMessage('Request failed: ' + error.message, 'error')
  })
  .finally(() => {
    isLoading.value = false
    hideLoading?.()
  })
}

const onImageLoad = () => {
  if (currentRegionsInfo.value.length > 0 && currentImageSize.value.width > 0) {
    createImageMap()
  }
}

// 创建图像映射
const createImageMap = () => {
  const imgElement = document.getElementById('result-image') as HTMLImageElement
  if (!imgElement || !imgElement.complete || imgElement.naturalWidth === 0) {
    return
  }
  
  const displayWidth = imgElement.offsetWidth
  const displayHeight = imgElement.offsetHeight
  
  // 计算缩放比例
  const scaleX = currentImageSize.value.width > 0 ? displayWidth / currentImageSize.value.width : 1
  const scaleY = currentImageSize.value.height > 0 ? displayHeight / currentImageSize.value.height : 1
  
  console.log('Processing regions_info:', currentRegionsInfo.value)
  console.log('Number of regions:', currentRegionsInfo.value.length)
  
  mappedRegions.value = currentRegionsInfo.value
    .filter((region: any) => {
      // 过滤掉无效的区域数据
      const validRegion = region && region.polygon && Array.isArray(region.polygon) && region.polygon.length >= 3
      if (!validRegion) {
        console.log('Skipping invalid region:', region)
      }
      return validRegion
    })
    .map((region: any) => {
      try {
        const scaledCoords = region.polygon.map((point: any) => {
          if (Array.isArray(point) && point.length === 2) {
            return [
              Math.round(point[0] * scaleX),
              Math.round(point[1] * scaleY)
            ]
          }
          return [0, 0]
        })
        
        const coordsString = scaledCoords.map((point: any) => `${point[0]},${point[1]}`).join(',')
        
        return {
          coords: coordsString,
          name: region.name || 'Unknown Region',
          title: `${region.name || 'Unknown Region'}: ${typeof region.value === 'number' ? region.value.toFixed(4) : region.value || 'N/A'}`,
          value: region.value
        }
      } catch (error) {
        console.error('Error processing region:', error, region)
        return {
          coords: '',
          name: region.name || 'Error Region',
          title: 'Error processing region',
          value: 'Error'
        }
      }
    })
  
  console.log('Generated mappedRegions:', mappedRegions.value)
  console.log('Number of mapped regions:', mappedRegions.value.length)
}

const showTooltip = (event: any, region: any) => {
  let valueDisplay: string
  
  if (typeof region.value === 'number') {
    valueDisplay = region.value.toFixed(4)
  } else {
    valueDisplay = region.value
  }
  
  tooltipContent.value = {
    name: region.name,
    value: valueDisplay
  }
  tooltipVisible.value = true
  moveTooltip(event)
}

const moveTooltip = (event: any) => {
  const img = document.getElementById('result-image') as HTMLImageElement
  if (!img || !img.complete || img.naturalWidth === 0) {
    return
  }
  
  const imgRect = img.getBoundingClientRect()
  const containerRect = img.parentElement?.getBoundingClientRect()
  if (!containerRect) return
  
  const x = event.clientX - containerRect.left + 15
  const y = event.clientY - containerRect.top + 15
  
  tooltipStyle.value = {
    left: `${x}px`,
    top: `${y}px`
  }
}

const hideTooltip = () => {
  tooltipVisible.value = false
}

// 显示消息
const showMessage = (text: string, type: string) => {
  message.value = text
  messageType.value = type
}

// 隐藏消息
const hideMessage = () => {
  message.value = ''
}

// 获取cookie
const getCookie = (name: string): string | null => {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i]?.trim()
      if (cookie && cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

const updateColorBox = (event: any) => {
  const type = event.target.dataset.type
  if (type === 'low') {
    lowColor.value = event.target.value
  } else if (type === 'mid') {
    midColor.value = event.target.value
  } else if (type === 'high') {
    highColor.value = event.target.value
  }
  console.log(`Color updated: ${type} = ${event.target.value}`)
}

// 触发颜色输入
const triggerColorInput = (type: string) => {
  document.getElementById(`${type}-color`)?.click()
}

// 处理窗口大小变化
const handleResize = () => {
  if (showResultImage.value && currentRegionsInfo.value.length > 0) {
    createImageMap()
  }
}

// 组件挂载时加载基因组数据
onMounted(async () => {
  await ensureGenomesLoaded()
  await fetchGenomesWithTissue()
  selectedGenome.value = pickDefaultGenome()

  document.getElementById('gene_id')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      generateImage()
    }
  })

  window.addEventListener('resize', handleResize)
  
  // 处理URL参数，如果有gene_id和genome_id，自动执行请求
  const urlGeneId = route.query.gene_id as string
  const urlGenomeId = route.query.genome_id as string
  
  if (urlGeneId) {
    geneId.value = urlGeneId
    
    // 如果URL中有genome_id，优先使用
    if (urlGenomeId && genomesWithTissue.value.includes(urlGenomeId)) {
      selectedGenome.value = urlGenomeId
    }
    
    // 自动执行请求绘制图形
    generateImage()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
  h1 {
    color: #2c3e50;
    text-align: center;
    margin-bottom: 30px;
  }
  .input-group {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 30px;
    gap: 15px;
    flex-wrap: wrap;
  }
  .color-picker-group {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 20px;
    gap: 20px;
    flex-wrap: wrap;
  }
  .color-picker {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .color-picker label {
    font-weight: bold;
    min-width: 60px;
  }
  .color-box {
    width: 30px;
    height: 30px;
    border: 2px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
  }
  #gene_id {
    padding: 12px;
    border: 2px solid #ddd;
    border-radius: 5px;
    font-size: 16px;
    width: 300px;
  }
  #gene_id:focus {
    border-color: #3498db;
    outline: none;
  }
  .genome-select {
    padding: 12px;
    border: 2px solid #ddd;
    border-radius: 5px;
    font-size: 16px;
    background-color: white;
    cursor: pointer;
  }
  .genome-select:focus {
    border-color: #3498db;
    outline: none;
  }
  button {
    padding: 12px 24px;
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
    transition: background-color 0.3s;
  }
  button:hover {
    background-color: #2980b9;
  }
  button:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
  .loading {
    color: #3498db;
    font-weight: bold;
    margin-left: 15px;
  }
  #result {
    text-align: center;
    margin-top: 20px;
  }
  /* 修改图片相关样式 */
  .image-container {
    position: relative;
    display: block;
    text-align: center;
    width: 100%;
  }
  #result-image, #initial-image {
    max-width: 90%;
    border: 2px solid #ddd;
    border-radius: 5px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    display: block;
    margin: 0 auto;
  }
  #initial-image {
    margin: 0 auto 20px;
  }
  .error {
    color: #e74c3c;
    text-align: center;
    margin-top: 20px;
    padding: 15px;
    background-color: #fadbd8;
    border-radius: 5px;
    border: 1px solid #e74c3c;
  }
  .success {
    color: #27ae60;
    text-align: center;
    margin-top: 20px;
    padding: 15px;
    background-color: #d4edda;
    border-radius: 5px;
    border: 1px solid #27ae60;
  }
  .tooltip {
    position: absolute;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 14px;
    pointer-events: none;
    z-index: 1000;
    max-width: 200px;
  }
  .tooltip-title {
    font-weight: bold;
    margin-bottom: 4px;
  }
  .tooltip-value {
    color: #3498db;
  }
</style>
