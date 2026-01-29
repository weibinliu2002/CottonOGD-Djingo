import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import httpInstance from '@/utils/http';
import { useAsyncTask } from '@/composables/useAsyncTask';

// 类型定义
export type GoResultCategory = 'BP' | 'MF' | 'CC';

export interface GoTerm {
  go_id: string;
  description: string;
  gene_ratio: string;
  bg_ratio: string;
  p_value: number;
  genes: string;
}

export interface GoEnrichmentResult {
  results: Record<GoResultCategory, { results: GoTerm[]; total: number }>;
  plot_images: Record<GoResultCategory, string>;
  execution_time: number;
}

export interface KeggEnrichmentResult {
  results: {
    data: Array<{
      pathway_id: string;
      description: { name: string };
      gene_ratio: string;
      bg_ratio: string;
      p_value: number;
      genes: string;
    }>;
    total: number;
  };
  plot_image: string;
  execution_time: number;
}

export const useEnrichmentStore = defineStore('enrichment', () => {
  // 状态
  const geneList = ref('');
  const pValue = ref(0.05);
  const qValue = ref(0.05);
  const enrichmentResults = ref<GoEnrichmentResult | KeggEnrichmentResult | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Asynchronous task handling
  const activeTask = ref<ReturnType<typeof useAsyncTask> | null>(null);

  // 计算属性
  const isLoading = computed(() => {
    const task = activeTask.value as any;
    return task?.loading?.value ?? false;
  });
  const errorMessage = computed(() => {
    const task = activeTask.value as any;
    return task?.error?.value ?? null;
  });

  // 示例数据
  const exampleGeneList = `Gh_D01G0001
Gh_D01G0002
Gh_D01G0003
Gh_D01G0004
Gh_D01G0005`;

  // Actions
  const fillExample = () => {
    geneList.value = exampleGeneList;
  };

  const runEnrichment = async (type: 'go' | 'kegg') => {
    if (!geneList.value.trim()) {
      error.value = '请输入基因ID';
      return;
    }

    const startEndpoint = type === 'go' 
      ? '/CottonOGD_api/go_enrichment/'
      : '/CottonOGD_api/kegg_enrichment/';
    const resultEndpoint = type === 'go'
      ? '/CottonOGD_api/go_enrichment_results/:taskId/'
      : '/CottonOGD_api/kegg_enrichment_results/:taskId/';

    const task = useAsyncTask(startEndpoint, resultEndpoint, { useFormData: false });
    activeTask.value = task;

    const payload = {
      gene_list: geneList.value,
      p_value: pValue.value,
      q_value: qValue.value,
    };

    try {
      const taskId = await task.execute(payload);
      if (taskId) {
        return taskId;
      } else {
        throw new Error('Failed to get task_id from server.');
      }
    } catch (e) {
      console.error('Enrichment submission failed:', e);
      error.value = `提交失败: ${e}`;
      return null;
    }
  };

  const pollEnrichmentResults = async (taskId: string, type: 'go' | 'kegg', params?: any) => {
    const resultEndpoint = type === 'go'
      ? '/CottonOGD_api/go_enrichment_results/:taskId/'
      : '/CottonOGD_api/kegg_enrichment_results/:taskId/';

    const task = useAsyncTask('', resultEndpoint, { useFormData: false });
    activeTask.value = task;

    try {
      await task.poll(taskId, params);
      if (task.data.value) {
        enrichmentResults.value = task.data.value;
      }
    } catch (e) {
      console.error('Failed to poll enrichment results:', e);
      error.value = `获取结果失败: ${e}`;
    }
  };

  const setError = (message: string) => {
    error.value = message;
  };

  const reset = () => {
    geneList.value = '';
    pValue.value = 0.05;
    qValue.value = 0.05;
    enrichmentResults.value = null;
    loading.value = false;
    error.value = null;
    if (activeTask.value) {
      const task = activeTask.value as any;
      if (task.error) {
        task.error.value = null;
      }
      if (task.data) {
        task.data.value = null;
      }
    }
  };

  return {
    // 状态
    geneList,
    pValue,
    qValue,
    enrichmentResults,
    loading,
    error,
    isLoading,
    errorMessage,
    // Actions
    fillExample,
    runEnrichment,
    pollEnrichmentResults,
    setError,
    reset,
  };
});
