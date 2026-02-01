import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { useRouter } from 'vue-router';
import httpInstance from '@/utils/http';
import { useAsyncTask } from '@/composables/useAsyncTask';
import { useNavigationStore } from './navigationStore';

// 定义类型
export type BlastType = 'blastp' | 'blastn' | 'blastx' | 'tblastn' | 'tblastx';
export type DatabaseType = 'genome' | 'cds' | 'mrna' | 'protein';

// 定义基因组选项的接口
interface GenomeOption {
  value: string;
  label: string;
  children?: GenomeOption[];
}

export const useBlastStore = defineStore('blast', () => {
  const router = useRouter();

  // --- 状态 (State) ---
  const sequence = ref('');
  const evalue = ref(0.01);
  const maxTargetSeqs = ref(30);
  const selectedBlastType = ref<BlastType>('blastp');
  const selectedDatabaseType = ref<DatabaseType>('protein');
  const selectedGenomes = ref<string>('');
  
  // 高级参数
  const wordSize = ref(7);
  const matchScore = ref(0);
  const gapOpen = ref(11);
  const gapExtend = ref(1);
  const lowComplexityFilter = ref(true);
  const showAdvancedParams = ref(false);

  // Asynchronous task handling
  const activeTask = ref<ReturnType<typeof useAsyncTask> | null>(null);

  // --- Computed Properties ---
  const loading = computed(() => {
    const task = activeTask.value as any;
    return task?.loading?.value ?? false;
  });
  const error = computed(() => {
    const task = activeTask.value as any;
    return task?.error?.value ?? null;
  });
  const blastResults = computed(() => {
    const task = activeTask.value as any;
    return task?.data?.value ?? null;
  });

  // --- 静态数据 (Static Data) ---
  const exampleSequences = ref({
    blastp: `>Example Protein Sequence for BLASTP
MGEAIKKQEGVSTVKEDNKLIDSKKKKANNSNLAKKTSWRRIDLMATKNQRNDDSSTRKRKSSEGEFDMCGIEVAYEDELKRLKQEGKEDRDECKVKNPDKSLISAYIHDIQQLLVKYRKCRFEYIPPMENNLAHILATETLKNKKEFYLVGSVPKSAEKKEERDRVREPD`,
    blastn: `>Example Nucleotide Sequence for BLASTN
ATGGGCGAAGCGATAAAGAAACAAGAAGGAGTGTCTACCGTCAAGGAAGACAACAAGTTGATCGACTCCAAGAAGAAGAAGGCCAACAAATCAAACCTGGCTAAGAAAACAAGTTGGCGGCGCATCGACCTCATGGCCACCAAGAACCAGAGAAATGATGATTCCAGCACACGAAAAAGGAAATCCTCTGAAGGAGAGTTTGACATGTGTGGGCAAGAGGTTGCGTACGAAGACGAGTTGAAGCGCCTGAAGCAAGAAGGCAAGGAAGACAGAGACGAGTGCAAGGTGAAGAACCCTGACAAATCCTTGATAAGCGCCTACATTCACGATATTCAGCAGCTGCTGGTCAAGAACCGCAAGTGTCGCTTTGAGTACATCCCGCCCATGGAGAACAACCTGGCCCAACATCCTGGCTACCGAGACCCTGAAGAACAAGAAGGAGTTCTACCTGGTGGGTTCCGTCCCTAAATCAGCCGAGAAAAAGGAGGAGCGTGACAGGGTTAGGGAGCCCGATTAG`,
    blastx: `>Example Nucleotide Sequence for BLASTX
ATGGGCGAAGCGATAAAGAAACAAGAAGGAGTGTCTACCGTCAAGGAAGACAACAAGTTGATCGACTCCAAGAAGAAGAAGGCCAACAAATCAAACCTGGCTAAGAAAACAAGTTGGCGGCGCATCGACCTCATGGCCACCAAGAACCAGAGAAATGATGATTCCAGCACACGAAAAAGGAAATCCTCTGAAGGAGAGTTTGACATGTGTGGGCAAGAGGTTGCGTACGAAGACGAGTTGAAGCGCCTGAAGCAAGAAGGCAAGGAAGACAGAGACGAGTGCAAGGTGAAGAACCCTGACAAATCCTTGATAAGCGCCTACATTCACGATATTCAGCAGCTGCTGGTCAAGAACCGCAAGTGTCGCTTTGAGTACATCCCGCCCATGGAGAACAACCTGGCCCAACATCCTGGCTACCGAGACCCTGAAGAACAAGAAGGAGTTCTACCTGGTGGGTTCCGTCCCTAAATCAGCCGAGAAAAAGGAGGAGCGTGACAGGGTTAGGGAGCCCGATTAG`,
    tblastn: `>Example Protein Sequence for TBLASTN
MGEAIKKQEGVSTVKEDNKLIDSKKKKANNSNLAKKTSWRRIDLMATKNQRNDDSSTRKRKSSEGEFDMCGIEVAYEDELKRLKQEGKEDRDECKVKNPDKSLISAYIHDIQQLLVKYRKCRFEYIPPMENNLAHILATETLKNKKEFYLVGSVPKSAEKKEERDRVREPD`,
    tblastx: `>Example Nucleotide Sequence for TBLASTX
ATGGGCGAAGCGATAAAGAAACAAGAAGGAGTGTCTACCGTCAAGGAAGACAACAAGTTGATCGACTCCAAGAAGAAGAAGGCCAACAAATCAAACCTGGCTAAGAAAACAAGTTGGCGGCGCATCGACCTCATGGCCACCAAGAACCAGAGAAATGATGATTCCAGCACACGAAAAAGGAAATCCTCTGAAGGAGAGTTTGACATGTGTGGGCAAGAGGTTGCGTACGAAGACGAGTTGAAGCGCCTGAAGCAAGAAGGCAAGGAAGACAGAGACGAGTGCAAGGTGAAGAACCCTGACAAATCCTTGATAAGCGCCTACATTCACGATATTCAGCAGCTGCTGGTCAAGAACCGCAAGTGTCGCTTTGAGTACATCCCGCCCATGGAGAACAACCTGGCCCAACATCCTGGCTACCGAGACCCTGAAGAACAAGAAGGAGTTCTACCTGGTGGGTTCCGTCCCTAAATCAGCCGAGAAAAAGGAGGAGCGTGACAGGGTTAGGGAGCCCGATTAG`
  });
  
  // 默认示例序列（蛋白质序列）
  const exampleSequence = ref(exampleSequences.value.blastp);

  const blastTypes = ref([
    { value: 'blastp', label: 'BLASTP', description: 'Protein-protein BLAST: Compares an amino acid query sequence against a protein sequence database.' },
    { value: 'blastn', label: 'BLASTN', description: 'Nucleotide-nucleotide BLAST: Compares a nucleotide query sequence against a nucleotide sequence database.' },
    { value: 'blastx', label: 'BLASTX', description: 'Translated query protein-nucleotide BLAST: Compares a nucleotide query sequence translated in all reading frames against a protein sequence database.' },
    { value: 'tblastn', label: 'TBLASTN', description: 'Protein-nucleotide translated BLAST: Compares a protein query sequence against a nucleotide sequence database dynamically translated in all reading frames.' },
    { value: 'tblastx', label: 'TBLASTX', description: 'Translated query-translated database BLAST: Compares a nucleotide query sequence translated in all reading frames against a nucleotide sequence database dynamically translated in all reading frames.' }
  ]);

  const databaseTypes = ref({
    blastp: [{ value: 'protein', label: 'Protein' }],
    blastn: [{ value: 'genome', label: 'Genome' }, { value: 'cds', label: 'CDS' }, { value: 'mrna', label: 'mRNA' }],
    blastx: [{ value: 'protein', label: 'Protein' }],
    tblastn: [{ value: 'genome', label: 'Genome' }, { value: 'cds', label: 'CDS' }, { value: 'mrna', label: 'mRNA' }],
    tblastx: [{ value: 'genome', label: 'Genome' }, { value: 'cds', label: 'CDS' }, { value: 'mrna', label: 'mRNA' }]
  });

  // --- Actions ---

  /**
   * 提交BLAST任务
   */
  const submitBlast = async () => {
    if (!sequence.value.trim()) {
      if (activeTask.value) {
        const task = activeTask.value as any;
        if (task.error) {
          task.error.value = 'Please enter a sequence.';
        }
      }
      return;
    }

    const blastType = selectedBlastType.value;
    const endpoint = `/CottonOGD_api/blast_cmd/`;

    console.log('selecthenome', selectedGenomes);
    // 处理基因组ID格式，确保与数据库目录名称匹配
    // 移除括号和括号内的内容，例如将 G.hirsutum(AD1)TM-1_HAU_v1.1 转换为 G.hirsutumAD1_TM-1_HAU_v1.1
    const processedGenome = selectedGenomes.value;
    
      console.log('Processed genome:', processedGenome);
    
    const payload = {
      sequence: sequence.value,
      blast_type: blastType,
      selected_genomes: processedGenome,
      data_type: selectedDatabaseType.value,
      evalue: evalue.value.toString(),
      max_target_seqs: maxTargetSeqs.value.toString(),
      word_size: wordSize.value,
      match_score: matchScore.value,
      gap_open: gapOpen.value,
      gap_extend: gapExtend.value,
      low_complexity_filter: lowComplexityFilter.value,
    };
    console.log('payload:', payload);

    try {
      const response = await httpInstance.post(endpoint, payload);
      console.log('response:', response);
      
      if (response) {
        // 尝试获取结果数据（支持多种响应格式）
        let results = null;
        
        // 检查是否有固定的 results 字段
        if (response.results) {
          results = response.results;
        } 
        // 检查是否有以基因组名称为键的字段
        else if (processedGenome && response[processedGenome]) {
          results = response[processedGenome];
        }
        // 检查是否直接在 data 中
        else {
          results = response;
        }
        
        if (results) {
          // 使用navigationStore存储结果，确保页面跳转后仍然可用
          const navigationStore = useNavigationStore();
          navigationStore.setNavigationData('blast', {
            results: results,
            blastType: blastType
          });
          console.log('Results stored in navigationStore:', results);
          
          // 同时存储到activeTask中，供组件使用
          setBlastResults(results);
          console.log('Results stored in activeTask:', results);
          
          // 跳转到结果页面，不需要传递结果数据
          console.log('Navigating to blastpResults');
          router.push({
            name: 'blastpResults'
          });
        } else {
          throw new Error('Invalid response from server.');
        }
      } else {
        throw new Error('Invalid response from server.');
      }
    } catch (e: any) {
      console.error('BLAST submission failed:', e);
    }
  };

  /**
   * 检查BLAST任务的结果（轮询）
   * @param taskId - 任务ID
   * @param blastType - BLAST类型
   */
  const pollBlastResults = async (taskId: string, blastType: BlastType) => {
    const startEndpoint = `/CottonOGD_api/blast_cmd/`;
    const resultEndpoint = `/CottonOGD_api/blast_cmd/`;

    const task = useAsyncTask(startEndpoint, resultEndpoint);
    activeTask.value = task;

    await task.poll(taskId);
  };


  /**
   * 重置表单到初始状态
   */
  const resetForm = () => {
    sequence.value = '';
    evalue.value = 0.01;
    maxTargetSeqs.value = 30;
    selectedBlastType.value = 'blastp';
    selectedDatabaseType.value = 'protein';
    if (activeTask.value) {
      const task = activeTask.value as any;
      if (task.error) {
        task.error.value = null;
      }
      if (task.data) {
        task.data.value = null;
      }
    }
    setDefaultGenomes([]);
  };

  /**
   * 设置默认选中的基因组
   * @param genomeOptions - 从genomeStore获取的基因组选项
   */
  const setDefaultGenomes = (genomeOptions: readonly any[]) => {
    const defaultGenome = 'G.hirsutumAD1_TM-1_HAU_v1.1';
    let found = false;

    if (genomeOptions && genomeOptions.length > 0) {
        for (const group of genomeOptions) {
            if (group && group.children) {
                for (const genome of group.children) {
                    if (genome && genome.value === defaultGenome) {
                        selectedGenomes.value = defaultGenome;
                        found = true;
                        break;
                    }
                }
            }
            if (found) break;
        }

        if (!found) {
            const firstGroup = genomeOptions[0];
            if (firstGroup && firstGroup.children && firstGroup.children.length > 0) {
                const firstChild = firstGroup.children[0] as { value: string };
                if (firstChild && firstChild.value) {
                    selectedGenomes.value = firstChild.value;
                }
            }
        }
    } else {
        selectedGenomes.value = defaultGenome;
    }
  };


  /**
   * 加载示例序列
   */
  const fillExample = () => {
    sequence.value = exampleSequences.value[selectedBlastType.value] || exampleSequences.value.blastp;
  };

  /**
   * 直接设置BLAST结果
   * @param results - BLAST结果数据
   */
  const setBlastResults = (results: any) => {
    // 现在我们在结果页面中直接处理结果
    // 这里只需要存储到activeTask中，供组件使用
    if (activeTask.value) {
      const task = activeTask.value as any;
      if (task.data) {
        task.data.value = results;
      }
    }
  };

  return {
    // State
    sequence,
    evalue,
    maxTargetSeqs,
    selectedBlastType,
    selectedDatabaseType,
    selectedGenomes,
    // Computed State from Task
    loading,
    error,
    blastResults,
    // Static Data
    blastTypes,
    databaseTypes,
    exampleSequence,
    exampleSequences,
    // Advanced Parameters
    wordSize,
    matchScore,
    gapOpen,
    gapExtend,
    lowComplexityFilter,
    showAdvancedParams,
    // Actions
    submitBlast,
    pollBlastResults,
    resetForm,
    setBlastResults,
    setDefaultGenomes,
    fillExample,
  };
});

