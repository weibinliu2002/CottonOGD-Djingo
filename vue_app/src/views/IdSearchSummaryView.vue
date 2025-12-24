<template>
  <div class="container mt-4">
    <!-- 状态信息区域 -->
    <div class="status-info bg-light p-3 rounded mb-4">
      <p v-if="results.length > 0" class="text-success">找到 {{ results.length }} 个基因序列</p>
      <p v-else-if="!loading && !error" class="text-muted">暂无数据，请检查输入的基因ID</p>
    </div>
    
    <h1>ID搜索结果汇总</h1>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border" role="status">
        <span class="visually-hidden">loading...</span>
      </div>
      <p class="mt-3">正在加载数据，请稍候...</p>
    </div>
    
    <!-- 错误信息 -->
    <div v-else-if="error" class="alert alert-danger mt-4">
      <p>错误: {{ error }}</p>
      <p>请检查URL参数格式或稍后重试</p>
    </div>
    
    <!-- 结果展示 - 只有在加载完成且没有错误时才显示 -->
    <template v-else-if="results">
      <div class="table-responsive">
        <table class="table table-bordered">
          <thead>
            <tr class="text-center">
              <th style="width: 10%">Input ID</th>
              <th style="width: 10%">Query ID</th>
              <th style="width: 10%">Species</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(result, index) in results" :key="`result-${index}`">
              <td class="text-center align-middle" style="width: 10%">
                {{ result.original_id || '-' }}
              </td>
              <td class="text-center align-middle" style="width: 10%">
                <router-link :to="{ path: '/tools/id-search/results/', query: { id: result.IDs } }">
                  {{ result.IDs || '-' }}
                </router-link>
              </td>
              <td class="text-center align-middle" style="width: 10%">
                {{ result.species || '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 序列展示区域 - 为每个基因添加序列按钮 -->
      <div v-if="results.length > 0" class="mt-6">
        <h4>Gene Sequences</h4>
    
          
          <!-- 使用通用序列展示组件，full模式 -->
          <sequence-display
            display-mode="full"
            :results="results"
            :loading="false"
            @show-sequence="handleShowSequence"
            @download-all="downloadAllFasta"
            @copy-all="copyAllFasta"
          />
       
        
        <!-- 批量操作按钮 -->
        <div class="mt-4 d-flex gap-2">
          <button class="btn btn-primary" @click="downloadAllSequences">Download All Sequences</button>
        </div>
      </div>
      <p v-else class="text-muted">No gene sequences available.</p>
    </template>
    
    <!-- 初始状态 - 未开始加载时显示 -->
    <div v-else class="text-center py-5">
      <p class="text-muted">准备加载数据...</p>
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
            <div class="bg-light p-3 rounded" style="max-height: calc(40vh - 100px); overflow-y: auto; white-space: pre-wrap; font-family: monospace;">
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
// 引入http实例和uuid库
import httpInstance from '../utils/http'
import { v4 as uuidv4 } from 'uuid'
import SequenceDisplay from '@/components/SequenceDisplay.vue'

export default {
  name: 'IdSearchSummaryView',
  components: {
    SequenceDisplay
  },
  data() {
    return {
      results: [],
      has_sequences: false,
      loading: false,
      error: null,
      // 弹窗相关状态
      showModal: false,
      modalTitle: '',
      modalContent: '',
      currentSeqType: '',
      currentGeneId: ''
    }
  },
  mounted() {
    console.log('页面已挂载，开始获取数据...');
    console.log('当前URL参数:', new URLSearchParams(window.location.search).toString());
    // 从URL参数或API获取数据
    this.fetchSearchResults()
  },
 methods: {
  async fetchSearchResults() {
    this.loading = true;
    this.error = null;
    this.results = [];
    this.has_sequences = false;

    try {
      const queryParams = new URLSearchParams(window.location.search);
      let geneIds = queryParams.get('id') || queryParams.get('ids') || queryParams.get('query_ids');
      if (!geneIds) {
        this.error = 'URL中未找到基因ID参数';
        this.loading = false;
        return;
      }

      // 将逗号分隔的ID转换为换行符分隔（后端要求）
      const geneIdsWithNewlines = geneIds.split(',').join('\n');

      // 构建表单数据
      const formDataString = `gene_ids=${encodeURIComponent(geneIdsWithNewlines)}`;

      // 只调用一次 POST
      const response = await httpInstance.post(
        '/tools/id-search/api/id-search-form/',
        formDataString,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      );

      if (response && response.status === 'success') {
        this.results = response.results || [];
        this.has_sequences = response.has_sequences || false;
      } else {
        this.error = response.error || '请求处理失败';
      }

    } catch (error) {
      console.error('获取数据失败:', error);
      this.error = '获取数据失败: ' + (error.message || '未知错误');
    } finally {
      this.loading = false;
    }
  },

  // 删除 fetchGeneDetails 方法，前端只依赖一次 POST 返回的 results
},

    
    downloadAllFasta(type) {
      // 实现批量下载功能
      let fastaContent = ''
      
      this.results.forEach(result => {
        let sequence = ''
        let header = `>${result.IDs} ${type}`
        
        switch(type) {
          case 'genomic':
            sequence = result.gene_seq || ''
            break
          case 'mrna':
            sequence = result.mrna_seq || ''
            break
          case 'cds':
            sequence = result.cds_seq || ''
            break
          case 'protein':
            sequence = result.protein_seq || ''
            break
        }
        
        if (sequence && sequence !== 'N/A' && sequence !== '未找到CDS序列' && sequence !== '未找到蛋白序列') {
          fastaContent += `${header}\n${sequence}\n\n`
        }
      })
      
      if (fastaContent) {
        const blob = new Blob([fastaContent], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `all_${type}_sequences.fasta`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
    },
    copyAllFasta(type) {
      // 实现批量复制功能
      let fastaContent = ''
      
      this.results.forEach(result => {
        let sequence = ''
        let header = `>${result.IDs} ${type}`
        
        switch(type) {
          case 'genomic':
            sequence = result.gene_seq || ''
            break
          case 'mrna':
            sequence = result.mrna_seq || ''
            break
          case 'cds':
            sequence = result.cds_seq || ''
            break
          case 'protein':
            sequence = result.protein_seq || ''
            break
        }
        
        if (sequence && sequence !== 'N/A' && sequence !== '未找到CDS序列' && sequence !== '未找到蛋白序列') {
          fastaContent += `${header}\n${sequence}\n\n`
        }
      })
      
      if (fastaContent) {
        navigator.clipboard.writeText(fastaContent)
          .then(() => {
            alert('序列已复制到剪贴板')
          })
          .catch(err => {
            console.error('复制失败:', err)
          })
      }
    },
    
    // 处理序列显示事件
    handleShowSequence(eventData) {
      const { type, title, content, id } = eventData
      this.modalTitle = title
      this.modalContent = content
      this.currentSeqType = type
      this.currentGeneId = id
      this.showModal = true
    },
    
    // 关闭弹窗
    closeModal() {
      this.showModal = false
    },
    
    // 批量下载所有序列
    downloadAllSequences() {
      let allSequences = ''
      
      // 收集所有基因的所有序列类型
      this.results.forEach(result => {
        const geneId = result.IDs
        
        // 添加基因组序列
        if (result.gene_seq && result.gene_seq !== 'N/A' && result.gene_seq !== '') {
          allSequences += `>${geneId} genomic\n${result.gene_seq}\n\n`
        }
        
        // 添加mRNA序列
        if (result.mrna_seq && result.mrna_seq !== 'N/A' && result.mrna_seq !== '') {
          allSequences += `>${geneId} mrna\n${result.mrna_seq}\n\n`
        }
        
        // 添加CDS序列
        if (result.cds_seq && result.cds_seq !== 'N/A' && result.cds_seq !== '未找到CDS序列') {
          allSequences += `>${geneId} cds\n${result.cds_seq}\n\n`
        }
        
        // 添加蛋白序列
        if (result.protein_seq && result.protein_seq !== 'N/A' && result.protein_seq !== '未找到蛋白序列') {
          allSequences += `>${geneId} protein\n${result.protein_seq}\n\n`
        }
      })
      
      if (allSequences) {
        const blob = new Blob([allSequences], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `all_sequences.fasta`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } else {
        alert('没有找到可用的序列数据')
      }
    },
    
    // 复制序列到剪贴板
    copySequence(sequence) {
      // 按照FASTA格式复制序列，包含基因ID和序列类型
      const header = `>${this.currentGeneId} ${this.currentSeqType}`
      const fastaContent = `${header}\n${sequence}`
      
      navigator.clipboard.writeText(fastaContent)
        .then(() => {
          // 创建临时提示元素显示给用户
          this.showTemporaryMessage('序列已复制到剪贴板')
        })
        .catch(err => {
          console.error('复制失败:', err)
          // 创建临时提示元素显示给用户
          this.showTemporaryMessage('复制失败，请手动复制')
        })
    },
    
    // 下载FASTA格式序列
    downloadFasta() {
      const header = `>${this.currentGeneId} ${this.currentSeqType}`
      const fastaContent = `${header}\n${this.modalContent}`
      
      const blob = new Blob([fastaContent], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${this.currentGeneId}_${this.currentSeqType}.fasta`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
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
        msgElement.style.transition = 'opacity 0.5s ease-out'
        setTimeout(() => {
          document.body.removeChild(msgElement)
        }, 500)
      }, 1500)
    }
  }
</script>

<style scoped>
/* 可以添加组件特定的样式 */
</style>