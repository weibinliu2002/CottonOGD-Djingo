<template>
  <div class="container mt-4">
    <h1>Search Results</h1>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="text-center py-5">
      <div class="spinner-border" role="status">
        <span class="visually-hidden">loading...</span>
      </div>
      <p class="mt-3">loading results...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="errorMessage" class="alert alert-danger mt-3">
        {{ errorMessage }}
        <router-link to="/tools/id-search" class="btn btn-primary btn-sm ml-2">new search</router-link>
      </div>
    
    <!-- 结果展示 -->
    <div v-else-if="result" class="mt-4">
      
      <!-- 基本信息卡片 -->
      <div class="card mb-4">
        <div class="card-header">
          <h2>Gene Basic Information</h2>
        </div>
        <div class="card-body">
          <table class="table table-bordered">
            <tbody>
              <tr>
                <td><strong>Gene ID:</strong></td>
                <td>{{ result.IDs }}</td>
              </tr>
              <tr>
                <td><strong>Chromosome:</strong></td>
                <td>{{ result.seqid }}</td>
              </tr>
              <tr>
                <td><strong>Start Position:</strong></td>
                <td>{{ result.start }}</td>
              </tr>
              <tr>
                <td><strong>End Position:</strong></td>
                <td>{{ result.end }}</td>
              </tr>
              <tr>
                <td><strong>Strand:</strong></td>
                <td>{{ result.strand }}</td>
              </tr>
              
            </tbody>
          </table>
        </div>
      </div>
      <div class="mb-4">
        <strong>JBrowse View:</strong>
        <div class="mt-2" v-if="jbrowse_url">
          <iframe :src="jbrowse_url" style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px;"></iframe>
        </div>
        <div v-else>
          JBrowse URL not available
        </div>
      </div>
      <!-- 序列信息卡片 -->
      <div v-if="has_sequences" class="card mb-4">
        <div class="card-header">
          <h2>Sequence</h2>
        </div>
        <div class="card-body">
            <!-- 转录本选择器 -->
            <div v-if="hasMultipleTranscripts" class="mb-4">
              <h4 class="h6 mb-2">Transcript Selector</h4>
              <select class="form-select w-auto" v-model="selectedTranscriptIndex" @change="switchTranscript(selectedTranscriptIndex)">
                <option v-for="(transcript, index) in result.mrna_transcripts" :key="index" :value="index">
                  {{ transcript.id }} (Protein Length: {{ transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== 'unavailable' && transcript.protein_seq !== '未找到蛋白序列' ? transcript.protein_seq.length : 'N/A' }} aa)
                </option>
              </select>
            </div>
            
            <!-- 转录本基因结构图 -->
            <div v-if="gffData.length > 0" class="mb-4">
              <h4 class="h6 mb-2">Transcript Structure</h4>
              <div class="gene-structure-container">
                <svg :width="svgWidth" height="150" class="gene-structure-svg">
                  <!-- 转录本名称 -->
                  <text x="20" y="20" font-size="12" font-weight="bold" fill="#333">
                    {{ currentTranscript ? currentTranscript.id : this.result.IDS }}
                  </text>
                  
                  <!-- 绘制基因结构元素 -->
                  <g v-if="currentTranscriptGffData.length > 0">
                    <!-- 绘制内含子（窄方框）和连接线 -->
                    <g v-for="(item, index) in currentTranscriptGffData" :key="'structure-' + index">
                      <template v-if="geneLength > 0">
                        <!-- 绘制当前结构元素 -->
                        <rect
                          v-if="item.type === 'CDS'"
                          :x="20 + (item.start - geneStart) * scale"
                          y="35"
                          :width="(item.end - item.start + 1) * scale"
                          height="50"
                          fill="#34A853"
                          stroke="#227A3D"
                          stroke-width="1"
                        />
                        <rect
                          v-else-if="item.type === 'five_prime_UTR'"
                          :x="20 + (item.start - geneStart) * scale"
                          y="45"
                          :width="(item.end - item.start + 1) * scale"
                          height="30"
                          fill="#FBBC05"
                          stroke="#F29900"
                          stroke-width="1"
                        />
                        <rect
                          v-else-if="item.type === 'three_prime_UTR'"
                          :x="20 + (item.start - geneStart) * scale"
                          y="45"
                          :width="(item.end - item.start + 1) * scale"
                          height="30"
                          fill="#EA4335"
                          stroke="#C5221F"
                          stroke-width="1"
                        />
                        
                        <!-- 绘制与下一个元素的连接线 -->
                        <line
                          v-if="index < currentTranscriptGffData.length - 1"
                          :x1="20 + (item.end - geneStart) * scale"
                          y1="60"
                          :x2="20 + (currentTranscriptGffData[index + 1].start - geneStart) * scale"
                          y2="60"
                          stroke="#333"
                          stroke-width="2"
                        />
                        
                        <!-- 绘制内含子（窄方框） -->
                        <rect
                          v-if="index < currentTranscriptGffData.length - 1"
                          :x="20 + (item.end - geneStart) * scale"
                          y="55"
                          :width="(currentTranscriptGffData[index + 1].start - item.end - 1) * scale"
                          height="10"
                          fill="#E0E0E0"
                          stroke="#BDBDBD"
                          stroke-width="1"
                        />
                      </template>
                    </g>
                    
                    <!-- 转录方向指示 -->
                    <g v-if="currentTranscriptGffData.length > 0">
                      <template v-if="geneLength > 0">
                        <!-- 箭头位置：基因结构的右侧 -->
                        <polygon
                          :points="[
                            20 + (currentTranscriptGffData[currentTranscriptGffData.length - 1].end - geneStart) * scale + 10,
                            60 - 10,
                            20 + (currentTranscriptGffData[currentTranscriptGffData.length - 1].end - geneStart) * scale + 20,
                            60,
                            20 + (currentTranscriptGffData[currentTranscriptGffData.length - 1].end - geneStart) * scale + 10,
                            60 + 10
                          ].join(',')"
                          fill="#333"
                        />
                        <text
                          :x="20 + (currentTranscriptGffData[currentTranscriptGffData.length - 1].end - geneStart) * scale + 25"
                          y="65"
                          font-size="12"
                          fill="#333"
                        >
                          Transcription Direction
                        </text>
                      </template>
                    </g>
                  </g>
                  
                  <!-- 基因范围标注 -->
                  <text x="20" y="110" font-size="10" fill="#666">
                    {{ geneStart }}
                  </text>
                  <text :x="svgWidth - 20" y="110" font-size="10" fill="#666" text-anchor="end">
                    {{ geneEnd }}
                  </text>
                  
                  <!-- 图注 -->
                  <g transform="translate(20, 130)">
                    <text font-size="11" font-weight="bold" fill="#333">Legend:</text>
                    <g transform="translate(50, 0)">
                      <rect x="0" y="-8" width="15" height="15" fill="#34A853" stroke="#227A3D" stroke-width="1" />
                      <text x="20" y="5" font-size="10" fill="#333">CDS</text>
                    </g>
                    <g transform="translate(120, 0)">
                      <rect x="0" y="-8" width="15" height="15" fill="#FBBC05" stroke="#F29900" stroke-width="1" />
                      <text x="20" y="5" font-size="10" fill="#333">5' UTR</text>
                    </g>
                    <g transform="translate(190, 0)">
                      <rect x="0" y="-8" width="15" height="15" fill="#EA4335" stroke="#C5221F" stroke-width="1" />
                      <text x="20" y="5" font-size="10" fill="#333">3' UTR</text>
                    </g>
                    <g transform="translate(260, 0)">
                      <rect x="0" y="-3" width="30" height="5" fill="#E0E0E0" stroke="#BDBDBD" stroke-width="1" />
                      <text x="35" y="5" font-size="10" fill="#333">Intron</text>
                    </g>
                  </g>
                </svg>
              </div>
            </div>
            
           <!-- 使用通用序列展示组件 -->
              <sequence-display
                display-mode="buttons"
                :gene_seq="result.gene_seq"
                :mrna_seq="result.mrna_seq"
                :upstream_seq="result.upstream_seq"
                :downstream_seq="result.downstream_seq"
                :cdna_seq="result.cdna_seq"
                :cds_seq="result.cds_seq"
                :protein_seq="result.protein_seq"
                :gene_id="result.IDs"
                :current-transcript="currentTranscript"
                :loading="isLoading"
                @show-sequence="handleShowSequence"
                @length-change="handleLengthChange"
              />
          
          <div class="mb-3">
            <button class="btn btn-success mr-2" @click="downloadAllSequences">Download All Sequences</button>
            <button v-if="hasMultipleTranscripts" class="btn btn-primary" @click="downloadCurrentTranscriptSequences">Download Current Transcript Sequences</button>
          </div>
        </div>
      </div>
      
      <!-- 注释信息卡片 -->
      <div v-if="annotations && Object.keys(annotations).length > 0" class="card mb-4">
        <div class="card-header">
          <h2>Annotations</h2>
        </div>
        <div class="card-body">
          <!-- GO注释 -->
          <div v-if="annotations.GO_annotation && annotations.GO_annotation.length > 0" class="mb-3">
            <h4>GO Annotations</h4>
            <table class="table table-bordered">
              <thead class="thead-light">
                <tr>
                  <th>GO Type</th>
                  <th>Term</th>
                  <th>GO ID</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(goItem, index) in parsedGoAnnotations" :key="index">
                  <td>{{ goItem.type }}</td>
                  <td>{{ goItem.term }}</td>
                  <td>{{ goItem.id }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- KEGG注释 -->
          <div v-if="annotations.KEGG_annotation && annotations.KEGG_annotation.length > 0" class="mb-3">
            <h4>KEGG Annotations</h4>
            <ul class="list-group">
              <li v-for="(item, index) in annotations.KEGG_annotation" :key="index" class="list-group-item">
                {{ item }}
              </li>
            </ul>
          </div>

           <!-- PFAM注释 -->
          <div v-if="annotations.Pfam_annotation && annotations.Pfam_annotation.length > 0" class="mb-3">
            <h4>PFAM Annotations</h4>
            <ul class="list-group">
              <li v-for="(item, index) in annotations.Pfam_annotation" :key="index" class="list-group-item">
                {{ item }}
              </li>
            </ul>
          </div>

           <!-- TrEMBL注释 -->
          <div v-if="annotations.TrEMBL_annotation && annotations.TrEMBL_annotation.length > 0" class="mb-3">
            <h4>TrEMBL Annotations</h4>
            <ul class="list-group">
              <li v-for="(item, index) in annotations.TrEMBL_annotation" :key="index" class="list-group-item">
                {{ item }}
              </li>
            </ul>
          </div>

           <!-- nr注释 -->
          <div v-if="annotations.nr_annotation && annotations.nr_annotation.length > 0" class="mb-3">
            <h4>nr Annotations</h4>
            <ul class="list-group">
              <li v-for="(item, index) in annotations.nr_annotation" :key="index" class="list-group-item">
                {{ item }}
              </li>
            </ul>
          </div>
          
          <!-- Swissprot注释 -->
          <div v-if="annotations.Swissprot_annotation && annotations.Swissprot_annotation.length > 0" class="mb-3">
            <h4>Swissprot Annotations</h4>
            <ul class="list-group">
              <li v-for="(item, index) in annotations.Swissprot_annotation" :key="index" class="list-group-item">
                {{ item }}
              </li>
            </ul>
          </div>
          
          <!-- 其他注释类型... -->
        </div>
      </div>
      
      <!-- GFF数据表格 -->
      <div v-if="hasGffData" class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h2>GFF Data</h2>
          <div>
            <button class="btn btn-sm btn-success mr-2" @click="downloadGff('txt')">Download as TXT</button>
            <button class="btn btn-sm btn-success" @click="downloadGff('gff')">Download as GFF</button>
          </div>
        </div>
        <div class="card-body">
          <!-- 表格控制 -->
          <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="table-pagination">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                layout="sizes"
                :total="gffData.length"
                @current-change="handlePageChange"
                @update:page-size="handlePageSizeChange"
              />
            </div>
          </div>
          
          <!-- 表格内容 -->
          <el-skeleton v-if="isLoading" :rows="10" animated />
          
          <el-table
            v-else
            :data="currentPageGffData"
            style="width: 100%"
            stripe
            border
          >
            <el-table-column prop="seqid" label="Seqid" min-width="100" />
            <el-table-column prop="source" label="Source" min-width="100" />
            <el-table-column prop="type" label="Type" min-width="100" />
            <el-table-column prop="start" label="Start" min-width="100" />
            <el-table-column prop="end" label="End" min-width="100" />
            <el-table-column prop="score" label="Score" min-width="50" />
            <el-table-column prop="strand" label="Strand" min-width="50" />
            <el-table-column prop="phase" label="Phase" min-width="50" />
            <el-table-column prop="attributes" label="Attributes" min-width="200" />
          </el-table>

          <!-- 分页 -->
          <div class="d-flex justify-content-between align-items-center mt-3">
            <span class="table-info">
              Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, gffData.length) }} of {{ gffData.length }} entries
            </span>
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              :total="gffData.length"
              @current-change="handlePageChange"
              @update:page-size="handlePageSizeChange"
            />
          </div>
        </div>
      </div>
      
      <!-- 返回按钮 -->
      <div class="mt-4">
        <router-link to="/id-search" class="btn btn-primary">Return to Search</router-link>
      </div>
    </div>
    
    <!-- 序列弹窗组件 -->
    <div v-if="showModal" class="modal" style="display: flex; justify-content: center; align-items: center; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.5); z-index: 1050;" @click.self="closeModal">
      <div class="modal-dialog" style="max-width: 50vw; max-height: 50vh; margin: 0; width: auto;">
        <div class="modal-content" style="height: 100%; display: flex; flex-direction: column;">
          <div class="modal-header">
            <h5 class="modal-title">{{ modalTitle }}</h5>
            <button type="button" class="close" @click="closeModal" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">&times;</button>
          </div>
          <div class="modal-body" style="flex: 1; overflow-y: auto;">
            <div class="bg-light p-3 rounded" style="max-height: calc(40vh - 100px); overflow-y: auto; white-space: pre-wrap; word-break: break-all;">
              {{ modalContent }}
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-primary mr-2" @click="copySequence(modalContent)">Copy Sequence</button>
            <button class="btn btn-secondary mr-2" @click="downloadFasta">Download FASTA</button>
            <button class="btn btn-secondary" @click="closeModal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// 引入http实例和SequenceDisplay组件
import httpInstance from '../utils/http'
import SequenceDisplay from '@/components/SequenceDisplay.vue'

export default {
  name: 'IdSearchResultsView',
  components: {
    SequenceDisplay
  },
  data() {
    return {
      result: null,
      hasFetched: false,
      annotations: {},
      jbrowse_url: '',
      isLoading: false,
      errorMessage: '',
      has_sequences: false,
      sequenceCache: {},   // key: geneId|type|transcriptId
      sequenceLoading: {}, // loading 状态
      // 转录本选择相关
      selectedTranscriptIndex: 0,
      // GFF数据相关
      gffData: [],
      hasGffData: false,
      // 分页相关
      currentPage: 1,
      pageSize: 10,
      // 弹窗相关状态
      showModal: false,
      modalTitle: '',
      modalContent: '',
      currentSeqType: '',
      currentGeneId: '',
      svgWidth: 800, // 基因结构图SVG宽度
      // 上下游序列长度
      upstreamLength: 500, // 默认值
      downstreamLength: 500 // 默认值
    }
  },
  computed: {
    parsedGoAnnotations() {
      const goAnnotations = this.annotations.GO_annotation || [];
      const parsed = [];
      
      goAnnotations.forEach(annotation => {
        // 处理每个注释项，移除末尾可能的分号
        const cleanAnnotation = annotation.replace(/;;+\s*$/, '');
        // 按;; 分割多个GO注释
        const goTerms = cleanAnnotation.split(';; ');
        
        goTerms.forEach(term => {
          // 匹配GO注释格式：Type: Term (GO:ID)
          const match = term.match(/^(\w+\s+\w+):\s*([^\(]+)\s*\((GO:\d+)\)$/);
          if (match) {
            parsed.push({
              type: match[1],
              term: match[2].trim(),
              id: match[3]
            });
          }
        });
      });
      
      return parsed;
    },
    // 当前选择的转录本
    currentTranscript() {
      if (!this.result || !this.result.mrna_transcripts || this.result.mrna_transcripts.length === 0) {
        return null;
      }
      return this.result.mrna_transcripts[this.selectedTranscriptIndex];
    },
    // 转录本数量
    hasMultipleTranscripts() {
      return this.result && this.result.mrna_transcripts && this.result.mrna_transcripts.length > 1;
    },
    // 当前页GFF数据
    currentPageGffData() {
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      return this.gffData.slice(start, end);
    },
      // 当前转录本的GFF数据
      currentTranscriptGffData() {
      if (!this.gffData || this.gffData.length === 0) {
        return [];
      }
      console.log('currentTranscriptId:', this.currentTranscript)
      const currentTranscriptId = this.currentTranscript ? this.currentTranscript.id : this.result.IDs;
      if (!currentTranscriptId) {
        return [];
      }
      
      // 过滤当前转录本的GFF数据
      return this.gffData.filter(item => {
        // 检查attributes字段是否包含当前转录本ID
        if (item.attributes) {
          return item.attributes.includes(currentTranscriptId);
        }
        return false;
      }).sort((a, b) => {
        // 按start位置排序
        return (a.start || 0) - (b.start || 0);
      });
    },
    // 基因起始位置
    geneStart() {
      if (!this.currentTranscriptGffData || this.currentTranscriptGffData.length === 0) {
        return 0;
      }
      return Math.min(...this.currentTranscriptGffData.map(item => item.start || 0));
    },
    // 基因结束位置
    geneEnd() {
      if (!this.currentTranscriptGffData || this.currentTranscriptGffData.length === 0) {
        return 0;
      }
      return Math.max(...this.currentTranscriptGffData.map(item => item.end || 0));
    },
    // 基因长度
    geneLength() {
      return this.geneEnd - this.geneStart + 1;
    },
    // 缩放比例
    scale() {
      // 计算缩放比例，留出20px的边距
      const availableWidth = this.svgWidth - 40;
      return availableWidth / Math.max(this.geneLength, 1);
    }
  },
mounted() {
  const geneId = this.$route.query.id
  if (geneId && !this.hasFetched) {
    this.hasFetched = true
    this.fetchGeneData(geneId)
  } else if (!geneId) {
    this.errorMessage = '未提供基因ID'
  }
},

  
  methods: {
    // 处理页码变化
    handlePageChange() {
      // 页码变化时不需要重新请求数据，只需要更新计算属性
    },
    // 处理每页条数变化
    handlePageSizeChange() {
      this.currentPage = 1 // 重置页码
    },
    async fetchGeneData(geneId) {
      // 添加延迟显示加载状态，避免快速请求时显示不必要的加载动画
      const loadingTimeout = setTimeout(() => {
        this.isLoading = true
      }, 300) // 300ms延迟，只有请求超过这个时间才显示加载状态
      
      this.errorMessage = ''
      this.selectedTranscriptIndex = 0; // 重置为默认选择第一个转录本
      
      try {
        // 修改为使用现有的批量查询API，传递单个基因ID
        const formData = new FormData()
        formData.append('gene_ids', geneId)

        const response = await httpInstance.post(
          '/tools/id-search/api/id-search-form/',
          formData
        )


        
        // 清除加载超时定时器
        clearTimeout(loadingTimeout)
        
        // 由于http拦截器已经返回response.data，直接使用response
        
        if (response.status === 'error' || response.status === 'not_found') {
          throw new Error(response.error || '基因信息不存在')
        }
        
        // 更新数据 - 从results数组中获取第一个元素
        if (response.results && response.results.length > 0) {
          this.result = response.results[0]
          this.annotations = this.result.annotations || {}
          this.jbrowse_url = this.result.jbrowse_url || ''
          this.gffData = this.result.gff_data || []
          this.gene_seq = this.result.gene_seq || ''
          
          // 调试日志：查看后端返回的完整数据结构
          console.log('后端返回的result数据:', this.result)
         //console.log('result中的gene_seq:', this.result.gene_seq)
          //console.log('result中的mrna_seq:', this.result.mrna_seq)
          //console.log('result中的cds_seq:', this.result.cds_seq)
         // console.log('result中的protein_seq:', this.result.protein_seq)
          
          // 检查是否有序列信息：包括直接序列属性和转录本中的序列
          this.has_sequences = !!(this.result.gene_seq || 
                                 this.result.mrna_seq || 
                                 (this.result.cds_seq && this.result.cds_seq !== '未找到CDS序列') ||
                                 (this.result.protein_seq && this.result.protein_seq !== '未找到蛋白序列') ||
                                 (this.result.mrna_transcripts && this.result.mrna_transcripts.length > 0))
        } else {
          throw new Error('未找到基因信息')
        }
        
        // 调试日志：查看has_sequences的值
        console.log('has_sequences:', this.has_sequences)
        
        // 设置GFF数据
        this.hasGffData = this.gffData.length > 0
        // 重置页码到第一页
        this.currentPage = 1
                                
      } catch (error) {
        // 清除加载超时定时器
        clearTimeout(loadingTimeout)
        this.errorMessage = error.message
        console.error('获取基因数据错误:', error)
      } finally {
        this.isLoading = false
      }
    },
    // 切换转录本
    switchTranscript(index) {
      this.selectedTranscriptIndex = index;
    },
    
    // 处理序列长度变化事件
    handleLengthChange(eventData) {
      const { upstreamLength, downstreamLength } = eventData;
      this.upstreamLength = upstreamLength;
      this.downstreamLength = downstreamLength;
      console.log('Sequence length changed:', upstreamLength, downstreamLength);
      
      // 当长度变化时，清除所有相关缓存，确保下次请求时使用新长度
      // 遍历缓存，清除包含upstream或downstream类型的缓存项
      Object.keys(this.sequenceCache).forEach(key => {
        if (key.includes('upstream') || key.includes('downstream')) {
          delete this.sequenceCache[key];
        }
      });
      
      // 清除对应的加载状态
      Object.keys(this.sequenceLoading).forEach(key => {
        if (key.includes('upstream') || key.includes('downstream')) {
          this.sequenceLoading[key] = false;
        }
      });
    },
    // 下载当前转录本的所有序列
    downloadCurrentTranscriptSequences() {
      if (!this.result || !this.currentTranscript) {
        this.showTemporaryMessage('无法获取基因序列数据')
        return;
      }
      
      let transcriptSequences = '';
      const geneId = this.currentGeneId || this.result.IDs;
      const transcriptId = this.currentTranscript.id;
      
      // 收集当前转录本的所有可用序列
      const sequenceTypes = [
        { key: 'gene_seq', type: 'genomic', label: 'Genomic Sequence' },
        { key: 'cds_seq', type: 'cds', label: 'CDS Sequence' },
        { key: 'protein_seq', type: 'protein', label: 'Protein Sequence' }
      ];
      
      // 添加基因组序列
      if (this.result.gene_seq && this.result.gene_seq !== 'N/A') {
        transcriptSequences += `>${geneId} genomic\n${this.result.gene_seq}\n\n`;
      }
      
      // 添加当前转录本的mRNA序列
      if (this.currentTranscript.mrna_seq && this.currentTranscript.mrna_seq !== 'N/A') {
        transcriptSequences += `>${transcriptId} mRNA\n${this.currentTranscript.mrna_seq}\n\n`;
      }
      
      // 添加当前转录本的上游序列
      if (this.currentTranscript.upstream_seq && this.currentTranscript.upstream_seq !== 'N/A') {
        transcriptSequences += `>${transcriptId} upstream\n${this.currentTranscript.upstream_seq}\n\n`;
      }
      
      // 添加当前转录本的下游序列
      if (this.currentTranscript.downstream_seq && this.currentTranscript.downstream_seq !== 'N/A') {
        transcriptSequences += `>${transcriptId} downstream\n${this.currentTranscript.downstream_seq}\n\n`;
      }
      
      // 添加当前转录本的cDNA序列
      if (this.currentTranscript.cdna_seq && this.currentTranscript.cdna_seq !== 'N/A' && this.currentTranscript.cdna_seq !== 'unavailable') {
        transcriptSequences += `>${transcriptId} cDNA\n${this.currentTranscript.cdna_seq}\n\n`;
      }
      
      // 添加其他序列类型（使用当前转录本的序列）
      const transcriptSequenceTypes = [
        { key: 'cds_seq', type: 'cds', label: 'CDS Sequence' },
        { key: 'protein_seq', type: 'protein', label: 'Protein Sequence' }
      ];
      
      transcriptSequenceTypes.forEach(item => {
        const sequence = this.currentTranscript[item.key];
        if (sequence && sequence !== 'N/A' && sequence !== 'unavailable' && sequence !== '未找到CDS序列' && sequence !== '未找到蛋白序列') {
          transcriptSequences += `>${transcriptId} ${item.type}\n${sequence}\n\n`;
        }
      });
      
      if (!transcriptSequences) {
        this.showTemporaryMessage('没有找到可用的序列数据')
        return;
      }
      
      // 创建并下载文件
      const blob = new Blob([transcriptSequences], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${transcriptId}_all_sequences.fasta`
      // 使用document.createEvent来创建一个自定义事件，避免触发页面刷新
      const event = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      })
      document.body.appendChild(a)
      a.dispatchEvent(event)
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      this.showTemporaryMessage('当前转录本的所有序列已下载')
    },
    // 显示序列弹窗
    showSequenceModal(title, content, seqType, geneId) {
      this.modalTitle = title
      this.modalContent = content
      this.currentSeqType = seqType
      this.currentGeneId = geneId
      this.showModal = true
    },
    
    // 处理SequenceDisplay组件的show-sequence事件
    async handleShowSequence(eventData) {
  /**
   * eventData: { type, title, content, id }
   * type: cds / protein / mrna / upstream / downstream / cdna / gene
   * title: SequenceDisplay 传来的标题
   * content: 序列内容（对于genomic类型，直接使用这个内容，不向后端请求）
   * id: gene ID
   */
  const { type, title, content, id } = eventData

  // 获取真正的基因ID，而不是可能的转录本ID
  const realGeneId = this.result.IDs
  // 使用mrnaid替代transcriptId，与后端字段名保持一致
  const mrnaid = this.currentTranscript?.id || id
  // 对于上下游序列，缓存key需要包含长度信息，确保不同长度的序列缓存分开
  const lengthPart = (type === 'upstream' || type === 'downstream') ? `|${type === 'upstream' ? this.upstreamLength : this.downstreamLength}` : ''
  // 使用realGeneId作为基因ID，确保缓存key的准确性
  const cacheKey = `${realGeneId}|${type}|${mrnaid}${lengthPart}`

  // 已经加载过，直接弹窗
  if (this.sequenceCache[cacheKey]) {
    this.showSequenceModal(
      title,
      this.sequenceCache[cacheKey],
      type,
      realGeneId
    )
    return
  }

  // 正在加载，避免重复点击
  if (this.sequenceLoading[cacheKey]) return
  this.sequenceLoading[cacheKey] = true

  try {
    let fastaContent = ''
    let seq = content
    let isFromContent = true
    
    // 如果content为空，向后端请求序列
    if (!seq) {
      isFromContent = false
      const res = await httpInstance.post(
        '/tools/id-search/api/sequence/',
        {
          gene_id: realGeneId,
          transcript_id: mrnaid,
          type: type
        }
      )
      console.log('序列懒传输成功:', res)
      seq = res.sequence || '未找到序列'
    }
    
    // 如果返回的是有效序列，添加FASTA格式头部
    if (seq && seq !== '未找到序列' && seq !== 'N/A') {
      // 构建FASTA头部，基因组序列使用realGeneId，其他使用mrnaid
      const headerId = type === 'genomic' ? realGeneId : mrnaid
      
      // 根据类型和长度截取序列
      let processedSeq = seq
      if (type === 'upstream') {
        processedSeq = seq.slice(0, this.upstreamLength)
      } else if (type === 'downstream') {
        processedSeq = seq.slice(0, this.downstreamLength)
      }
      
      const lengthInfo = (type === 'upstream' || type === 'downstream') ? ` (${processedSeq.length}bp)` : ''
      fastaContent = `>${headerId} ${type}${lengthInfo}\n${processedSeq}\n`
    } else {
      // 无效序列直接使用
      fastaContent = seq
    }

    // 缓存FASTA格式的序列
    this.sequenceCache[cacheKey] = fastaContent
    this.sequenceLoading[cacheKey] = false

    // 打开弹窗，显示FASTA格式序列
    this.showSequenceModal(
      title,
      fastaContent,
      type,
      realGeneId
    )
  } catch (err) {
    //console.error('序列懒加载失败:', err)
    this.showSequenceModal(
      title,
      '序列加载失败',
      type,
      realGeneId
    )
    this.sequenceLoading[cacheKey] = false
  } finally {
    this.sequenceLoading[cacheKey] = false
  }
    },

    
    // 关闭弹窗
    closeModal() {
      this.showModal = false
    },
    
    copySequence(sequence) {
      // 按照FASTA格式复制序列，包含基因ID和序列类型
      const header = `>${this.currentGeneId} ${this.currentSeqType}`
      const fastaContent = `${header}\n${sequence}`
      
      navigator.clipboard.writeText(fastaContent)
        .then(() => {
          // 创建临时提示元素显示给用户
          this.showTemporaryMessage('序列已复制到剪贴板')
          // 移除自动关闭弹窗逻辑，让用户手动关闭
        })
        .catch(err => {
          console.error('复制失败:', err)
          // 创建临时提示元素显示给用户
          this.showTemporaryMessage('复制失败，请手动复制')
          // 移除自动关闭弹窗逻辑，让用户手动关闭
        })
    },
    
    // 辅助函数：将序列按每行80个字符换行
    formatSequence(seq) {
      if (!seq) return ''
      return seq.replace(/(.{1,80})/g, '$1\n')
    },
    
    // 显示临时消息的方法
    showTemporaryMessage(message) {
      // 创建提示元素
      const msgElement = document.createElement('div')
      msgElement.textContent = message
      msgElement.style.position = 'fixed'
      msgElement.style.top = '50%'
      msgElement.style.left = '50%'
      msgElement.style.transform = 'translate(-50%, -50%)'
      msgElement.style.padding = '10px 20px'
      msgElement.style.backgroundColor = 'rgba(0, 0, 0, 0.8)'
      msgElement.style.color = 'white'
      msgElement.style.borderRadius = '4px'
      msgElement.style.zIndex = '9999'
      msgElement.style.fontSize = '16px'
      
      // 添加到页面
      document.body.appendChild(msgElement)
      
      // 短暂显示后移除
      setTimeout(() => {
        msgElement.style.opacity = '0'
        msgElement.style.transition = 'opacity 2s ease-out'
        setTimeout(() => {
          document.body.removeChild(msgElement)
        }, 1500)
      }, 1500)
    },
    
    downloadFasta() {
      const header = `>${this.currentGeneId} ${this.currentSeqType}`
      const fastaContent = `${header}\n${this.modalContent}`
      
      const blob = new Blob([fastaContent], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${this.currentGeneId}_${this.currentSeqType}.fasta`
      // 使用document.createEvent来创建一个自定义事件，避免触发页面刷新
      const event = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      })
      document.body.appendChild(a)
      a.dispatchEvent(event)
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      // 不移除弹窗，让用户手动关闭
    },
    
    async downloadAllSequences() {
      if (!this.result) {
        this.showTemporaryMessage('无法获取基因序列数据')
        return
      }
      
      this.isLoading = true
      let allSequences = ''
      const geneId = this.currentGeneId || this.result.IDs
      
      // 定义所有需要下载的序列类型
      const allSeqTypes = ['genomic', 'mrna', 'upstream', 'downstream', 'cdna', 'cds', 'protein']
      
      // 获取所有转录本
      const transcripts = this.result.mrna_transcripts || []
      
      try {
        // 添加基因组序列（直接从result获取，不需要请求后端）
        if (this.result.gene_seq && this.result.gene_seq !== 'N/A') {
          const formattedSeq = this.formatSequence(this.result.gene_seq)
          allSequences += `>${geneId} genomic\n${formattedSeq}\n\n`
        }
        
        // 为每个转录本处理所有序列类型
        for (const transcript of transcripts) {
          const transcriptId = transcript.id
          
          // 为每种序列类型获取序列
          for (const seqType of allSeqTypes) {
            // 跳过基因组序列，因为已经添加过了
            if (seqType === 'genomic') continue
            
            // 尝试从当前转录本获取序列
            let seqContent = ''
            let foundInResult = false
            
            // 根据序列类型从transcript或result中获取
            switch (seqType) {
              case 'mrna':
                if (transcript.mrna_seq && transcript.mrna_seq !== 'N/A') {
                  seqContent = transcript.mrna_seq
                  foundInResult = true
                }
                break
              case 'upstream':
                if (transcript.upstream_seq && transcript.upstream_seq !== 'N/A') {
                  seqContent = transcript.upstream_seq
                  foundInResult = true
                }
                break
              case 'downstream':
                if (transcript.downstream_seq && transcript.downstream_seq !== 'N/A') {
                  seqContent = transcript.downstream_seq
                  foundInResult = true
                }
                break
              case 'cdna':
                if (transcript.cdna_seq && transcript.cdna_seq !== 'N/A' && transcript.cdna_seq !== 'unavailable') {
                  seqContent = transcript.cdna_seq
                  foundInResult = true
                }
                break
              case 'cds':
                if (transcript.cds_seq && transcript.cds_seq !== 'N/A' && transcript.cds_seq !== 'unavailable' && transcript.cds_seq !== '未找到CDS序列') {
                  seqContent = transcript.cds_seq
                  foundInResult = true
                }
                break
              case 'protein':
                if (transcript.protein_seq && transcript.protein_seq !== 'N/A' && transcript.protein_seq !== 'unavailable' && transcript.protein_seq !== '未找到蛋白序列') {
                  seqContent = transcript.protein_seq
                  foundInResult = true
                }
                break
            }
            
            // 如果在result中没有找到，从后端获取
            if (!foundInResult) {
              // 构建请求参数
              const requestParams = {
                gene_id: geneId,
                transcript_id: transcriptId,
                type: seqType
              }
              
              // 对于上下游序列，添加长度信息
              if (seqType === 'upstream') {
                requestParams.upstream_length = this.upstreamLength
              } else if (seqType === 'downstream') {
                requestParams.downstream_length = this.downstreamLength
              }
              
              // 发送请求获取序列
              const response = await httpInstance.post(
                '/tools/id-search/api/sequence/',
                requestParams
              )
              
              // 处理响应
              if (response.sequence && response.sequence !== '未找到序列' && response.sequence !== 'N/A') {
                seqContent = response.sequence
              }
            }
            
            // 如果获取到了序列，添加到结果中
            if (seqContent) {
              const formattedSeq = this.formatSequence(seqContent)
              // 基因组序列使用gene_id，其他使用transcriptId
              const headerId = seqType === 'genomic' ? geneId : transcriptId
              allSequences += `>${headerId} ${seqType}\n${formattedSeq}\n\n`
            }
          }
        }
        
        // 如果没有获取到任何序列
        if (!allSequences) {
          this.showTemporaryMessage('没有找到可用的序列数据')
          return
        }
        
        // 创建并下载文件
        const blob = new Blob([allSequences], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${geneId}_all_sequences.fasta`
        // 使用document.createEvent来创建一个自定义事件，避免触发页面刷新
        const event = new MouseEvent('click', {
          bubbles: true,
          cancelable: true,
          view: window
        })
        document.body.appendChild(a)
        a.dispatchEvent(event)
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        this.showTemporaryMessage('所有序列已下载完成')
      } catch (error) {
        console.error('下载序列失败:', error)
        this.showTemporaryMessage('下载序列失败，请重试')
      } finally {
        this.isLoading = false
        // 移除自动关闭弹窗逻辑，避免影响用户体验
      }
    },
    
    // 下载GFF数据
    downloadGff(format) {
      const geneId = this.currentGeneId || this.result.IDs
      
      if (format === 'txt') {
        // 生成TXT格式文本
        let txtContent = ''
        
        this.gffData.forEach(item => {
          const fields = [
            item.seqid || '',
            item.source || '',
            item.type || '',
            item.start || '',
            item.end || '',
            item.score || '',
            item.strand || '',
            item.phase || '',
            item.attributes || ''
          ]
          txtContent += fields.join('\t') + '\n'
        })
        
        const blob = new Blob([txtContent], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${geneId}_gff.txt`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        this.showTemporaryMessage('GFF数据已下载为TXT格式')
      } else if (format === 'gff') {
        // 生成标准GFF格式文本
        let gffContent = ''
        
        this.gffData.forEach(item => {
          const fields = [
            item.seqid || '',
            item.source || '.',
            item.type || '.',
            item.start || '.',
            item.end || '.',
            item.score || '.',
            item.strand || '.',
            item.phase || '.',
            item.attributes || '.'
          ]
          gffContent += fields.join('\t') + '\n'
        })
        
        const blob = new Blob([gffContent], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${geneId}_gff.gff`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        this.showTemporaryMessage('GFF数据已下载为GFF格式')
      }
    },
    
    // 转义CSV字段，处理包含逗号、引号和换行符的情况
    escapeCsvField(field) {
      if (typeof field !== 'string') {
        field = String(field)
      }
      // 如果字段包含逗号、双引号或换行符，则需要用双引号包裹
      if (field.includes(',') || field.includes('"') || field.includes('\n') || field.includes('\r')) {
        // 替换双引号为两个双引号
        field = field.replace(/"/g, '""')
        // 用双引号包裹整个字段
        return `"${field}"`
      }
      return field
    }
  }
}
</script>

<style scoped>
/* 自定义样式 */
.list-group-item {
  word-break: break-all;
}
</style>






