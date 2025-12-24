<template>
  <div class="container">
    <h1>gene_expression_in_eFP</h1>

    <div class="input-group">
      <input 
        type="text" 
        id="gene_id" 
        v-model="geneId"
        placeholder="请输入基因ID，例如: Gh_A01G0001" 
        autocomplete="off"
      >
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
        生成热图
      </button>
      <span class="loading" id="loading" v-if="isLoading">正在生成热图...</span>
    </div>
 
    <!-- 颜色选择器 -->
    <div class="color-picker-group">
      <div class="color-picker">
        <label for="low-color">低值:</label>
        <input 
          type="color" 
          id="low-color" 
          v-model="lowColor" 
          class="color-input"
          @change="updateColorBox($event, 'low')"
        >
        <div 
          class="color-box" 
          :style="{ backgroundColor: lowColor }"
          @click="triggerColorInput('low')"
        ></div>
      </div>
      <div class="color-picker">
        <label for="mid-color">中值:</label>
        <input 
          type="color" 
          id="mid-color" 
          v-model="midColor" 
          class="color-input"
          @change="updateColorBox($event, 'mid')"
        >
        <div 
          class="color-box" 
          :style="{ backgroundColor: midColor }"
          @click="triggerColorInput('mid')"
        ></div>
      </div>
      <div class="color-picker">
        <label for="high-color">高值:</label>
        <input 
          type="color" 
          id="high-color" 
          v-model="highColor" 
          class="color-input"
          @change="updateColorBox($event, 'high')"
        >
        <div 
          class="color-box" 
          :style="{ backgroundColor: highColor }"
          @click="triggerColorInput('high')"
        ></div>
      </div>
    </div>
    
    <!-- 初始图片 -->
    <img 
      id="initial-image" 
      src="../assets/images/egg.jpg" 
      alt="初始热图模板" 
      v-if="!showResultImage"
      @error="hideInitialImage"
    >
    <div id="message" v-if="message" :class="messageType">{{ message }}</div>
    
    <div id="result">
      <div class="image-container">
        <img 
          id="result-image" 
          :src="resultImage" 
          alt="热图结果" 
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
          表达值: {{ tooltipContent.value }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GeneExpressionEfpView',
  data() {
    return {
      geneId: '',
      lowColor: '#0000FF',
      midColor: '#00FF00',
      highColor: '#FF0000',
      isLoading: false,
      resultImage: '',
      showResultImage: false,
      message: '',
      messageType: '',
      currentRegionsInfo: [],
      currentImageSize: { width: 0, height: 0 },
      mappedRegions: [],
      tooltipVisible: false,
      tooltipContent: { name: '', value: '' },
      tooltipStyle: { left: '0px', top: '0px' }
    }
  },
  mounted() {
    // 支持回车键提交
    document.getElementById('gene_id').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.generateImage();
      }
    });

    // 窗口大小变化时重新计算坐标
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    fillExample() {
      const exampleIDs = 'Ghjin_A01g000040';
      this.geneId = exampleIDs;
    },
    generateImage() {
      if (!this.geneId.trim()) {
        this.showMessage('请输入基因ID', 'error');
        return;
      }
      
      this.isLoading = true;
      this.showResultImage = false;
      this.hideMessage();
      
      const data = {
        'gene_id': this.geneId.trim(),
        'low_color': this.lowColor,
        'mid_color': this.midColor,
        'high_color': this.highColor
      };
      
      fetch('/tools/gene_expression_in_eFP/generate-thermal-image/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken')
        },
        body: JSON.stringify(data)
      })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => {
            throw new Error(`HTTP错误 ${response.status}`);
          });
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          this.currentRegionsInfo = data.regions_info || [];
          this.currentImageSize = {
            width: data.image_width || 0,
            height: data.image_height || 0
          };
          
          this.resultImage = data.image;
          this.showResultImage = true;
        } else {
          this.showMessage('错误: ' + data.error, 'error');
        }
      })
      .catch(error => {
        this.showMessage('请求失败: ' + error.message, 'error');
      })
      .finally(() => {
        this.isLoading = false;
      });
    },
    onImageLoad() {
      if (this.currentRegionsInfo.length > 0 && this.currentImageSize.width > 0) {
        this.createImageMap();
      }
    },
    createImageMap() {
      const imgElement = document.getElementById('result-image');
      if (!imgElement || !imgElement.complete || imgElement.naturalWidth === 0) {
        return;
      }
      
      // 获取当前显示的图像尺寸
      const displayWidth = imgElement.offsetWidth;
      const displayHeight = imgElement.offsetHeight;
      
      // 计算缩放比例
      const scaleX = this.currentImageSize.width > 0 ? displayWidth / this.currentImageSize.width : 1;
      const scaleY = this.currentImageSize.height > 0 ? displayHeight / this.currentImageSize.height : 1;
      
      this.mappedRegions = this.currentRegionsInfo
        .filter(region => region.polygon && region.polygon.length >= 3)
        .map(region => {
          // 缩放坐标以适应显示的图像尺寸
          const scaledCoords = region.polygon.map(point => [
            Math.round(point[0] * scaleX),
            Math.round(point[1] * scaleY)
          ]);
          
          const coordsString = scaledCoords.map(point => `${point[0]},${point[1]}`).join(',');
          
          return {
            coords: coordsString,
            name: region.name,
            title: `${region.name}: ${typeof region.value === 'number' ? region.value.toFixed(4) : region.value}`,
            value: region.value
          };
        });
    },
    showTooltip(event, region) {
      let valueDisplay;
      
      if (typeof region.value === 'number') {
        valueDisplay = region.value.toFixed(4);
      } else {
        valueDisplay = region.value;
      }
      
      this.tooltipContent = {
        name: region.name,
        value: valueDisplay
      };
      this.tooltipVisible = true;
      this.moveTooltip(event);
    },
    moveTooltip(event) {
      const img = document.getElementById('result-image');
      if (!img || !img.complete || img.naturalWidth === 0) {
        return;
      }
      
      const imgRect = img.getBoundingClientRect();
      const containerRect = img.parentElement.getBoundingClientRect();
      const x = event.clientX - containerRect.left + 15;
      const y = event.clientY - containerRect.top + 15;
      
      this.tooltipStyle = {
        left: `${x}px`,
        top: `${y}px`
      };
    },
    hideTooltip() {
      this.tooltipVisible = false;
    },
    showMessage(text, type) {
      this.message = text;
      this.messageType = type;
    },
    hideMessage() {
      this.message = '';
    },
    hideInitialImage() {
      // 错误处理
    },
    getCookie(name) {
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
    },
    updateColorBox(event, type) {
      // 颜色更新处理
      if (type === 'low') {
        this.lowColor = event.target.value;
      } else if (type === 'mid') {
        this.midColor = event.target.value;
      } else if (type === 'high') {
        this.highColor = event.target.value;
      }
      console.log(`Color updated: ${type} = ${event.target.value}`);
    },
    triggerColorInput(type) {
      document.getElementById(`${type}-color`).click();
    },
    handleResize() {
      if (this.showResultImage && this.currentRegionsInfo.length > 0) {
        this.createImageMap();
      }
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