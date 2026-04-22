import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import BrowseGenomeView from '@/views/BrowseGenomeView.vue'
import IdSearchView from '@/views/IdSearchView.vue'
import IdSearchResultsView from '@/views/IdSearchResultsView.vue'
import IdSearchSummaryView from '@/views/IdSearchSummaryView.vue'
import JbrowseView from '@/views/JbrowseView.vue'
import IGVView from '@/views/IGVView.vue'
import DownloadView from '@/views/DownloadView.vue'
import Contact_usView from '@/views/Contact_usView.vue'
import AboutView from '@/views/AboutView.vue'
import BlastpView from '@/views/BlastpView.vue'
import BlastpResultView from '@/views/BlastpResultView.vue'
import GoEnrichmentView from '@/views/GoEnrichmentView.vue'
import GoEnrichmentResultView from '@/views/GoEnrichmentResultView.vue'
import GoAnnotationView from '@/views/GoAnnotationView.vue'
import GoAnnotationResultView from '@/views/GoAnnotationResultView.vue'
import GeneExpressionView from '@/views/GeneExpressionView.vue'
import GeneExpressionResultView from '@/views/GeneExpressionResultView.vue'
import GeneExpressionEfpView from '@/views/GeneExpressionEfpView.vue'
import KeggAnnotationView from '@/views/KeggAnnotationView.vue'
import KeggAnnotationResultView from '@/views/KeggAnnotationResultView.vue'
import KeggEnrichmentView from '@/views/KeggEnrichmentView.vue'
import KeggEnrichmentResultView from '@/views/KeggEnrichmentResultView.vue'
import TFView from '@/views/TFView.vue'
import TRView from '@/views/TRView.vue'
import PrimerView from '@/views/PrimerView.vue'
import Clustergramme_heatmapView from '@/views/Clustergramme_heatmap.vue'
import PPIView from '@/views/PPIView.vue'
import PhylotreeView from '@/views/PhylotreeView.vue'
import CircosView from '@/views/CircosView.vue'
import CanvaspressView from '@/views/CanvaspressView.vue'
import SequenceServerView from '@/views/sequence-server.vue'



//简单的占位组件
const SimpleView = { 
  props: ['title'],
  template: `<div class="container mt-4">
    <h1>{{ title }}</h1>
    <p>此页面正在开发中...</p>
  </div>`
}

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/browse/genome',
    name: 'BrowseGenome',
    component: BrowseGenomeView
  },
  {
    path: '/browse/species',
    name: 'BrowseSpecies',
    component: () => ({ ...SimpleView, propsData: { title: 'Browse Species' } })
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
    path: '/jbrowse',
    name: 'jbrowse',
    component: JbrowseView
  },
  {
    path: '/IGV',
    name: 'IGV',
    component: IGVView
  },
  {    path: '/tools/id-search',
    name: 'idSearch',
    component: IdSearchView
  },
  {    path: '/tools/id-search/results',
    name: 'idSearchResults',
    component: IdSearchResultsView
  },
  {    path: '/tools/id-search/id-search-summary/',
    name: 'idSearchSummary',
    component: IdSearchSummaryView
  },
  // 其他工具页面使用简单占位组件
  {
    path: '/tools/blastp',
    name: 'Blastp',
    component: BlastpView
  },
  {
    path: '/tools/blastp/results',
    name: 'blastpResults',
    component: BlastpResultView
  },
  {
    path: '/tools/go-enrichment',
    name: 'GoEnrichment',
    component: GoEnrichmentView
  },
  {
    path: '/tools/go-enrichment/results',
    name: 'goEnrichmentResults',
    component: GoEnrichmentResultView
  },
  {
    path: '/tools/go-annotation',
    name: 'GoAnnotation',
    component: GoAnnotationView
  },
  {
    path: '/tools/go-annotation/results',
    name: 'goAnnotationResults',
    component: GoAnnotationResultView
  },
  {    path: '/tools/kegg-annotation',
    name: 'KeggAnnotation',
    component: KeggAnnotationView
  },
  {    path: '/tools/kegg-annotation/results',
    name: 'KeggAnnotationResults',
    component: KeggAnnotationResultView
  },
  {    path: '/tools/kegg-enrichment',
    name: 'KeggEnrichment',
    component: KeggEnrichmentView
  },
  {    path: '/tools/kegg-enrichment/results',
    name: 'KeggEnrichmentResults',
    component: KeggEnrichmentResultView
  },
  {
    path: '/tools/heatmap',
    name: 'Heatmap',
    component: () => ({ ...SimpleView, propsData: { title: 'Heatmap Analysis' } })
  },
  {    path: '/tools/gene-expression',
    name: 'GeneExpression',
    component: GeneExpressionView
  },
  {    path: '/tools/gene-expression/results',
    name: 'geneExpressionResults',
    component: GeneExpressionResultView
  },
  {    path: '/tools/gene-expression-efp',
    name: 'GeneExpressionEfp',
    component: GeneExpressionEfpView
  },
  {
    path: '/tools/primer-design',
    name: 'PrimerDesign',
    component: PrimerView
  },
  {
    path: '/tools/ks-calculator',
    name: 'KsCalculator',
    component: () => ({ ...SimpleView, propsData: { title: 'KS Calculator' } })
  },
  {
    path: '/tools/ks-calculator/results',
    name: 'KsCalculatorResults',
    component: () => ({ ...SimpleView, propsData: { title: 'KS Calculator Results' } })
  },
  {
    path: '/tools/orthogroup',
    name: 'Orthogroup',
    component: () => ({ ...SimpleView, propsData: { title: 'Orthogroup Analysis' } })
  },
  {
    path: '/tools/orthogroup/results',
    name: 'OrthogroupResults',
    component: () => ({ ...SimpleView, propsData: { title: 'Orthogroup Analysis Results' } })
  },
  {
    path: '/tools/msa',
    name: 'Msa',
    component: () => ({ ...SimpleView, propsData: { title: '多序列比对' } })
  },
  {
    path: '/tools/msa/results',
    name: 'MsaResults',
    component: () => ({ ...SimpleView, propsData: { title: '多序列比对结果' } })
  },
  {
    path: '/tools/clustergramme_heatmap',
    name: 'Clustergramme_heatmap',
    component: Clustergramme_heatmapView
  },
  {
    path: '/tools/ppi',
    name: 'PPI',
    component: PPIView
  },
  {
    path: '/tools/phylotree',
    name: 'Phylotree',
    component: PhylotreeView
  },
  {
    path: '/tools/circos',
    name: 'Circos',
    component: CircosView
  },
  {
    path: '/tools/canvaspress',
    name: 'Canvaspress',
    component: CanvaspressView
  },
  {
    path: '/tools/sequence-server',
    name: 'SequenceServer',
    component: SequenceServerView
  },
  {
    path: '/download',
    name: 'Download',
    component: DownloadView
  },
  {
    path: '/contact-us',
    name: 'Contact_us',
    component: Contact_usView
  },
  {    
    path: '/about-us',
    name: 'About_us',
    component: AboutView
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes
})

export default router
