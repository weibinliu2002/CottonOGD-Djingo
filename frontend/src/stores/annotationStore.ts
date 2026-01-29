
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useRouter } from 'vue-router'
import { useAsyncTask } from '@/composables/useAsyncTask'

type EnrichmentType = 'go' | 'kegg'

// --- TYPE DEFINITIONS ---

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
  results: Record<GoResultCategory, {
    results: GoTerm[];
    total: number;
  }>;
  plot_images: Record<GoResultCategory, string>;
  execution_time: number;
}

export interface KeggTerm {
  pathway_id: string;
  description: {
    name: string;
    definition?: string;
  };
  gene_ratio: string;
  bg_ratio: string;
  p_value: number;
  genes: string;
}

export interface KeggEnrichmentResult {
  results: {
    data: KeggTerm[];
    total: number;
  };
  plot_image: string | null;
  execution_time: number;
}

export const useEnrichmentStore = defineStore('enrichment', () => {
  const router = useRouter()

  // --- STATE ---
  const geneList = ref('')
  const pValue = ref(0.05)
  const qValue = ref(0.05)

  // --- ASYNC TASK HANDLERS ---
  const goTask = useAsyncTask('/tools/go_enrichment/api/start/', '/tools/go_enrichment/api/results/:taskId/')
  const keggTask = useAsyncTask('/tools/kegg_enrichment/api/start/', '/tools/kegg_enrichment/api/results/:taskId/')

  // Unified state from the active task
  const activeTask = ref<ReturnType<typeof useAsyncTask> | null>(null)

  const enrichmentResults = computed(() => {
    const task = activeTask.value as any;
    return task?.data?.value;
  });
  const loading = computed(() => {
    const task = activeTask.value as any;
    return task?.loading?.value ?? false;
  });
  const error = computed(() => {
    const task = activeTask.value as any;
    return task?.error?.value ?? null;
  });

  // --- ACTIONS ---

  /**
   * Fills the gene list with example data.
   */
  const fillExample = () => {
    const exampleIDs = `Kirkii_Juiced.00g000010
Kirkii_Juiced.00g000020
Kirkii_Juiced.00g000030
Kirkii_Juiced.00g000040
Kirkii_Juiced.00g000050
Kirkii_Juiced.00g000060
Kirkii_Juiced.00g000070
Kirkii_Juiced.00g000080
Kirkii_Juiced.00g000090
Kirkii_Juiced.00g000100
Kirkii_Juiced.00g000110
Kirkii_Juiced.00g000120
Kirkii_Juiced.00g000130
Kirkii_Juiced.00g000140
Kirkii_Juiced.00g000150
Kirkii_Juiced.00g000160
Kirkii_Juiced.00g000170
Kirkii_Juiced.00g000180
Kirkii_Juiced.00g000190
Kirkii_Juiced.00g000200`
    geneList.value = exampleIDs
  }

  /**
   * Runs the enrichment analysis by calling the backend API.
   * @param {EnrichmentType} type - The type of enrichment to run ('go' or 'kegg').
   */
  const runEnrichment = async (type: EnrichmentType) => {
    if (!geneList.value.trim()) {
      // This should be handled by the form validation, but as a safeguard:
      activeTask.value = { ...goTask, error: ref('Gene list cannot be empty.') } as any
      return
    }
    
    activeTask.value = type === 'go' ? goTask : keggTask

    const payload = {
      gene_list: geneList.value,
      p_value: pValue.value,
      q_value: qValue.value,
    }

    if (activeTask.value) {
      const taskId = await activeTask.value.execute(payload)

      if (taskId) {
        const resultPath = type === 'go' ? '/tools/go-enrichment/results' : '/tools/kegg-enrichment/results'
        router.push({
          path: resultPath,
          query: { task_id: taskId },
        })
      }
    }
    // Errors are now handled within the useAsyncTask composable and reflected in the 'error' ref
  }

  /**
   * Polls the results of an enrichment task periodically.
   * @param {EnrichmentType} type - The type of enrichment to check.
   * @param {string} taskId - The ID of the task to check.
   * @param {Record<string, any>} [pollParams] - Optional parameters for polling (e.g., pagination).
   */
  const pollEnrichmentResults = (type: EnrichmentType, taskId: string, pollParams?: Record<string, any>) => {
    activeTask.value = type === 'go' ? goTask : keggTask
    if (activeTask.value) {
      activeTask.value.poll(taskId, pollParams)
    }
  }

  const reset = () => {
    activeTask.value = null;
  }

  return {
    geneList,
    pValue,
    qValue,
    enrichmentResults,
    loading,
    error,
    fillExample,
    runEnrichment,
    pollEnrichmentResults,
    reset, // <-- Export the new action
  }
})
