import { path } from 'd3'
import { createRouter, createWebHistory } from 'vue-router'

// Common views
const HomeView = () => import('@/views/common/HomeView.vue')
const AboutView = () => import('@/views/common/AboutView.vue')
const Contact_usView = () => import('@/views/common/Contact_usView.vue')
const DownloadView = () => import('@/views/common/DownloadView.vue')
const PlaceholderView = () => import('@/views/common/PlaceholderView.vue')

// Genome module
const BrowseGenomeView = () => import('@/views/genome/BrowseGenomeView.vue')
const GenomeDetailView = () => import('@/views/genome/GenomeDetailView.vue')
const JbrowseView = () => import('@/views/genome/JbrowseView.vue')
const IGVView = () => import('@/views/genome/IGVView.vue')
const GenomeSyntenyView = () => import('@/views/genome/GenomeSyntenyView.vue')
const GeneLocationView = () => import('@/views/genome/GeneLocationView.vue')

// Annotation module
const GoAnnotationView = () => import('@/views/annotation/GoAnnotationView.vue')
const GoAnnotationResultView = () => import('@/views/annotation/GoAnnotationResultView.vue')
const KeggAnnotationView = () => import('@/views/annotation/KeggAnnotationView.vue')
const KeggAnnotationResultView = () => import('@/views/annotation/KeggAnnotationResultView.vue')

// Enrichment module
const GoEnrichmentView = () => import('@/views/enrichment/GoEnrichmentView.vue')
const GoEnrichmentResultView = () => import('@/views/enrichment/GoEnrichmentResultView.vue')
const KeggEnrichmentView = () => import('@/views/enrichment/KeggEnrichmentView.vue')
const KeggEnrichmentResultView = () => import('@/views/enrichment/KeggEnrichmentResultView.vue')

// Expression module
const GeneExpressionView = () => import('@/views/expression/GeneExpressionView.vue')
const GeneExpressionResultView = () => import('@/views/expression/GeneExpressionResultView.vue')
const GeneExpressionEfpView = () => import('@/views/expression/GeneExpressionEfpView.vue')

// Sequence module
const IdSearchView = () => import('@/views/sequence/IdSearchView.vue')
const IdSearchResultsView = () => import('@/views/sequence/IdSearchResultsView.vue')
const IdSearchSummaryView = () => import('@/views/sequence/IdSearchSummaryView.vue')
const BlastpView = () => import('@/views/sequence/BlastpView.vue')
const BlastpResultView = () => import('@/views/sequence/BlastpResultView.vue')
const RegionSearchView = () => import('@/views/sequence/RegionSearchView.vue')
const SequenceServerView = () => import('@/views/sequence/sequence-server.vue')

// Visualization module
const CircosView = () => import('@/views/visualization/CircosView.vue')
const PhylotreeView = () => import('@/views/visualization/PhylotreeView.vue')
const PPIView = () => import('@/views/visualization/PPIView.vue')
const Clustergramme_heatmapView = () => import('@/views/visualization/Clustergramme_heatmap.vue')
const CanvaspressView = () => import('@/views/visualization/CanvaspressView.vue')

// Tools module
const TFView = () => import('@/views/tools/TFView.vue')
const TRView = () => import('@/views/tools/TRView.vue')
const PrimerView = () => import('@/views/tools/PrimerView.vue')

const TreeView = () => import('@/views/test/tree.vue')



//简单的占位组件
const SimpleView = { 
  props: ['title'],
  template: `<div class="container mt-4">
    <h1>{{ title }}</h1>
    <p>此页面正在开发中...</p>
  </div>`
}

const routes = [
  // Common routes
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/about',
    name: 'about',
    component: AboutView
  },
  {
    path: '/contact',
    name: 'contact',
    component: Contact_usView
  },
  {
    path: '/download',
    name: 'download',
    component: DownloadView
  },

  // Genome browser routes (with redirects for backward compatibility)
  {
    path: '/genome/browse',
    name: 'BrowseGenome',
    component: BrowseGenomeView
  },
  {
    path: '/species',
    redirect: '/species/diploid'
  },
  {
    path: '/species/diploid',
    name: 'DiploidSpecies',
    component: BrowseGenomeView,
    meta: { ploidy: 'Diploid' }
  },
  {
    path: '/species/tetraploid',
    name: 'TetraploidSpecies',
    component: BrowseGenomeView,
    meta: { ploidy: 'Tetraploid' }
  },
  {
    path: '/genome/detail/:key',
    name: 'GenomeDetail',
    component: GenomeDetailView,
    props: true,
  },
  {
    path: '/genome/jbrowse',
    name: 'jbrowse',
    component: JbrowseView
  },
  {
    path: '/genome/igv',
    name: 'IGV',
    component: IGVView
  },
  {
    path: '/genome/synteny',
    name: 'GenomeSynteny',
    component: GenomeSyntenyView
  },
  {
    path: '/genome/gene-location',
    name: 'GeneLocation',
    component: GeneLocationView
  },

  // Browse routes (legacy - will redirect to new paths)
  {
    path: '/browse/genome',
    redirect: '/genome/browse'
  },
  {
    path: '/browse/tf',
    name: 'BrowseTF',
    component: TFView
  },
  {
    path: '/browse/tr',
    name: 'BrowseTR',
    component: TRView
  },
  {
    path: '/browse/species',
    redirect: '/species/diploid'
  },

  // Sequence analysis routes
  {
    path: '/sequence/search',
    name: 'idSearch',
    component: IdSearchView
  },
  {
    path: '/sequence/search/results',
    name: 'idSearchResults',
    component: IdSearchResultsView
  },
  {
    path: '/sequence/search/summary',
    name: 'idSearchSummary',
    component: IdSearchSummaryView
  },
  {
    path: '/sequence/blast',
    name: 'Blastp',
    component: BlastpView
  },
  {
    path: '/sequence/blast/results',
    name: 'blastpResults',
    component: BlastpResultView
  },
  {
    path: '/sequence/region',
    name: 'RegionSearch',
    component: RegionSearchView
  },
  {
    path: '/sequence/server',
    name: 'SequenceServer',
    component: SequenceServerView
  },

  // Legacy sequence routes (redirects)
  {
    path: '/tools/id-search',
    redirect: '/sequence/search'
  },
  {
    path: '/tools/id-search/results',
    redirect: '/sequence/search/results'
  },
  {
    path: '/tools/id-search/id-search-summary/',
    redirect: '/sequence/search/summary'
  },
  {
    path: '/tools/blastp',
    redirect: '/sequence/blast'
  },
  {
    path: '/tools/blastp/results',
    redirect: '/sequence/blast/results'
  },
  {
    path: '/tools/region-search',
    redirect: '/sequence/region'
  },
  {
    path: '/tools/sequence-server',
    redirect: '/sequence/server'
  },

  // Annotation routes
  {
    path: '/annotation/go',
    name: 'GoAnnotation',
    component: GoAnnotationView
  },
  {
    path: '/annotation/go/results',
    name: 'goAnnotationResults',
    component: GoAnnotationResultView
  },
  {
    path: '/annotation/kegg',
    name: 'KeggAnnotation',
    component: KeggAnnotationView
  },
  {
    path: '/annotation/kegg/results',
    name: 'KeggAnnotationResults',
    component: KeggAnnotationResultView
  },

  // Legacy annotation routes (redirects)
  {
    path: '/tools/go-annotation',
    redirect: '/annotation/go'
  },
  {
    path: '/tools/go-annotation/results',
    redirect: '/annotation/go/results'
  },
  {
    path: '/tools/kegg-annotation',
    redirect: '/annotation/kegg'
  },
  {
    path: '/tools/kegg-annotation/results',
    redirect: '/annotation/kegg/results'
  },

  // Enrichment routes
  {
    path: '/enrichment/go',
    name: 'GoEnrichment',
    component: GoEnrichmentView
  },
  {
    path: '/enrichment/go/results',
    name: 'goEnrichmentResults',
    component: GoEnrichmentResultView
  },
  {
    path: '/enrichment/kegg',
    name: 'KeggEnrichment',
    component: KeggEnrichmentView
  },
  {
    path: '/enrichment/kegg/results',
    name: 'KeggEnrichmentResults',
    component: KeggEnrichmentResultView
  },

  // Legacy enrichment routes (redirects)
  {
    path: '/tools/go-enrichment',
    redirect: '/enrichment/go'
  },
  {
    path: '/tools/go-enrichment/results',
    redirect: '/enrichment/go/results'
  },
  {
    path: '/tools/kegg-enrichment',
    redirect: '/enrichment/kegg'
  },
  {
    path: '/tools/kegg-enrichment/results',
    redirect: '/enrichment/kegg/results'
  },

  // Expression routes
  {
    path: '/expression/gene',
    name: 'GeneExpression',
    component: GeneExpressionView
  },
  {
    path: '/expression/gene/results',
    name: 'geneExpressionResults',
    component: GeneExpressionResultView
  },
  {
    path: '/expression/efp',
    name: 'GeneExpressionEfp',
    component: GeneExpressionEfpView
  },

  // Legacy expression routes (redirects)
  {
    path: '/tools/gene-expression',
    redirect: '/expression/gene'
  },
  {
    path: '/tools/gene-expression/results',
    redirect: '/expression/gene/results'
  },
  {
    path: '/tools/gene-expression-efp',
    redirect: '/expression/efp'
  },

  // Visualization routes
  {
    path: '/visualization/circos',
    name: 'Circos',
    component: CircosView
  },
  {
    path: '/visualization/phylotree',
    name: 'Phylotree',
    component: PhylotreeView
  },
  {
    path: '/visualization/ppi',
    name: 'PPI',
    component: PPIView
  },
  {
    path: '/visualization/heatmap',
    name: 'Clustergramme_heatmap',
    component: Clustergramme_heatmapView
  },
  {
    path: '/visualization/canvaspress',
    name: 'Canvaspress',
    component: CanvaspressView
  },

  // Legacy visualization routes (redirects)
  {
    path: '/tools/circos',
    redirect: '/visualization/circos'
  },
  {
    path: '/tools/phylotree',
    redirect: '/visualization/phylotree'
  },
  {
    path: '/tools/ppi',
    redirect: '/visualization/ppi'
  },
  {
    path: '/tools/clustergramme_heatmap',
    redirect: '/visualization/heatmap'
  },
  {
    path: '/tools/canvaspress',
    redirect: '/visualization/canvaspress'
  },
  {
    path: '/tools/heatmap',
    redirect: '/visualization/heatmap'
  },

  // Tools routes
  {
    path: '/tools/primer-design',
    name: 'PrimerDesign',
    component: PrimerView
  },

  // Placeholder routes for future features
  {
    path: '/tools/ks-calculator',
    name: 'KsCalculator',
    component: PlaceholderView,
    props: { title: 'KS Calculator' }
  },
  {
    path: '/tools/orthogroup',
    name: 'Orthogroup',
    component: PlaceholderView,
    props: { title: 'Orthogroup Analysis' }
  },
  {
    path: '/tools/msa',
    name: 'Msa',
    component: PlaceholderView,
    props: { title: 'Multiple Sequence Alignment' }
  },
  {
    path: '/test/protein-viewer',
    name: 'ProteinViewerTest',
    component: () => import('@/views/test/ProteinViewerTest.vue')
  },
  {
    path: '/test/tianditu-map',
    name: 'TiandituMapTest',
    component: () => import('@/views/test/TiandituMapTest.vue')
  },
  {
    path: '/test/tree',
    name: 'tree',
    component: () => import('@/views/test/tree.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes
})

export default router
