import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import httpInstance from '@/utils/http';
import { useAsyncTask } from '@/composables/useAsyncTask';

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

export interface RegionGene {
  geneid_id: string;
  seqid: string;
  start: number;
  end: number;
  strand: string;
  type: string;
  id_id: number;
}

export interface RegionSearchResult {
  region: string;
  genome: string;
  genes: RegionGene[];
  count: number;
}

export interface SyntenyGene {
  id: number;
  Ref_genome: number;
  Query_genome: number;
  Ref_genome_chr: string;
  Ref_genome_start: number;
  Ref_genome_end: number;
  Ref_seq: string;
  Alt_seq: string;
  Query_genome_chr: string;
  Query_genome_start: number;
  Query_genome_end: number;
  Variation_type: string;
  Parent_Variation: string;
  son_type: string;
  copygain: string;
}

export interface GenomeSyntenyResult {
  reference_genome: string;
  query_genome: string;
  chromosome: string;
  reference_genes: SyntenyGene[];
  ref_gene_count: number;
}

export interface GeneLocation {
  gene_id: string;
  chr: string;
  start: number;
  end: number;
  strand: string;
}

export interface GeneLocationResult {
  genome: string;
  chr_distribution: Record<string, number>;
  gene_locations: GeneLocation[];
  total_genes: number;
}

export const useEnrichmentStore = defineStore('enrichment', () => {
  const geneList = ref('');
  const pValue = ref(0.05);
  const qValue = ref(0.05);
  const enrichmentResults = ref<GoEnrichmentResult | KeggEnrichmentResult | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const activeTask = ref<ReturnType<typeof useAsyncTask> | null>(null);

  const isLoading = computed(() => {
    const task = activeTask.value as any;
    return task?.loading?.value ?? false;
  });
  const errorMessage = computed(() => {
    const task = activeTask.value as any;
    return task?.error?.value ?? null;
  });

  const exampleGeneList = `Gh_D01G0001
Gh_D01G0002
Gh_D01G0003
Gh_D01G0004
Gh_D01G0005`;

  const fillExample = () => {
    geneList.value = exampleGeneList;
  };

  const runEnrichment = async (type: 'go' | 'kegg') => {
    if (!geneList.value.trim()) {
      error.value = 'Please enter gene IDs';
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
      error.value = `Submission failed: ${e}`;
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
      error.value = `Failed to get results: ${e}`;
    }
  };

  // ========== Region Search ==========
  const regionSearchResult = ref<RegionSearchResult | null>(null);
  const regionSearchLoading = ref(false);
  const regionSearchError = ref<string | null>(null);

  const searchByRegion = async (genome: string, region: string) => {
    regionSearchLoading.value = true;
    regionSearchError.value = null;
    regionSearchResult.value = null;

    try {
      const formData = new FormData();
      formData.append('genome', genome);
      formData.append('region', region);

      const response = await httpInstance.post('/CottonOGD_api/search_by_genome_location/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }) as any;

      if (response && response.genes) {
        regionSearchResult.value = response as RegionSearchResult;
      } else {
        regionSearchError.value = 'No genes found in the specified region';
      }
    } catch (e: any) {
      regionSearchError.value = e.message || 'Region search failed';
      console.error('Region search failed:', e);
    } finally {
      regionSearchLoading.value = false;
    }
  };

  const clearRegionSearch = () => {
    regionSearchResult.value = null;
    regionSearchError.value = null;
  };

  // ========== Genome Synteny ==========
  const syntenyResult = ref<GenomeSyntenyResult | null>(null);
  const syntenyLoading = ref(false);
  const syntenyError = ref<string | null>(null);

  const searchGenomeSynteny = async (
    referenceGenome: string,
    queryGenome: string,
    chromosome: string,
    variationType: string
  ) => {
    syntenyLoading.value = true;
    syntenyError.value = null;
    syntenyResult.value = null;

    try {
      const formData = new FormData();
      formData.append('reference_genome', referenceGenome);
      formData.append('query_genome', queryGenome);
      formData.append('chromosome', chromosome);
      formData.append('Variation_type', variationType);

      const response = await httpInstance.post('/CottonOGD_api/genome_synteny/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }) as any;

      if (response && response.reference_genes) {
        syntenyResult.value = response as GenomeSyntenyResult;
      } else {
        syntenyError.value = 'No synteny data found';
      }
    } catch (e: any) {
      syntenyError.value = e.message || 'Genome synteny search failed';
      console.error('Genome synteny search failed:', e);
    } finally {
      syntenyLoading.value = false;
    }
  };

  const clearSynteny = () => {
    syntenyResult.value = null;
    syntenyError.value = null;
  };

  // ========== Gene Location ==========
  const geneLocationResult = ref<GeneLocationResult | null>(null);
  const geneLocationLoading = ref(false);
  const geneLocationError = ref<string | null>(null);

  const searchGeneLocation = async (genome: string, geneIds: string) => {
    geneLocationLoading.value = true;
    geneLocationError.value = null;
    geneLocationResult.value = null;

    try {
      const formData = new FormData();
      formData.append('genome', genome);
      formData.append('gene_ids', geneIds);

      const response = await httpInstance.post('/CottonOGD_api/gene_genomic_distribution/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }) as any;

      if (response && response.gene_locations) {
        geneLocationResult.value = response as GeneLocationResult;
      } else {
        geneLocationError.value = 'No gene location data found';
      }
    } catch (e: any) {
      geneLocationError.value = e.message || 'Gene location search failed';
      console.error('Gene location search failed:', e);
    } finally {
      geneLocationLoading.value = false;
    }
  };

  const clearGeneLocation = () => {
    geneLocationResult.value = null;
    geneLocationError.value = null;
  };

  // ========== Common ==========
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
      if (task.error) task.error.value = null;
      if (task.data) task.data.value = null;
    }
  };

  return {
    geneList,
    pValue,
    qValue,
    enrichmentResults,
    loading,
    error,
    isLoading,
    errorMessage,
    fillExample,
    runEnrichment,
    pollEnrichmentResults,
    setError,
    reset,
    regionSearchResult,
    regionSearchLoading,
    regionSearchError,
    searchByRegion,
    clearRegionSearch,
    syntenyResult,
    syntenyLoading,
    syntenyError,
    searchGenomeSynteny,
    clearSynteny,
    geneLocationResult,
    geneLocationLoading,
    geneLocationError,
    searchGeneLocation,
    clearGeneLocation,
  };
});
