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
    
          
          <!-- 使用通用序列展示组件 -->
          <sequence-display
            :results="results"
            :loading="false"
            @show-sequence="handleShowSequence"
            @length-change="handleLengthChange"
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
      // 上下游长度选择
      selectedUpstreamLength: 10000,
      selectedDownstreamLength: 10000,
      // 序列缓存和加载状态
      sequenceCache: {},   // key: geneId|type|transcriptId|upLen|downLen
      sequenceLoading: {}, // loading 状态
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
  // 处理长度变化事件
  handleLengthChange(lengths) {
    this.selectedUpstreamLength = lengths.upstreamLength || 10000
    this.selectedDownstreamLength = lengths.downstreamLength || 10000
  },
  
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

  downloadAllFasta(type) {
    // 实现批量下载功能，支持所有转录本
    let fastaContent = ''
    
    this.results.forEach(result => {
      const geneId = result.IDs
      
      // 处理基因组序列
      if (type === 'genomic' && result.gene_seq && result.gene_seq !== 'N/A' && result.gene_seq !== '') {
        fastaContent += `>${geneId} genomic\n${result.gene_seq}\n\n`
      }
      
      // 处理转录本序列
      if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
        result.mrna_transcripts.forEach(transcript => {
          let sequence = ''
          
          switch(type) {
            case 'mrna':
              sequence = transcript.mrna_seq || ''
              break
            case 'cdna':
              sequence = transcript.cdna_seq || ''
              break
            case 'cds':
              sequence = transcript.cds_seq || ''
              break
            case 'protein':
              sequence = transcript.protein_seq || ''
              break
            case 'upstream':
              sequence = transcript.upstream_seq || ''
              break
            case 'downstream':
              sequence = transcript.downstream_seq || ''
              break
          }
          
          if (sequence && sequence !== 'N/A' && sequence !== '未找到CDS序列' && sequence !== '未找到蛋白序列') {
            fastaContent += `>${transcript.id} ${type}\n${sequence}\n\n`
          }
        })
      } else {
        // 如果没有transcripts数组，使用result本身的序列
        let sequence = ''
        
        switch(type) {
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
          fastaContent += `>${geneId} ${type}\n${sequence}\n\n`
        }
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
    // 实现批量复制功能，支持所有转录本
    let fastaContent = ''
    
    this.results.forEach(result => {
      const geneId = result.IDs
      
      // 处理基因组序列
      if (type === 'genomic' && result.gene_seq && result.gene_seq !== 'N/A' && result.gene_seq !== '') {
        fastaContent += `>${geneId} genomic\n${result.gene_seq}\n\n`
      }
      
      // 处理转录本序列
      if (result.mrna_transcripts && result.mrna_transcripts.length > 0) {
        result.mrna_transcripts.forEach(transcript => {
          let sequence = ''
          
          switch(type) {
            case 'mrna':
              sequence = transcript.mrna_seq || ''
              break
            case 'cdna':
              sequence = transcript.cdna_seq || ''
              break
            case 'cds':
              sequence = transcript.cds_seq || ''
              break
            case 'protein':
              sequence = transcript.protein_seq || ''
              break
            case 'upstream':
              sequence = transcript.upstream_seq || ''
              break
            case 'downstream':
              sequence = transcript.downstream_seq || ''
              break
          }
          
          if (sequence && sequence !== 'N/A' && sequence !== '未找到CDS序列' && sequence !== '未找到蛋白序列') {
            fastaContent += `>${transcript.id} ${type}\n${sequence}\n\n`
          }
        })
      } else {
        // 如果没有transcripts数组，使用result本身的序列
        let sequence = ''
        
        switch(type) {
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
          fastaContent += `>${geneId} ${type}\n${sequence}\n\n`
        }
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
  
  // 辅助函数：将序列按每行80个字符换行
  formatSequence(seq) {
    if (!seq) return ''
    return seq.replace(/(.{1,80})/g, '$1\n')
  },
  
  // 处理序列显示事件
  async handleShowSequence(eventData) {
    const { type, title, content, id } = eventData
    this.modalTitle = title
    this.currentSeqType = type
    this.currentGeneId = id
    
    // 获取选择的长度
    const upLen = this.selectedUpstreamLength || 500
    const downLen = this.selectedDownstreamLength || 500
    
    // 生成所有基因的该类型序列的FASTA内容
    let allFastaContent = ''
    
    // 遍历所有基因结果
    for (const geneData of this.results) {
      const geneId = geneData.IDs
      
      // 1. 首先处理基因组序列（如果是基因组序列类型）
      if (type === 'genomic' && geneData.gene_seq && geneData.gene_seq !== 'N/A' && geneData.gene_seq !== '') {
        // 直接从result中获取基因组序列，不需要请求后端
        allFastaContent += `>${geneId} genomic\n`
        allFastaContent += this.formatSequence(geneData.gene_seq)
        allFastaContent += '\n\n'
        continue // 基因组序列不需要处理转录本
      }
      
      // 2. 处理其他序列类型
      // 对于其他序列类型，处理所有转录本的序列
      if (geneData.mrna_transcripts && geneData.mrna_transcripts.length > 0) {
        // 使用transcript_id替代mrnaid，修复拼写错误
        for (const transcript of geneData.mrna_transcripts) {
          const transcriptId = transcript.id || transcript.transcript_id || geneId
          // 在缓存键中添加长度信息
          const cacheKey = `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`
          
          // 检查缓存
          if (this.sequenceCache[cacheKey]) {
            allFastaContent += this.sequenceCache[cacheKey]
            allFastaContent += '\n\n'
            continue
          }
          
          // 正在加载，跳过
          if (this.sequenceLoading[cacheKey]) continue
          
          // 设置加载状态
          this.sequenceLoading[cacheKey] = true
          
          try {
            let seqContent = ''
            
            // 从转录本对象中获取序列（如果有）
            if (transcript[type + '_seq'] && transcript[type + '_seq'] !== 'N/A' && transcript[type + '_seq'] !== '未找到CDS序列' && transcript[type + '_seq'] !== '未找到蛋白序列') {
              seqContent = transcript[type + '_seq']
            } 
            // 如果转录本中没有，向后端请求序列
            else {
              const res = await httpInstance.post(
                '/tools/id-search/api/sequence/',
                {
                  gene_id: geneId,
                  transcript_id: transcriptId,
                  type: type,
                  // 添加长度参数
                  upstream_length: upLen,
                  downstream_length: downLen
                }
              )
              console.log('序列检索成功:', res)
              const seq = res.sequence || '未找到序列'
              
              // 如果返回的是有效序列，直接使用
              if (seq && seq !== '未找到序列' && seq !== 'N/A') {
                seqContent = seq
              } else {
                seqContent = seq
              }
            }
            
            // 对上下游序列进行长度截取
            if ((type === 'upstream' || type === 'downstream') && seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
              const maxLen = type === 'upstream' ? upLen : downLen
              seqContent = seqContent.slice(0, maxLen)
            }
            
            // 生成FASTA格式的序列
            let fastaContent = ''
            if (seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
              // 添加FASTA头部，包含长度信息
              const lenInfo = (type === 'upstream' || type === 'downstream') ? ` (${type === 'upstream' ? upLen : downLen}bp)` : ''
              fastaContent = `>${transcriptId} ${type}${lenInfo}\n`
              // 格式化序列，每80个字符换行
              fastaContent += this.formatSequence(seqContent)
            } else {
              fastaContent = seqContent
            }
            
            // 缓存FASTA格式的序列
            this.sequenceCache[cacheKey] = fastaContent
            
            // 添加到所有序列内容中
            allFastaContent += fastaContent
            allFastaContent += '\n\n'
          } catch (error) {
            console.error('序列检索失败:', error)
            allFastaContent += `>${transcriptId} ${type}\n检索序列失败\n\n`
          } finally {
            this.sequenceLoading[cacheKey] = false
          }
        }
      } else {
        // 如果没有transcripts数组，使用geneData本身的序列
        // 在缓存键中添加长度信息
        const cacheKey = `${geneId}|${type}|${geneId}|${upLen}|${downLen}`
        
        // 检查缓存
        if (this.sequenceCache[cacheKey]) {
          allFastaContent += this.sequenceCache[cacheKey]
          allFastaContent += '\n\n'
          continue
        }
        
        // 正在加载，跳过
        if (this.sequenceLoading[cacheKey]) continue
        
        // 设置加载状态
        this.sequenceLoading[cacheKey] = true
        
        try {
          let seqContent = ''
          
          // 从geneData对象中获取序列（如果有）
          if (geneData[type + '_seq'] && geneData[type + '_seq'] !== 'N/A' && geneData[type + '_seq'] !== '未找到CDS序列' && geneData[type + '_seq'] !== '未找到蛋白序列') {
            seqContent = geneData[type + '_seq']
          } 
          // 如果没有，向后端请求序列
          else {
            const res = await httpInstance.post(
              '/tools/id-search/api/sequence/',
              {
                gene_id: geneId,
                transcript_id: geneId,
                type: type,
                // 添加长度参数
                upstream_length: upLen,
                downstream_length: downLen
              }
            )
            console.log('序列检索成功:', res)
            const seq = res.sequence || '未找到序列'
            
            // 如果返回的是有效序列，直接使用
            if (seq && seq !== '未找到序列' && seq !== 'N/A') {
              seqContent = seq
            } else {
              seqContent = seq
            }
          }
          
          // 对上下游序列进行长度截取
          if ((type === 'upstream' || type === 'downstream') && seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
            const maxLen = type === 'upstream' ? upLen : downLen
            seqContent = seqContent.slice(0, maxLen)
          }
          
          // 生成FASTA格式的序列
          let fastaContent = ''
          if (seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
            // 添加FASTA头部，包含长度信息
            const lenInfo = (type === 'upstream' || type === 'downstream') ? ` (${type === 'upstream' ? upLen : downLen}bp)` : ''
            fastaContent = `>${geneId} ${type}${lenInfo}\n`
            // 格式化序列，每80个字符换行
            fastaContent += this.formatSequence(seqContent)
          } else {
            fastaContent = seqContent
          }
          
          // 缓存FASTA格式的序列
          this.sequenceCache[cacheKey] = fastaContent
          
          // 添加到所有序列内容中
          allFastaContent += fastaContent
          allFastaContent += '\n\n'
        } catch (error) {
          console.error('序列检索失败:', error)
          allFastaContent += `>${geneId} ${type}\n检索序列失败\n\n`
        } finally {
          this.sequenceLoading[cacheKey] = false
        }
      }
    }
    
    // 移除最后多余的换行
    allFastaContent = allFastaContent.trim()
    
    // 如果没有序列，显示提示信息
    if (!allFastaContent) {
      allFastaContent = '未找到该类型的序列'
    }
    
    // 显示所有序列
    this.modalContent = allFastaContent
    this.showModal = true
  },
  
  // 关闭弹窗
  closeModal() {
    this.showModal = false
  },
  
  // 批量下载所有序列
  async downloadAllSequences() {
    // 所有可能的序列类型
    const sequenceTypes = ['genomic', 'mrna', 'upstream', 'downstream', 'cdna', 'cds', 'protein']
    
    // 获取选择的长度
    const upLen = this.selectedUpstreamLength || 500
    const downLen = this.selectedDownstreamLength || 500
    
    let allSequences = ''
    let hasSequences = false
    
    // 遍历所有基因结果
    for (const geneData of this.results) {
      const geneId = geneData.IDs
      
      // 遍历所有序列类型
      for (const type of sequenceTypes) {
        // 1. 首先处理基因组序列
        if (type === 'genomic' && geneData.gene_seq && geneData.gene_seq !== 'N/A' && geneData.gene_seq !== '') {
          // 直接从result中获取基因组序列
          allSequences += `>${geneId} genomic\n`
          allSequences += this.formatSequence(geneData.gene_seq)
          allSequences += '\n\n'
          hasSequences = true
          continue
        }
        
        // 2. 处理所有转录本的序列
        if (geneData.mrna_transcripts && geneData.mrna_transcripts.length > 0) {
          for (const transcript of geneData.mrna_transcripts) {
            const transcriptId = transcript.id || transcript.transcript_id || geneId
            const cacheKey = `${geneId}|${type}|${transcriptId}|${upLen}|${downLen}`
            
            let seqContent = ''
            let found = false
            
            // 检查缓存
            if (this.sequenceCache[cacheKey]) {
              seqContent = this.sequenceCache[cacheKey]
              found = true
            }
            // 从转录本对象中获取序列（如果有）
            else if (transcript[type + '_seq'] && transcript[type + '_seq'] !== 'N/A' && transcript[type + '_seq'] !== '未找到CDS序列' && transcript[type + '_seq'] !== '未找到蛋白序列') {
              seqContent = transcript[type + '_seq']
              found = true
            }
            // 从geneData对象中获取序列（如果有）
            else if (geneData[type + '_seq'] && geneData[type + '_seq'] !== 'N/A' && geneData[type + '_seq'] !== '未找到CDS序列' && geneData[type + '_seq'] !== '未找到蛋白序列') {
              seqContent = geneData[type + '_seq']
              found = true
            }
            
            // 对上下游序列进行长度截取
            if ((type === 'upstream' || type === 'downstream') && seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
              const maxLen = type === 'upstream' ? upLen : downLen
              seqContent = seqContent.slice(0, maxLen)
            }
            
            // 如果找到了序列，添加到结果中
            if (found && seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
              // 添加FASTA头部，包含长度信息
              const lenInfo = (type === 'upstream' || type === 'downstream') ? ` (${type === 'upstream' ? upLen : downLen}bp)` : ''
              allSequences += `>${transcriptId} ${type}${lenInfo}\n`
              allSequences += this.formatSequence(seqContent)
              allSequences += '\n\n'
              hasSequences = true
            }
            // 如果没有找到，从后端获取
            else {
              try {
                const res = await httpInstance.post(
                  '/tools/id-search/api/sequence/',
                  {
                    gene_id: geneId,
                    transcript_id: transcriptId,
                    type: type,
                    // 添加长度参数
                    upstream_length: upLen,
                    downstream_length: downLen
                  }
                )
                const seq = res.sequence || '未找到序列'
                
                // 如果返回的是有效序列，添加到结果中
                if (seq && seq !== '未找到序列' && seq !== 'N/A') {
                  // 对上下游序列进行长度截取
                  let finalSeq = seq
                  if ((type === 'upstream' || type === 'downstream')) {
                    const maxLen = type === 'upstream' ? upLen : downLen
                    finalSeq = seq.slice(0, maxLen)
                  }
                  
                  // 添加FASTA头部，包含长度信息
                  const lenInfo = (type === 'upstream' || type === 'downstream') ? ` (${type === 'upstream' ? upLen : downLen}bp)` : ''
                  allSequences += `>${transcriptId} ${type}${lenInfo}\n`
                  allSequences += this.formatSequence(finalSeq)
                  allSequences += '\n\n'
                  hasSequences = true
                  
                  // 缓存序列
                  this.sequenceCache[cacheKey] = finalSeq
                }
              } catch (error) {
                console.error('序列检索失败:', error)
                // 跳过失败的序列，继续处理其他序列
              }
            }
          }
        } else {
          // 如果没有transcripts数组，使用geneData本身的序列或从后端获取
          const cacheKey = `${geneId}|${type}|${geneId}|${upLen}|${downLen}`
          
          let seqContent = ''
          let found = false
          
          // 检查缓存
          if (this.sequenceCache[cacheKey]) {
            seqContent = this.sequenceCache[cacheKey]
            found = true
          }
          // 从geneData对象中获取序列（如果有）
          else if (geneData[type + '_seq'] && geneData[type + '_seq'] !== 'N/A' && geneData[type + '_seq'] !== '未找到CDS序列' && geneData[type + '_seq'] !== '未找到蛋白序列') {
            seqContent = geneData[type + '_seq']
            found = true
          }
          
          // 对上下游序列进行长度截取
          if ((type === 'upstream' || type === 'downstream') && seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
            const maxLen = type === 'upstream' ? upLen : downLen
            seqContent = seqContent.slice(0, maxLen)
          }
          
          // 如果找到了序列，添加到结果中
          if (found && seqContent && seqContent !== '未找到序列' && seqContent !== 'N/A') {
            // 添加FASTA头部，包含长度信息
            const lenInfo = (type === 'upstream' || type === 'downstream') ? ` (${type === 'upstream' ? upLen : downLen}bp)` : ''
            allSequences += `>${geneId} ${type}${lenInfo}\n`
            allSequences += this.formatSequence(seqContent)
            allSequences += '\n\n'
            hasSequences = true
          }
          // 如果没有找到，从后端获取
          else {
            try {
              const res = await httpInstance.post(
                '/tools/id-search/api/sequence/',
                {
                  gene_id: geneId,
                  transcript_id: geneId,
                  type: type,
                  // 添加长度参数
                  upstream_length: upLen,
                  downstream_length: downLen
                }
              )
              const seq = res.sequence || '未找到序列'
              
              // 如果返回的是有效序列，添加到结果中
              if (seq && seq !== '未找到序列' && seq !== 'N/A') {
                // 对上下游序列进行长度截取
                let finalSeq = seq
                if ((type === 'upstream' || type === 'downstream')) {
                  const maxLen = type === 'upstream' ? upLen : downLen
                  finalSeq = seq.slice(0, maxLen)
                }
                
                // 添加FASTA头部，包含长度信息
                const lenInfo = (type === 'upstream' || type === 'downstream') ? ` (${type === 'upstream' ? upLen : downLen}bp)` : ''
                allSequences += `>${geneId} ${type}${lenInfo}\n`
                allSequences += this.formatSequence(finalSeq)
                allSequences += '\n\n'
                hasSequences = true
                
                // 缓存序列
                this.sequenceCache[cacheKey] = finalSeq
              }
            } catch (error) {
              console.error('序列检索失败:', error)
              // 跳过失败的序列，继续处理其他序列
            }
          }
        }
      }
    }
    
    // 移除最后多余的换行
    allSequences = allSequences.trim()
    
    if (allSequences && hasSequences) {
      const blob = new Blob([allSequences], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `all_sequences.fasta`
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
    } else {
      // 使用自定义消息提示，避免alert弹窗
      this.showTemporaryMessage('没有找到可用的序列数据')
    }
  },
  
  // 复制序列到剪贴板
  copySequence(sequence) {
    // 直接复制完整的FASTA格式序列
    navigator.clipboard.writeText(sequence)
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
    // 直接使用完整的FASTA格式序列
    const fastaContent = this.modalContent
    
    const blob = new Blob([fastaContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${this.currentGeneId}_${this.currentSeqType}_all_transcripts.fasta`
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
}
</script>

<style scoped>
/* 可以添加组件特定的样式 */
</style>