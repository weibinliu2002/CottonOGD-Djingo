// 引入Pinia
import { defineStore } from 'pinia'
import httpInstance from '@/utils/http.js'
import router from '@/router'
import { useNavigationStore } from './navigationStore.ts'

// 定义基因搜索状态管理store
export const useGeneSearchStore = defineStore('geneSearch', {
  // 状态定义
  state: () => ({
    // 存储搜索输入
    searchInput: '',
    // 存储选择的基因组
    selectedGenome: [],
    // 存储搜索结果
    searchResults: null,
    // 存储加载状态
    isLoading: false,
    // 存储错误信息
    error: null
  }),

  // 动作定义
  actions: {
    // 执行搜索
    async performSearch(geneIds, genomeId) {
      console.log('performSearch called');
      this.isLoading = true;
      this.error = null;
      
      try {
        // 生成请求ID
        const request_id = Date.now().toString();
        console.log('Request ID:', request_id);
        console.log('Search Input:', geneIds);
        console.log('Selected Genome:', genomeId);

        const params = {
          gene_id: geneIds,
          genome_id: genomeId.join(','),
          request_id: request_id
        };
        console.log('API Request Params:', params);

        const response = await httpInstance.post('/CottonOGD_api/geneid_summary/', params);
        console.log('API Response:', response);

        const data = response;
        if (data && data.geneid_result) {
          console.log('Search success');
          this.searchResults = {
            geneid_result: typeof data.geneid_result === 'string' ? JSON.parse(data.geneid_result) : data.geneid_result,
            gene_info_result: typeof data.gene_info_result === 'string' ? JSON.parse(data.gene_info_result) : data.gene_info_result,
            search_map: typeof data.search_map === 'string' ? JSON.parse(data.search_map) : data.search_map
          };
          console.log('Parsed Search Results:', this.searchResults);

          const dbIds = this.searchResults?.search_map 
            ? Object.values(this.searchResults.search_map).map((item) => item.db_id).filter(Boolean)
            : [];
          console.log('DB IDs:', dbIds);
          
          const navigationStore = useNavigationStore();
          navigationStore.setNavigationData('geneSearch', {
            results: this.searchResults,
            dbIds: dbIds,
            requestId: request_id
          });

          router.push({
            name: 'idSearchSummary'
          });
        } else {
          console.error('Search failed: missing geneid_result');
          throw new Error(data.message || 'Search failed: No data returned');
        }
      } catch (e) {
        console.error('Search failed with exception:', e);
        this.error = e.message || 'An unknown error occurred';
        this.searchResults = null;
      } finally {
        this.isLoading = false;
        console.log('performSearch finished');
      }
    },

    // 清除状态
    clearState() {
      this.searchInput = ''
      this.selectedGenome = []
      this.searchResults = null
      this.isLoading = false
      this.error = null
    },

    // 清除错误
    clearError() {
      this.error = null
    },

    // 设置错误
    setError(message) {
      this.error = message
    }
  }
})

