<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ArrowDown, Setting, ArrowRight } from '@element-plus/icons-vue'
import { searchGenes } from '@/utils/meilisearch.js'

const searchQuery = ref('')
const selectedDatabase = ref('all')
const router = useRouter()
const showAdvancedSearch = ref(false)
const currentBgIndex = ref(0)
const bgGradients = [
  'linear-gradient(135deg, rgba(58, 110, 165, 0.95) 0%, rgba(114, 151, 189, 0.95) 100%)',
  'linear-gradient(135deg, rgba(70, 102, 134, 0.95) 0%, rgba(90, 129, 168, 0.95) 100%)',
  'linear-gradient(135deg, rgba(47, 95, 148, 0.95) 0%, rgba(58, 110, 165, 0.95) 100%)',
]
let bgInterval: number | null = null

onMounted(() => {
  bgInterval = window.setInterval(() => {
    currentBgIndex.value = (currentBgIndex.value + 1) % bgGradients.length
  }, 8000)
})
onUnmounted(() => { if (bgInterval) clearInterval(bgInterval) })

const advancedOptions = reactive({
  genomeId: '', geneFamily: '', chromosome: '',
  startPosition: null as number | null, endPosition: null as number | null, exactMatch: false
})

const databaseOptions = [
  { label: 'All Databases', value: 'all' }, { label: 'Gene', value: 'gene' },
  { label: 'Protein', value: 'protein' }, { label: 'Genome', value: 'genome' },
  { label: 'Orthogroup', value: 'orthogroup' }, { label: 'Expression', value: 'expression' }
]
const genomeOptions = [
  { label: 'All Genomes', value: '' }, { label: 'G. hirsutum (AD1)', value: 'Ghirsutum' },
  { label: 'G. barbadense (AD2)', value: 'Gbarbadense' },
  { label: 'G. arboreum (A2)', value: 'Garboreum' }, { label: 'G. raimondii (D5)', value: 'Graimondii' }
]
const geneFamilyOptions = [
  { label: 'All Families', value: '' }, { label: 'Transcription Factors', value: 'TF' },
  { label: 'Transposable Elements', value: 'TE' }, { label: 'Kinase', value: 'kinase' },
  { label: 'Transporter', value: 'transporter' }
]

const performSearch = async () => {
  if (!searchQuery.value.trim()) return
  const searchParams: any = { q: searchQuery.value.trim(), database: selectedDatabase.value, limit: 20 }
  if (showAdvancedSearch.value) {
    if (advancedOptions.genomeId) searchParams.genome_id = advancedOptions.genomeId
    if (advancedOptions.geneFamily) searchParams.gene_family = advancedOptions.geneFamily
    if (advancedOptions.chromosome) searchParams.chromosome = advancedOptions.chromosome
    if (advancedOptions.startPosition !== null) searchParams.start = advancedOptions.startPosition
    if (advancedOptions.endPosition !== null) searchParams.end = advancedOptions.endPosition
    searchParams.exact_match = advancedOptions.exactMatch
  }
  if (selectedDatabase.value === 'all' || selectedDatabase.value === 'gene') {
    try {
      const results = await searchGenes(searchQuery.value.trim(), { limit: 20, genome_id: advancedOptions.genomeId || undefined })
      if (results.success && results.total > 0) {
        router.push({ path: '/sequence/search/results', query: { q: searchQuery.value.trim(), source: 'meilisearch', ...searchParams } })
        return
      }
    } catch (error) { console.error('Search failed:', error) }
  }
  router.push({ path: '/sequence/search/results', query: searchParams })
}
const fillExample = (ex: string) => { searchQuery.value = ex }
const toggleAdvancedSearch = () => { showAdvancedSearch.value = !showAdvancedSearch.value }
const clearAdvancedOptions = () => {
  Object.assign(advancedOptions, { genomeId: '', geneFamily: '', chromosome: '', startPosition: null, endPosition: null, exactMatch: false })
}
</script>

<template>
  <div class="home-modern">
    <section class="hero-section">
      <div class="hero-bg" :style="{ background: bgGradients[currentBgIndex] }">
        <div class="particles">
          <div class="particle" v-for="n in 20" :key="n" :style="{ left: `${Math.random() * 100}%`, animationDelay: `${Math.random() * 5}s` }"></div>
        </div>
      </div>
      <div class="container">
        <div class="hero-content animate-fade-in">
          <div class="hero-badge"><span>Cotton Genomics Database</span></div>
          <h1 class="hero-title">{{ t('welcome_to_cottonogd') }}</h1>
          <p class="hero-subtitle">{{ t('a_comprehensive_cotton_orthogroups_database') }}</p>
          <p class="hero-desc">{{ t('cottonogd_description') }}</p>
          <div class="search-box">
            <div class="search-row">
              <el-select v-model="selectedDatabase" class="db-select" size="large" placeholder="Database">
                <el-option v-for="opt in databaseOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
              <el-input v-model="searchQuery" placeholder="Search genes, proteins, genomes..." clearable size="large" @keyup.enter="performSearch" class="search-input">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-button type="primary" size="large" @click="performSearch" class="search-btn">
                <el-icon><Search /></el-icon>{{ t('search') }}
              </el-button>
            </div>
            <div class="advanced-toggle">
              <el-button type="text" size="small" @click="toggleAdvancedSearch">
                <el-icon><Setting /></el-icon> Advanced Search <el-icon :class="{ rotate: showAdvancedSearch }"><ArrowDown /></el-icon>
              </el-button>
            </div>
            <el-collapse-transition>
              <div v-show="showAdvancedSearch" class="advanced-panel">
                <el-divider />
                <div class="filters">
                  <div class="filter-row">
                    <div class="filter-item"><label>Genome</label><el-select v-model="advancedOptions.genomeId" placeholder="All" clearable><el-option v-for="opt in genomeOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select></div>
                    <div class="filter-item"><label>Gene Family</label><el-select v-model="advancedOptions.geneFamily" placeholder="All" clearable><el-option v-for="opt in geneFamilyOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select></div>
                    <div class="filter-item"><label>Chromosome</label><el-input v-model="advancedOptions.chromosome" placeholder="e.g., A01" clearable /></div>
                  </div>
                  <div class="actions"><el-button type="primary" @click="performSearch">Search</el-button><el-button @click="clearAdvancedOptions">Clear</el-button></div>
                </div>
              </div>
            </el-collapse-transition>
            <div class="search-hints"><span>Try:</span><el-tag size="small" @click="fillExample('Ghir_A01G000100')">Ghir_A01G000100</el-tag><el-tag size="small" @click="fillExample('Transcription Factor')">Transcription Factor</el-tag></div>
          </div>
        </div>
      </div>
      <div class="bg-indicators">
        <div v-for="(bg, i) in bgGradients" :key="i" class="indicator" :class="{ active: i === currentBgIndex }" @click="currentBgIndex = i"></div>
      </div>
      <div class="scroll-hint"><div class="mouse"><div class="wheel"></div></div><p>Scroll to explore</p></div>
    </section>
    <section class="stats-section">
      <div class="container">
        <h2 class="section-title">{{ t('database_statistics') }}</h2>
        <div class="stats-grid">
          <div class="stat-card animate-slide-in" style="animation-delay: 0.1s"><div class="stat-icon gradient-blue"><i class="fas fa-dna"></i></div><div class="stat-value">200+</div><div class="stat-label">Genomes</div></div>
          <div class="stat-card animate-slide-in" style="animation-delay: 0.2s"><div class="stat-icon gradient-green"><i class="fas fa-gene"></i></div><div class="stat-value">200K+</div><div class="stat-label">Annotated Genes</div></div>
          <div class="stat-card animate-slide-in" style="animation-delay: 0.3s"><div class="stat-icon gradient-orange"><i class="fas fa-users"></i></div><div class="stat-value">15K+</div><div class="stat-label">Orthogroups</div></div>
          <div class="stat-card animate-slide-in" style="animation-delay: 0.4s"><div class="stat-icon gradient-purple"><i class="fas fa-book"></i></div><div class="stat-value">5K+</div><div class="stat-label">References</div></div>
        </div>
      </div>
    </section>
    <section class="features-section">
      <div class="container">
        <h2 class="section-title">{{ t('core_features') }}</h2>
        <div class="features-grid">
          <div class="feature-card animate-fade-in">
            <div class="card-image" style="background-image: url('@/assets/images/egg.jpg')"><div class="image-overlay"></div></div>
            <div class="card-body"><div class="card-icon icon-blue"><i class="fas fa-database"></i></div><h3>{{ t('browse') }}</h3><p>Explore cotton genome data through intuitive browsing interfaces.</p><router-link to="/browse/tf" class="card-link">Explore <el-icon><ArrowRight /></el-icon></router-link></div>
          </div>
          <div class="feature-card animate-fade-in" style="animation-delay: 0.2s">
            <div class="card-image" style="background-image: url('@/assets/images/mh.png')"><div class="image-overlay"></div></div>
            <div class="card-body"><div class="card-icon icon-green"><i class="fas fa-tools"></i></div><h3>Analysis Tools</h3><p>Powerful tools for sequence analysis and functional annotation.</p><router-link to="/sequence/blast" class="card-link">Start Analysis <el-icon><ArrowRight /></el-icon></router-link></div>
          </div>
          <div class="feature-card animate-fade-in" style="animation-delay: 0.4s">
            <div class="card-image" style="background-image: url('@/assets/images/screenshot-dashboard.png')"><div class="image-overlay"></div></div>
            <div class="card-body"><div class="card-icon icon-purple"><i class="fas fa-chart-pie"></i></div><h3>Visualization</h3><p>Interactive genomic data visualization with modern tools.</p><router-link to="/genome/jbrowse" class="card-link">View Data <el-icon><ArrowRight /></el-icon></router-link></div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-modern{min-height:100vh}.hero-section{position:relative;min-height:90vh;display:flex;align-items:center;overflow:hidden}.hero-bg{position:absolute;inset:0;transition:background 2s ease;z-index:0}.particles{position:absolute;inset:0;overflow:hidden}.particle{position:absolute;width:4px;height:4px;background:rgba(255,255,255,0.3);border-radius:50%;bottom:-10px;animation:float-up 15s infinite}@keyframes float-up{0%{transform:translateY(0) scale(0);opacity:0}10%,90%{opacity:1}100%{transform:translateY(-100vh) scale(1);opacity:0}}
.hero-content{position:relative;z-index:1;text-align:center;max-width:1000px;margin:0 auto;padding:60px 20px}.hero-badge{display:inline-block;background:rgba(255,255,255,0.15);backdrop-filter:blur(10px);padding:8px 20px;border-radius:50px;color:white;font-size:14px;margin-bottom:24px;border:1px solid rgba(255,255,255,0.3)}.hero-title{font-size:56px;font-weight:800;color:white;margin-bottom:16px;text-shadow:0 2px 20px rgba(0,0,0,0.3)}.hero-subtitle{font-size:24px;color:rgba(255,255,255,0.95);margin-bottom:12px;font-weight:600}.hero-desc{font-size:16px;color:rgba(255,255,255,0.85);line-height:1.8;margin-bottom:40px;max-width:800px;margin-left:auto;margin-right:auto}
.search-box{background:rgba(255,255,255,0.98);backdrop-filter:blur(20px);padding:32px;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}.search-row{display:flex;gap:12px;margin-bottom:16px}.db-select{width:160px;flex-shrink:0}.search-input{flex:1}.search-btn{background:linear-gradient(135deg,#3a6ea5,#7297bd);border:none;padding:0 32px}.advanced-toggle{text-align:left;margin-bottom:8px}.rotate{transform:rotate(180deg);transition:transform 0.3s}.advanced-panel{margin-top:16px}.filters{display:flex;flex-direction:column;gap:16px}.filter-row{display:flex;gap:16px;flex-wrap:wrap}.filter-item{flex:1;min-width:180px}.filter-item label{display:block;font-size:12px;font-weight:600;color:#495057;margin-bottom:8px;text-transform:uppercase}.actions{display:flex;gap:12px;padding-top:16px;border-top:1px solid #e9ecef}.search-hints{margin-top:16px;display:flex;align-items:center;gap:10px;font-size:14px;color:#666}.search-hints el-tag{cursor:pointer;transition:all 0.3s}.search-hints el-tag:hover{transform:translateY(-2px)}
.bg-indicators{position:absolute;bottom:100px;left:50%;transform:translateX(-50%);display:flex;gap:12px;z-index:1}.indicator{width:12px;height:12px;border-radius:50%;background:rgba(255,255,255,0.4);cursor:pointer;transition:all 0.3s}.indicator.active{background:white;transform:scale(1.3)}
.scroll-hint{position:absolute;bottom:40px;left:50%;transform:translateX(-50%);text-align:center;color:white;z-index:1;animation:bounce 2s infinite}.mouse{width:26px;height:40px;border:2px solid rgba(255,255,255,0.6);border-radius:20px;margin:0 auto 8px}.wheel{width:4px;height:8px;background:rgba(255,255,255,0.8);border-radius:2px;margin:8px auto 0;animation:scroll 1.5s infinite}@keyframes scroll{0%{opacity:1;transform:translateY(0)}100%{opacity:0;transform:translateY(12px)}}@keyframes bounce{0%,20%,50%,80%,100%{transform:translateX(-50%) translateY(0)}40%{transform:translateX(-50%) translateY(-10px)}60%{transform:translateX(-50%) translateY(-5px)}}.scroll-hint p{font-size:12px;color:rgba(255,255,255,0.8);margin:0}
.stats-section{padding:80px 0;background:linear-gradient(180deg,#f8f9fa,#fff)}.section-title{font-size:36px;font-weight:700;text-align:center;margin-bottom:48px;color:#333;position:relative}.section-title::after{content:'';position:absolute;bottom:-12px;left:50%;transform:translateX(-50%);width:60px;height:4px;background:linear-gradient(90deg,#3a6ea5,#7297bd);border-radius:2px}.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px}.stat-card{background:white;padding:32px;border-radius:16px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.08);transition:all 0.3s;border:1px solid #e9ecef}.stat-card:hover{transform:translateY(-8px);box-shadow:0 12px 40px rgba(58,110,165,0.15);border-color:#3a6ea5}.stat-icon{width:64px;height:64px;margin:0 auto 20px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:28px;color:white}.gradient-blue{background:linear-gradient(135deg,#3a6ea5,#7297bd)}.gradient-green{background:linear-gradient(135deg,#52c41a,#95de64)}.gradient-orange{background:linear-gradient(135deg,#ff7b29,#ffa940)}.gradient-purple{background:linear-gradient(135deg,#722ed1,#b37feb)}.stat-value{font-size:36px;font-weight:800;color:#3a6ea5;margin-bottom:8px}.stat-label{font-size:14px;color:#666;text-transform:uppercase;letter-spacing:1px}
.features-section{padding:80px 0;background:white}.features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:32px}.feature-card{background:white;border-radius:20px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);transition:all 0.4s;border:1px solid #e9ecef}.feature-card:hover{transform:translateY(-12px);box-shadow:0 20px 60px rgba(58,110,165,0.2)}.card-image{height:200px;background-size:cover;background-position:center;position:relative;transition:transform 0.4s}.feature-card:hover .card-image{transform:scale(1.05)}.image-overlay{position:absolute;inset:0;background:linear-gradient(180deg,transparent,rgba(58,110,165,0.3))}.card-body{padding:32px}.card-icon{width:56px;height:56px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:24px;color:white;margin-bottom:20px}.icon-blue{background:linear-gradient(135deg,#3a6ea5,#7297bd)}.icon-green{background:linear-gradient(135deg,#52c41a,#95de64)}.icon-purple{background:linear-gradient(135deg,#722ed1,#b37feb)}.card-body h3{font-size:22px;font-weight:700;color:#333;margin-bottom:12px}.card-body p{font-size:14px;color:#666;line-height:1.8;margin-bottom:20px}.card-link{display:inline-flex;align-items:center;gap:8px;color:#3a6ea5;font-weight:600;text-decoration:none;padding:10px 20px;background:rgba(58,110,165,0.1);border-radius:8px;transition:all 0.3s}.card-link:hover{background:#3a6ea5;color:white;transform:translateX(4px)}
@media(max-width:768px){.hero-title{font-size:36px}.hero-subtitle{font-size:18px}.search-row{flex-direction:column}.db-select{width:100%}.search-btn{width:100%}.stats-grid,.features-grid{grid-template-columns:1fr}}
</style>
