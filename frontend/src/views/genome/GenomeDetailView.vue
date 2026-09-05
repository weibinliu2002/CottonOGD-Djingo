<template>
  <div class="container mt-4 mb-5">
    <!-- 返回 + 面包屑 -->
    <div class="mb-4">
      <el-button type="default" :icon="ArrowLeft" @click="goBack">
        Back to Genome List
      </el-button>
      <el-breadcrumb separator="/" class="mt-2">
        <el-breadcrumb-item :to="{ path: '/genome/browse' }">Genome Browser</el-breadcrumb-item>
        <el-breadcrumb-item>{{ current ? current.alias || current.name || detailKey : 'Detail' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 加载中 -->
    <el-skeleton v-if="loading" :rows="14" animated :throttle="100" />

    <!-- 未找到 -->
    <el-alert
      v-else-if="!current"
      type="error"
      :title="`Genome '${detailKey}' not found`"
      show-icon
      class="mb-4"
    >
      <template #default>
        <el-button type="primary" size="small" class="mt-2" @click="goBack">
          Return to list
        </el-button>
      </template>
    </el-alert>

    <!-- 详情区 -->
    <template v-else>
      <!-- 头部信息卡 -->
      <el-card shadow="hover" class="header-card mb-4">
        <div class="header-row">
          <div class="header-main">
            <h1 class="genome-name">
              {{ current.alias || current.name }}
            </h1>
            <p v-if="current.name && current.name !== current.alias" class="genome-internal-name">
              ({{ current.name }})
            </p>
            <div class="header-tags mt-3">
              <el-tag type="success" size="large" effect="light" class="mr-2">
                {{ current.Genome_type || 'Unknown Type' }}
              </el-tag>
              <el-tag type="warning" size="large" effect="light" class="mr-2">
                {{ current.Ploidy || 'Unknown Ploidy' }}
              </el-tag>
              <el-tag type="info" size="large" effect="light" v-if="current.Category" class="mr-2">
                {{ current.Category }}
              </el-tag>
              <el-tag
                size="large"
                effect="light"
                :type="buscoTagType(current.Busco)"
                v-if="formatBusco(current.Busco) !== '-'"
              >
                BUSCO {{ formatBusco(current.Busco) }}
              </el-tag>
            </div>
          </div>

          <!-- 快速下载 / 外链 -->
          <div class="header-actions">
            <el-button
              type="primary"
              size="large"
              :icon="Download"
              :disabled="!cleanWebsite(current.Website)"
              @click="openDownload"
            >
              Download Genome
            </el-button>
            <el-button
              size="large"
              :icon="Link"
              :disabled="!cleanWebsite(current.Website)"
              @click="openDownload"
              class="ml-2"
            >
              Source Page
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 关键指标卡片 -->
      <el-row :gutter="16" class="metric-row mb-4">
        <el-col :xs="12" :sm="6">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-label">Genome Size</div>
            <div class="metric-value">{{ formatGenomeSize(current.Genome_size) }} Gb</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-label">BUSCO</div>
            <div class="metric-value">{{ formatBusco(current.Busco) }}</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-label">LAI Value</div>
            <div class="metric-value">{{ current.LAI_value || '-' }}</div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-label">Cotton Species</div>
            <div class="metric-value small">{{ current.Cotton_Species || '-' }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 详细描述表 + 快捷面板 -->
      <el-row :gutter="20">
        <el-col :xs="24" :lg="16">
          <el-card shadow="hover" class="mb-4">
            <template #header>
              <div class="card-header">
                <el-icon><InfoFilled /></el-icon>
                <span>Assembly Information</span>
              </div>
            </template>

            <el-descriptions :column="2" border size="default">
              <el-descriptions-item label="Species">
                {{ current.Cotton_Species || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="Genome Type">
                <el-tag type="success" size="small">{{ current.Genome_type || '-' }}</el-tag>
              </el-descriptions-item>

              <el-descriptions-item label="Category">
                {{ current.Category || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="Ploidy">
                <el-tag type="warning" size="small">{{ current.Ploidy || '-' }}</el-tag>
              </el-descriptions-item>

              <el-descriptions-item label="Accession / Cultivar" :span="2">
                {{ current.Accession || '-' }}
              </el-descriptions-item>

              <el-descriptions-item label="Assembling Institution" :span="2">
                {{ current.Assembling_institution || '-' }}
              </el-descriptions-item>

              <el-descriptions-item label="Article / Reference" :span="2">
                {{ current.Article || '-' }}
              </el-descriptions-item>

              <el-descriptions-item label="Download / Source Link" :span="2">
                <template v-if="cleanWebsite(current.Website)">
                  <el-link
                    :href="cleanWebsite(current.Website)"
                    type="primary"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ cleanWebsite(current.Website) }}
                    <el-icon class="link-icon"><Link /></el-icon>
                  </el-link>
                </template>
                <span v-else>-</span>
              </el-descriptions-item>

              <el-descriptions-item label="Description" :span="2" v-if="current.description">
                {{ current.description }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- Explore This Genome：快捷跳转到各模块，并自动预设当前基因组 -->
          <el-card shadow="hover" class="mb-4">
            <template #header>
              <div class="card-header">
                <el-icon><Compass /></el-icon>
                <span>Explore This Genome</span>
              </div>
            </template>

            <h4 class="explore-section-title">Sequence Analysis</h4>
            <div class="explore-grid">
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goIdSearch"
              >
                <el-icon class="exp-icon" color="#409EFF"><Search /></el-icon>
                <div class="exp-title">Search Genes by ID</div>
                <div class="exp-sub">ID / Keyword search in this genome</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goRegion"
              >
                <el-icon class="exp-icon" color="#67C23A"><LocationFilled /></el-icon>
                <div class="exp-title">Region Search</div>
                <div class="exp-sub">Retrieve sequences by coordinate</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goBlast"
              >
                <el-icon class="exp-icon" color="#E6A23C"><Share /></el-icon>
                <div class="exp-title">BLAST</div>
                <div class="exp-sub">SequenceServer (BLASTp, etc.)</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goJBrowse"
              >
                <el-icon class="exp-icon" color="#909399"><Grid /></el-icon>
                <div class="exp-title">JBrowse</div>
                <div class="exp-sub">Interactive genome browser</div>
              </el-card>
            </div>

            <h4 class="explore-section-title">Functional Annotations</h4>
            <div class="explore-grid">
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goGOAnnot"
              >
                <el-icon class="exp-icon" color="#722ed1"><Files /></el-icon>
                <div class="exp-title">GO Annotation</div>
                <div class="exp-sub">Gene Ontology terms</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goKEGGAnnot"
              >
                <el-icon class="exp-icon" color="#eb2f96"><Histogram /></el-icon>
                <div class="exp-title">KEGG Annotation</div>
                <div class="exp-sub">Pathway &amp; KO annotations</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goGOEnrich"
              >
                <el-icon class="exp-icon" color="#13c2c2"><CollectionTag /></el-icon>
                <div class="exp-title">GO Enrichment</div>
                <div class="exp-sub">Enrichment analysis (gseapy)</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goKEGGEnrich"
              >
                <el-icon class="exp-icon" color="#f5222d"><PieChart /></el-icon>
                <div class="exp-title">KEGG Enrichment</div>
                <div class="exp-sub">Pathway enrichment analysis</div>
              </el-card>
            </div>

            <h4 class="explore-section-title">Regulators &amp; Expression</h4>
            <div class="explore-grid">
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goTF"
              >
                <el-icon class="exp-icon" color="#2f54eb"><Connection /></el-icon>
                <div class="exp-title">Transcription Factors (TF)</div>
                <div class="exp-sub">TF families &amp; target genes</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goTR"
              >
                <el-icon class="exp-icon" color="#fa8c16"><Aim /></el-icon>
                <div class="exp-title">Transcription Regulators (TR)</div>
                <div class="exp-sub">TR families &amp; classifications</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goExpression"
              >
                <el-icon class="exp-icon" color="#52c41a"><DataLine /></el-icon>
                <div class="exp-title">Gene Expression</div>
                <div class="exp-sub">Tissue / multi-sample expression</div>
              </el-card>
              <el-card
                shadow="never"
                class="explore-card"
                @click="explore.goPrimer"
              >
                <el-icon class="exp-icon" color="#8c8c8c"><Promotion /></el-icon>
                <div class="exp-title">Primer Design</div>
                <div class="exp-sub">Design PCR primers</div>
              </el-card>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="8">
          <!-- 快速统计 -->
          <el-card shadow="hover" class="mb-4">
            <template #header>
              <div class="card-header">
                <el-icon><DataAnalysis /></el-icon>
                <span>Quality Summary</span>
              </div>
            </template>

            <div class="quality-list">
              <div class="quality-item">
                <span class="q-label">BUSCO Score</span>
                <el-progress
                  :percentage="safeProgress(parseBusco(current.Busco))"
                  :color="progressBuscoColor(current.Busco)"
                  :stroke-width="14"
                />
                <span class="q-value">{{ formatBusco(current.Busco) }}</span>
              </div>
              <div class="quality-item">
                <span class="q-label">Genome Size (Gb)</span>
                <el-progress
                  :percentage="sizeProgress(current.Genome_size)"
                  color="#409EFF"
                  :stroke-width="14"
                />
                <span class="q-value">{{ formatGenomeSize(current.Genome_size) }} Gb</span>
              </div>
              <div class="quality-item">
                <span class="q-label">LAI Score</span>
                <el-progress
                  :percentage="laiProgress(current.LAI_value)"
                  color="#67C23A"
                  :stroke-width="14"
                />
                <span class="q-value">{{ current.LAI_value || '-' }}</span>
              </div>
            </div>
          </el-card>

          <!-- 快捷操作 -->
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <el-icon><Operation /></el-icon>
                <span>Quick Actions</span>
              </div>
            </template>
            <div class="action-list">
              <el-button
                type="primary"
                size="large"
                class="w-100 mb-2"
                :icon="Download"
                :disabled="!cleanWebsite(current.Website)"
                @click="openDownload"
              >
                Download Genome
              </el-button>
              <el-button
                type="success"
                size="large"
                class="w-100 mb-2"
                :icon="View"
                @click="goJBrowse"
              >
                View in JBrowse
              </el-button>
              <el-button
                type="warning"
                size="large"
                class="w-100"
                :icon="Search"
                @click="goIdSearch"
              >
                Search Genes in this Genome
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Download,
  Link,
  InfoFilled,
  DataAnalysis,
  Operation,
  View,
  Search,
  Compass,
  LocationFilled,
  Share,
  Grid,
  Files,
  Histogram,
  CollectionTag,
  PieChart,
  Connection,
  Aim,
  DataLine,
  Promotion,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useGenomeStore } from '@/stores/modules/genome'
import type { Species } from '@/stores/modules/genome'

const route = useRoute()
const router = useRouter()
const genomeStore = useGenomeStore()

const loading = ref(true)

// 路径参数（name 或 id）
const detailKey = computed<string>(() => {
  const raw = (route.params.key as string) || ''
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
})

// 根据 key 在 speciesData 里定位
const current = computed<Species | null>(() => {
  const list = genomeStore.speciesData
  if (!list.length) return null
  const k = detailKey.value
  // 1. name 精确匹配
  let hit = list.find((s) => s.name === k)
  if (hit) return hit
  // 2. alias 精确匹配
  hit = list.find((s) => s.alias === k)
  if (hit) return hit
  // 3. id 匹配（纯数字参数）
  if (/^\d+$/.test(k)) {
    const id = Number(k)
    hit = list.find((s) => s.id === id)
    if (hit) return hit
  }
  return null
})

// ============ 格式化工具 ============
function formatGenomeSize(size: number | null | undefined): string {
  if (size === null || size === undefined || isNaN(size as number)) return '-'
  return (Number(size) / 1_000_000_000).toFixed(3)
}

function parseBusco(busco: string | undefined | null): number {
  if (!busco) return NaN
  const n = Number(String(busco).trim())
  if (isNaN(n)) return NaN
  return n <= 1 ? n * 100 : n
}
function formatBusco(busco: string | undefined | null): string {
  const n = parseBusco(busco)
  if (isNaN(n)) return '-'
  return `${n.toFixed(1)}%`
}
function buscoTagType(busco: string | undefined | null): '' | 'success' | 'warning' | 'danger' | 'info' {
  const n = parseBusco(busco)
  if (isNaN(n)) return 'info'
  if (n >= 95) return 'success'
  if (n >= 90) return ''
  if (n >= 80) return 'warning'
  return 'danger'
}
function safeProgress(n: number): number {
  if (isNaN(n)) return 0
  return Math.max(0, Math.min(100, Math.round(n)))
}
function progressBuscoColor(busco: string | undefined | null): string {
  const n = parseBusco(busco)
  if (isNaN(n)) return '#909399'
  if (n >= 95) return '#67C23A'
  if (n >= 90) return '#409EFF'
  if (n >= 80) return '#E6A23C'
  return '#F56C6C'
}
// 基因组大小进度（0-3Gb 归一化到 0-100，超 3Gb 按 100 显示）
function sizeProgress(size: number | null | undefined): number {
  if (size === null || size === undefined || isNaN(size as number)) return 0
  const gb = Number(size) / 1_000_000_000
  return Math.max(0, Math.min(100, Math.round((gb / 3) * 100)))
}
// LAI 进度（0-20 归一化到 0-100）
function laiProgress(lai: string | undefined | null): number {
  if (!lai) return 0
  const n = Number(String(lai).trim())
  if (isNaN(n)) return 0
  return Math.max(0, Math.min(100, Math.round((n / 20) * 100)))
}

// 清洗 Website 链接：数据中可能包含反引号和空格包裹，如 `https://xxx`
function cleanWebsite(raw: string | null | undefined): string {
  if (!raw) return ''
  let s = String(raw).trim()
  // 去掉首尾反引号/空格
  s = s.replace(/^[`\s"'“”‘’]+|[`\s"'“”‘’]+$/g, '')
  // 如果不是 http(s) 开头，补上
  if (s && !/^https?:\/\//i.test(s)) {
    s = 'https://' + s.replace(/^\/+/, '')
  }
  return s
}

// ============ 操作 ============
function goBack(): void {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push({ path: '/genome/browse' })
  }
}

function openDownload(): void {
  const url = cleanWebsite(current.value?.Website)
  if (!url) {
    ElMessage.warning('No download link available for this genome')
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

// 当前基因组用于传参：优先用 name（与 genomeOptions 的 GenomeItem.value 一致）
const genomeParam = computed<string>(() => {
  return current.value?.name ?? current.value?.alias ?? ''
})

// 所有带 genome query 的跳转：如果当前基因组不在可选列表里，则不携带
function pushWithGenome(path: string): void {
  const query: Record<string, string> = {}
  if (genomeParam.value) query.genome = genomeParam.value
  router.push({ path, query })
}

// Explore This Genome 快捷跳转面板
const explore = {
  // ====== Sequence Analysis ======
  goIdSearch: () => pushWithGenome('/sequence/search'),
  goRegion: () => pushWithGenome('/sequence/region'),
  goBlast: () => pushWithGenome('/sequence/server'),
  goJBrowse: () => pushWithGenome('/genome/jbrowse'),

  // ====== Functional Annotations ======
  goGOAnnot: () => pushWithGenome('/annotation/go'),
  goKEGGAnnot: () => pushWithGenome('/annotation/kegg'),
  goGOEnrich: () => pushWithGenome('/enrichment/go'),
  goKEGGEnrich: () => pushWithGenome('/enrichment/kegg'),

  // ====== Regulators & Expression ======
  goTF: () => pushWithGenome('/browse/tf'),
  goTR: () => pushWithGenome('/browse/tr'),
  goExpression: () => pushWithGenome('/expression/gene'),
  goPrimer: () => pushWithGenome('/tools/primer-design'),
}

// 兼容 Quick Actions 卡片原有按钮
const goJBrowse = explore.goJBrowse
const goIdSearch = explore.goIdSearch

// ============ 初始化 ============
async function ensureData(): Promise<void> {
  loading.value = true
  try {
    if (genomeStore.speciesData.length === 0) {
      await genomeStore.fetchGenomes()
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  ensureData()
})

// 路由参数变化时不用重新请求数据（store 已缓存），只等下一帧重新计算
watch(detailKey, () => {
  ensureData()
})
</script>

<style scoped>
.genome-name {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0;
  color: #303133;
}
.genome-internal-name {
  color: #909399;
  margin-top: 0.25rem;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
}
.header-main {
  flex: 1;
  min-width: 0;
}
.header-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0;
}
.mr-2 {
  margin-right: 0.5rem;
}
.ml-2 {
  margin-left: 0.5rem;
}
.mt-2 {
  margin-top: 0.5rem;
}
.mt-3 {
  margin-top: 1rem;
}
.mb-4 {
  margin-bottom: 1.5rem;
}
.mb-5 {
  margin-bottom: 3rem;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
}
.link-icon {
  margin-left: 4px;
  vertical-align: -2px;
}

.metric-card :deep(.el-card__body) {
  padding: 16px 20px;
}
.metric-label {
  color: #909399;
  font-size: 0.85rem;
  margin-bottom: 6px;
}
.metric-value {
  font-size: 1.4rem;
  font-weight: 700;
  color: #303133;
}
.metric-value.small {
  font-size: 1rem;
}

.quality-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.quality-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.quality-item .q-label {
  font-size: 0.85rem;
  color: #606266;
}
.quality-item .q-value {
  font-size: 0.85rem;
  color: #303133;
  font-weight: 600;
  align-self: flex-end;
}

.action-list :deep(.el-button) {
  width: 100%;
}
.w-100 {
  width: 100%;
}

/* ========== Explore This Genome ========== */
.explore-section-title {
  margin: 0 0 12px 4px;
  font-size: 0.95rem;
  color: #606266;
  font-weight: 600;
  border-left: 3px solid #409EFF;
  padding-left: 8px;
}
.explore-section-title + .explore-grid {
  margin-bottom: 20px;
}
.explore-section-title:not(:first-of-type) {
  margin-top: 12px;
}
.explore-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 1200px) {
  .explore-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  .explore-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 480px) {
  .explore-grid { grid-template-columns: 1fr; }
}
.explore-card {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.explore-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.12) !important;
  border-color: #b3d8ff;
}
.explore-card :deep(.el-card__body) {
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}
.exp-icon {
  font-size: 28px;
  margin-bottom: 4px;
}
.exp-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #303133;
}
.exp-sub {
  font-size: 0.8rem;
  color: #909399;
  line-height: 1.35;
}
</style>
