import { computed, ref } from 'vue'
import { useGenomeStore } from '@/stores/genome_info'

const DEFAULT_GENOME = 'G.hirsutumAD1_TM-1_HAU_v1.1'
const DEFAULT_CASCADER_PROPS = {
  multiple: false,
  checkStrictly: false,
  expandTrigger: 'click',
  showAllLevels: false
} as const

export interface GenomeDataPaths {
  fastaURL: string
  faiURL: string
  gffURL: string
  gffIndexURL: string
}

export const buildGenomeDataPaths = (genomeName: string): GenomeDataPaths => ({
  fastaURL: `/data/genome/${genomeName}/${genomeName}.genome.fa.gz`,
  faiURL: `/data/genome/${genomeName}/${genomeName}.genome.fa.gz.fai`,
  gffURL: `/data/genome/${genomeName}/${genomeName}.gff.gz`,
  gffIndexURL: `/data/genome/${genomeName}/${genomeName}.gff.gz.tbi`
})

export const getFirstChromosomeFromFai = async (genomeName: string, fallback = 'chr1') => {
  const { faiURL } = buildGenomeDataPaths(genomeName)
  try {
    const response = await fetch(faiURL)
    if (!response.ok) return fallback

    const text = await response.text()
    const firstLine = text.trim().split('\n')[0] || ''
    const chromosome = firstLine.split('\t')[0] || ''
    return chromosome || fallback
  } catch {
    return fallback
  }
}

export const createDefaultLocus = async (
  genomeName: string,
  range = '1-1000000',
  fallbackChromosome = 'chr1'
) => {
  const chromosome = await getFirstChromosomeFromFai(genomeName, fallbackChromosome)
  return `${chromosome}:${range}`
}

export const useGenomeSelector = (preferredGenome = DEFAULT_GENOME) => {
  const genomeStore = useGenomeStore()
  const selectedGenome = ref<string[]>([])
  const cascaderProps = ref({ ...DEFAULT_CASCADER_PROPS })

  const genomeOptions = computed(() => genomeStore.genomeOptions)
  const genomeLoading = computed(() => genomeStore.loading)
  const allGenomes = computed(() =>
    genomeOptions.value.flatMap((group) => (group.children || []).map((item) => item.value))
  )
  const selectedGenomeName = computed(() => {
    if (!selectedGenome.value.length) return ''
    return selectedGenome.value[selectedGenome.value.length - 1]
  })

  const ensureGenomesLoaded = async () => {
    if (!genomeStore.genomeOptions.length) {
      await genomeStore.fetchGenomes()
    }
  }

  const pickDefaultGenome = () => {
    if (allGenomes.value.includes(preferredGenome)) return preferredGenome
    return allGenomes.value[0] || ''
  }

  const setSelectedGenome = (genomeName: string) => {
    selectedGenome.value = genomeName ? [genomeName] : []
  }

  const extractGenomeName = (value?: string[]) => {
    if (!value || !value.length) return ''
    return value[value.length - 1]
  }

  return {
    genomeStore,
    selectedGenome,
    selectedGenomeName,
    genomeOptions,
    genomeLoading,
    cascaderProps,
    allGenomes,
    ensureGenomesLoaded,
    pickDefaultGenome,
    setSelectedGenome,
    extractGenomeName
  }
}

