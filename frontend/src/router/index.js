import { createRouter, createWebHistory } from 'vue-router'

// Common views
import HomeView from '@/views/common/HomeView.vue'
import AboutView from '@/views/common/AboutView.vue'
import Contact_usView from '@/views/common/Contact_usView.vue'
import DownloadView from '@/views/common/DownloadView.vue'
import PlaceholderView from '@/views/common/PlaceholderView.vue'

// Genome module
import BrowseGenomeView from '@/views/genome/BrowseGenomeView.vue'
import JbrowseView from '@/views/genome/JbrowseView.vue'
import IGVView from '@/views/genome/IGVView.vue'
import GenomeSyntenyView from '@/views/genome/GenomeSyntenyView.vue'
import GeneLocationView from '@/views/genome/GeneLocationView.vue'

// Annotation module
import GoAnnotationView from '@/views/annotation/GoAnnotationView.vue'
import GoAnnotationResultView from '@/views/annotation/GoAnnotationResultView.vue'
import KeggAnnotationView from '@/views/annotation/KeggAnnotationView.vue'
import KeggAnnotationResultView from '@/views/annotation/KeggAnnotationResultView.vue'

// Enrichment module
import GoEnrichmentView from '@/views/enrichment/GoEnrichmentView.vue'
import GoEnrichmentResultView from '@/views/enrichment/GoEnrichmentResultView.vue'
import KeggEnrichmentView from '@/views/enrichment/KeggEnrichmentView.vue'
import KeggEnrichmentResultView from '@/views/enrichment/KeggEnrichmentResultView.vue'

// Expression module
import GeneExpressionView from '@/views/expression/GeneExpressionView.vue'
import GeneExpressionResultView from '@/views/expression/GeneExpressionResultView.vue'
import GeneExpressionEfpView from '@/views/expression/GeneExpressionEfpView.vue'

// Sequence module
import IdSearchView from '@/views/sequence/IdSearchView.vue'
import IdSearchResultsView from '@/views/sequence/IdSearchResultsView.vue'
import IdSearchSummaryView from '@/views/sequence/IdSearchSummaryView.vue'
import BlastpView from '@/views/sequence/BlastpView.vue'
import BlastpResultView from '@/views/sequence/BlastpResultView.vue'
import RegionSearchView from '@/views/sequence/RegionSearchView.vue'
import SequenceServerView from '@/views/sequence/sequence-server.vue'

// Visualization module
import CircosView from '@/views/visualization/CircosView.vue'
import PhylotreeView from '@/views/visualization/PhylotreeView.vue'
import PPIView from '@/views/visualization/PPIView.vue'
import Clustergramme_heatmapView from '@/views/visualization/Clustergramme_heatmap.vue'
import CanvaspressView from '@/views/visualization/CanvaspressView.vue'

// Tools module
import TFView from '@/views/tools/TFView.vue'
import TRView from '@/views/tools/TRView.vue'
import PrimerView from '@/views/tools/PrimerView.vue'



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
    redirect: '/genome/browse'
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
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes
})

export default router
