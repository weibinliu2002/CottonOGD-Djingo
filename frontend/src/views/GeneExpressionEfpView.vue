<template>
  <div class="container">
    <h1>Gene Expression in eFP</h1>

    <div class="input-group">
      <input 
        type="text" 
        id="gene_id" 
        v-model="geneId"
        placeholder="Please enter gene ID, e.g.: Gh_A01G0001" 
        autocomplete="off"
      >
      <select 
        v-model="selectedGenome" 
        class="genome-select"
      >
        <template v-for="genomeType in genomeStore.genomeOptions" :key="genomeType.value">
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
        load example
      </button>
      <button 
        @click="generateImage" 
        id="generate-btn"
        :disabled="isLoading"
      >
        Generate Heatmap
      </button>
      <span class="loading" id="loading" v-if="isLoading">Generating heatmap...</span>
    </div>

    <!-- Color Picker -->
    <div class="color-picker-group">
      <div class="color-picker">
        <label for="low-color">Low value:</label>
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
        <label for="mid-color">Middle value:</label>
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
        <label for="high-color">High value:</label>
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
    
    <!-- Initial Image -->
    <img 
      id="initial-image" 
      src="../assets/images/egg.jpg" 
      alt="Initial heatmap template" 
      v-if="!showResultImage"
      @error="hideInitialImage"
    >
    <div id="message" v-if="message" :class="messageType">{{ message }}</div>
    
    <div id="result">
      <div class="image-container">
        <img 
          id="result-image" 
          :src="resultImage" 
          alt="Heatmap result" 
          usemap="#regionMap"
          v-if="showResultImage"
          @load="onImageLoad"
        >
        <map name="regionMap" id="regionMap">
          <area 
            v-for="(region, index) in mappedRegions" 
            :key="index"
            shape="poly"
            :coords="region.coords"
            :alt="region.name"
            :title="region.title"
            @mouseenter="showTooltip($event, region)"
            @mousemove="moveTooltip($event)"
            @mouseleave="hideTooltip"
          />
        </map>
        <div 
          id="tooltip" 
          class="tooltip" 
          v-if="tooltipVisible"
          :style="tooltipStyle"
        >
          <strong>{{ tooltipContent.name }}</strong><br>
          Expression value: {{ tooltipContent.value }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useGenomeStore } from '@/stores/genome_info'

export default {
  name: 'GeneExpressionEfpView',
  setup() {
    const genomeStore = useGenomeStore()
    const geneId = ref('')
    const selectedGenome = ref('G.hirsutumAD1_Jin668_HAU_v1T2T')
    const lowColor = ref('#0000FF')
    const midColor = ref('#00FF00')
    const highColor = ref('#FF0000')
    const isLoading = ref(false)
    const resultImage = ref('')
    const showResultImage = ref(false)
    const message = ref('')
    const messageType = ref('')
    const currentRegionsInfo = ref([])
    const currentImageSize = ref({ width: 0, height: 0 })
    const mappedRegions = ref([])
    const tooltipVisible = ref(false)
    const tooltipContent = ref({ name: '', value: '' })
    const tooltipStyle = ref({ left: '0px', top: '0px' })
    
    // 组件挂载时加载基因组数据
    onMounted(() => {
      console.log('Initial genomeOptions:', genomeStore.genomeOptions);
      console.log('Initial genomeStore error:', genomeStore.error);
      if (genomeStore.genomeOptions.length === 0) {
        console.log('Fetching genomes...');
        genomeStore.fetchGenomes().then(() => {
          console.log('Genomes fetched successfully:', genomeStore.genomeOptions);
          console.log('GenomeStore error after fetch:', genomeStore.error);
          // 如果仍然没有数据，添加一些测试数据
          if (genomeStore.genomeOptions.length === 0) {
            console.log('Adding test genome data...');
            genomeStore.genomeOptions = [
              {
                value: 'AD1',
                label: 'AD1',
                children: [
                  { value: 'G.hirsutumAD1_Jin668_HAU_v1T2T', label: 'G.hirsutumAD1_Jin668_HAU_v1T2T' },
                  { value: 'G.hirsutumAD1_TM1_NBI_v2.1', label: 'G.hirsutumAD1_TM1_NBI_v2.1' }
                ]
              },
              {
                value: 'D5',
                label: 'D5',
                children: [
                  { value: 'G.raimondiiD5_JGI_v2.1', label: 'G.raimondiiD5_JGI_v2.1' }
                ]
              }
            ];
            console.log('Test genome data added:', genomeStore.genomeOptions);
            // 确保 selectedGenome 被设置为默认值
            if (!selectedGenome.value) {
              selectedGenome.value = 'G.hirsutumAD1_Jin668_HAU_v1T2T';
              console.log('Set selectedGenome to default value:', selectedGenome.value);
            }
          }
        }).catch((error) => {
          console.error('Error fetching genomes:', error);
          // 如果请求失败，添加一些测试数据
          console.log('Adding test genome data due to error...');
          genomeStore.genomeOptions = [
            {
              value: 'AD1',
              label: 'AD1',
              children: [
                { value: 'G.hirsutumAD1_Jin668_HAU_v1T2T', label: 'G.hirsutumAD1_Jin668_HAU_v1T2T' },
                { value: 'G.hirsutumAD1_TM1_NBI_v2.1', label: 'G.hirsutumAD1_TM1_NBI_v2.1' }
              ]
            },
            {
              value: 'D5',
              label: 'D5',
              children: [
                { value: 'G.raimondiiD5_JGI_v2.1', label: 'G.raimondiiD5_JGI_v2.1' }
              ]
            }
          ];
          console.log('Test genome data added:', genomeStore.genomeOptions);
          // 确保 selectedGenome 被设置为默认值
          if (!selectedGenome.value) {
            selectedGenome.value = 'G.hirsutumAD1_Jin668_HAU_v1T2T';
            console.log('Set selectedGenome to default value:', selectedGenome.value);
          }
        });
      }
      
      // 支持回车键提交
      document.getElementById('gene_id').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          generateImage();
        }
      });

      // 窗口大小变化时重新计算坐标
      window.addEventListener('resize', handleResize);
    })
    
    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize);
    })
    
    // 填充示例基因ID
    const fillExample = () => {
      const exampleIDs = 'Ghjin_A01g000040';
      geneId.value = exampleIDs;
    }
    
    // Generate heatmap
    const generateImage = () => {
      if (!geneId.value.trim()) {
        showMessage('Please enter gene ID', 'error');
        return;
      }
      
      isLoading.value = true;
      showResultImage.value = false;
      hideMessage();
      
      const data = {
        'gene_id': geneId.value.trim(),
        'genome_id': selectedGenome.value,
        'low_color': lowColor.value,
        'mid_color': midColor.value,
        'high_color': highColor.value
      };
      console.log('Request data:', data);
      console.log('selectedGenome.value:', selectedGenome.value);
      console.log('typeof selectedGenome.value:', typeof selectedGenome.value);
      
      fetch('/CottonOGD_api/expression_EFP_image/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
      })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => {
            throw new Error(`HTTP error ${response.status}`);
          });
        }
        return response.json();
      })
      .then(data => {
        console.log('Response data:', data);
        console.log('typeof data:', typeof data);
        // Try to get image field directly, not dependent on success field
        if (data.image) {
          console.log('Found image in response:', data.image);
          currentRegionsInfo.value = data.regions_info || [];
          currentImageSize.value = {
            width: data.image_width || 0,
            height: data.image_height || 0
          };
          
          resultImage.value = data.image;
          showResultImage.value = true;
        } else if (data.error) {
          console.log('Error response:', data.error);
          showMessage('Error: ' + data.error, 'error');
        } else {
          console.log('Unexpected response format:', data);
          showMessage('Error: Invalid response format', 'error');
        }
      })
      .catch(error => {
        showMessage('Request failed: ' + error.message, 'error');
      })
      .finally(() => {
        isLoading.value = false;
      });
    }
    
    // 图片加载完成后创建图像映射
    const onImageLoad = () => {
      if (currentRegionsInfo.value.length > 0 && currentImageSize.value.width > 0) {
        createImageMap();
      }
    }
    
    // 创建图像映射
    const createImageMap = () => {
      const imgElement = document.getElementById('result-image');
      if (!imgElement || !imgElement.complete || imgElement.naturalWidth === 0) {
        return;
      }
      
      // 获取当前显示的图像尺寸
      const displayWidth = imgElement.offsetWidth;
      const displayHeight = imgElement.offsetHeight;
      
      // 计算缩放比例
      const scaleX = currentImageSize.value.width > 0 ? displayWidth / currentImageSize.value.width : 1;
      const scaleY = currentImageSize.value.height > 0 ? displayHeight / currentImageSize.value.height : 1;
      
      console.log('Processing regions_info:', currentRegionsInfo.value);
      console.log('Number of regions:', currentRegionsInfo.value.length);
      
      mappedRegions.value = currentRegionsInfo.value
        .filter(region => {
          // 过滤掉无效的区域数据
          const validRegion = region && region.polygon && Array.isArray(region.polygon) && region.polygon.length >= 3;
          if (!validRegion) {
            console.log('Skipping invalid region:', region);
          }
          return validRegion;
        })
        .map(region => {
          try {
            // 缩放坐标以适应显示的图像尺寸
            const scaledCoords = region.polygon.map(point => {
              if (Array.isArray(point) && point.length === 2) {
                return [
                  Math.round(point[0] * scaleX),
                  Math.round(point[1] * scaleY)
                ];
              }
              return [0, 0];
            });
            
            const coordsString = scaledCoords.map(point => `${point[0]},${point[1]}`).join(',');
            
            return {
              coords: coordsString,
              name: region.name || 'Unknown Region',
              title: `${region.name || 'Unknown Region'}: ${typeof region.value === 'number' ? region.value.toFixed(4) : region.value || 'N/A'}`,
              value: region.value
            };
          } catch (error) {
            console.error('Error processing region:', error, region);
            return {
              coords: '',
              name: region.name || 'Error Region',
              title: 'Error processing region',
              value: 'Error'
            };
          }
        });
      
      console.log('Generated mappedRegions:', mappedRegions.value);
      console.log('Number of mapped regions:', mappedRegions.value.length);
    }
    
    // 显示提示框
    const showTooltip = (event, region) => {
      let valueDisplay;
      
      if (typeof region.value === 'number') {
        valueDisplay = region.value.toFixed(4);
      } else {
        valueDisplay = region.value;
      }
      
      tooltipContent.value = {
        name: region.name,
        value: valueDisplay
      };
      tooltipVisible.value = true;
      moveTooltip(event);
    }
    
    // 移动提示框
    const moveTooltip = (event) => {
      const img = document.getElementById('result-image');
      if (!img || !img.complete || img.naturalWidth === 0) {
        return;
      }
      
      const imgRect = img.getBoundingClientRect();
      const containerRect = img.parentElement.getBoundingClientRect();
      const x = event.clientX - containerRect.left + 15;
      const y = event.clientY - containerRect.top + 15;
      
      tooltipStyle.value = {
        left: `${x}px`,
        top: `${y}px`
      };
    }
    
    // 隐藏提示框
    const hideTooltip = () => {
      tooltipVisible.value = false;
    }
    
    // 显示消息
    const showMessage = (text, type) => {
      message.value = text;
      messageType.value = type;
    }
    
    // 隐藏消息
    const hideMessage = () => {
      message.value = '';
    }
    
    // 隐藏初始图片
    const hideInitialImage = () => {
      // 错误处理
    }
    
    // 获取cookie
    const getCookie = (name) => {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
    
    // 更新颜色框
    const updateColorBox = (event) => {
      const type = event.target.dataset.type;
      if (type === 'low') {
        lowColor.value = event.target.value;
      } else if (type === 'mid') {
        midColor.value = event.target.value;
      } else if (type === 'high') {
        highColor.value = event.target.value;
      }
      console.log(`Color updated: ${type} = ${event.target.value}`);
    }
    
    // 触发颜色输入
    const triggerColorInput = (type) => {
      document.getElementById(`${type}-color`).click();
    }
    
    // 处理窗口大小变化
    const handleResize = () => {
      if (showResultImage.value && currentRegionsInfo.value.length > 0) {
        createImageMap();
      }
    }
    
    return {
      geneId,
      selectedGenome,
      lowColor,
      midColor,
      highColor,
      isLoading,
      resultImage,
      showResultImage,
      message,
      messageType,
      currentRegionsInfo,
      currentImageSize,
      mappedRegions,
      tooltipVisible,
      tooltipContent,
      tooltipStyle,
      genomeStore,
      fillExample,
      generateImage,
      onImageLoad,
      createImageMap,
      showTooltip,
      moveTooltip,
      hideTooltip,
      showMessage,
      hideMessage,
      hideInitialImage,
      getCookie,
      updateColorBox,
      triggerColorInput,
      handleResize
    }
  }
}
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
  }
  /* 添加提示框样式 */
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
    text-align: center;
  }
  .tooltip strong {
    color: #ffeb3b;
  }
  /* 区域悬停效果 */
  area:hover {
    cursor: pointer;
  }
  /* 确保地图元素居中 */
  map {
    display: block;
    margin: 0 auto;
  }
</style>