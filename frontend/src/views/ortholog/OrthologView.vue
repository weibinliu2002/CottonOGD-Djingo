<script setup lang="ts">
/**
 * 同源分析 / Orthogroup 统一查询页（2026-11 升级）。
 *
 * 单页承载三类入口（不新增菜单页面）：
 *  - Tab「浏览 Orthogroup」：左侧基因组树（可搜索/多选/全选/清空）+
 *    服务端筛选（OG 编号精确/模糊、基因数、物种数、所选物种覆盖数、单拷贝、排序）+ 分页；
 *    点击 OG 行在当前页抽屉中打开详情（复用 OrthogroupAnalysis），并保留完整详情页链接。
 *    列表下方折叠统计区域（OrthofinderStatistics）。
 *  - Tab「按基因查」：保留原基因→OG 跨物种检索（Meilisearch Orthologs 索引）。
 *  - 原 OG 详情路由 /tools/orthogroup/:og_code 保留，深链直达。
 *
 * 数据源与语义严格遵循 v1 契约（docs/COMPARATIVE_ANALYSIS_API_HANDOFF.md，2026-11-21 重写）：
 *  - mode=all 为交集、any 为并集，默认 all（与旧行为一致）；
 *  - “共享 OG”不是 Ortholog，直系同源只在详情页的 genes/orthologs 结果中展示。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search, Link } from '@element-plus/icons-vue'
import OrthogroupAnalysis from '@/components/data-display/OrthogroupAnalysis.vue'
import OrthofinderStatistics from '@/components/data-display/OrthofinderStatistics.vue'
import {
  getOrthogroupsBySpecies,
  getOrthologMeta,
  searchGenes,
  ORTHOLOG_INDEX,
  type OrthologOrthogroup,
  type OrthologSpeciesMeta,
} from '@/api/index'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const activeTab = ref<'browse' | 'gene'>('browse')

// ============ 物种元数据（左侧复选框 + 默认列表用） ============
const metaList = ref<OrthologSpeciesMeta[]>([])
const allSpeciesNames = computed(() => metaList.value.map((m) => m.name))
const totalSpecies = computed(() => allSpeciesNames.value.length)

interface SpeciesTreeNode {
  id: string
  label: string
  children?: SpeciesTreeNode[]
}

const treeRef = ref<any>(null)
const selectedSpecies = ref<string[]>([])
const genomeKeyword = ref('')

/** 按 Genome_type 将基因组聚合成「分组 → 单个基因组」的树结构 */
const speciesTree = computed<SpeciesTreeNode[]>(() => {
  const byType = new Map<string, OrthologSpeciesMeta[]>()
  for (const m of metaList.value) {
    const key = m.Genome_type || ''
    if (!byType.has(key)) byType.set(key, [])
    byType.get(key)!.push(m)
  }
  const typeKeys = [...byType.keys()].sort((a, b) => {
    const ua = a.toUpperCase()
    const ub = b.toUpperCase()
    if (ua && !ub) return -1
    if (!ua && ub) return 1
    return ua.localeCompare(ub)
  })
  const nodes: SpeciesTreeNode[] = []
  for (const k of typeKeys) {
    const metas = byType.get(k)!
    metas.sort((a, b) => a.name.localeCompare(b.name))
    const label = k ? `${k} (${metas.length})` : t('uncategorized')
    const children: SpeciesTreeNode[] = metas.map((m) => ({
      id: m.name,
      label: m.alias || m.Cotton_Species || m.name,
    }))
    nodes.push({ id: k ? `__group__${k}` : '__group__uncategorized', label, children })
  }
  return nodes
})

/** el-tree 关键字过滤：匹配基因组展示名或内部名 */
function filterGenomeNode(value: string, data: SpeciesTreeNode): boolean {
  if (!value) return true
  const kw = value.trim().toLowerCase()
  if (!kw) return true
  return (data.label || '').toLowerCase().includes(kw) || (data.id || '').toLowerCase().includes(kw)
}

watch(genomeKeyword, (val) => {
  treeRef.value?.filter(val)
})

const isAllSelected = computed(
  () => selectedSpecies.value.length === allSpeciesNames.value.length && allSpeciesNames.value.length > 0,
)
function toggleSelectAll(): void {
  const tree = treeRef.value
  if (isAllSelected.value) {
    tree?.setCheckedKeys([])
    selectedSpecies.value = []
  } else {
    tree?.setCheckedKeys(allSpeciesNames.value)
    selectedSpecies.value = [...allSpeciesNames.value]
  }
}

/** 树勾选变化：仅取叶子（单个基因组）key，勾选父分组自动级联 */
function onTreeCheck(): void {
  const tree = treeRef.value
  if (!tree) return
  selectedSpecies.value = (tree.getCheckedKeys(true) as string[]) ?? []
}

// ============ 浏览 Tab：服务端筛选 + 服务端分页 ============
const ogIdInput = ref('')
const ogIdMode = ref<'like' | 'exact'>('like')
const minGenes = ref<number | null>(null)
const maxGenes = ref<number | null>(null)
const minSpecies = ref<number | null>(null)
const maxSpecies = ref<number | null>(null)
const minCoverage = ref<number | null>(null)
const maxCoverage = ref<number | null>(null)
const singleCopyOnly = ref(false)
const speciesMode = ref<'all' | 'any'>('all')
const sortBy = ref<'selected_species' | 'gene_count' | 'species_count' | 'og_code'>('selected_species')
const ogPage = ref(1)
const ogPageSize = ref(50)
const ogList = ref<OrthologOrthogroup[]>([])
const ogTotal = ref(0)
const ogLoading = ref(false)
const ogError = ref('')

/** 单拷贝的严格定义（交接文档 B.1）：覆盖全部物种且每物种恰好 1 个基因 */
const totalForSingleCopy = computed(() => totalSpecies.value || undefined)

/** 当前请求的筛选参数（与交接文档 C.3 一一对应） */
function buildQuery() {
  const species = selectedSpecies.value
  const single = singleCopyOnly.value ? totalForSingleCopy.value : undefined
  return {
    species,
    mode: species.length ? speciesMode.value : ('any' as const),
    og_code: ogIdMode.value === 'exact' ? (ogIdInput.value.trim() || undefined) : undefined,
    og_code_like: ogIdMode.value === 'like' ? (ogIdInput.value.trim() || undefined) : undefined,
    min_genes: singleCopyOnly.value ? single : (minGenes.value ?? undefined),
    max_genes: singleCopyOnly.value ? single : (maxGenes.value ?? undefined),
    min_species: singleCopyOnly.value ? single : (minSpecies.value ?? undefined),
    max_species: singleCopyOnly.value ? single : (maxSpecies.value ?? undefined),
    // 所选物种覆盖数只在已选物种时有意义
    min_selected_species: species.length ? (minCoverage.value ?? undefined) : undefined,
    max_selected_species: species.length ? (maxCoverage.value ?? undefined) : undefined,
    // 未选物种时后端默认按 og_code 浏览；显式传入所选排序
    sort: species.length ? sortBy.value : (sortBy.value === 'selected_species' ? undefined : sortBy.value),
    limit: ogPageSize.value,
    offset: (ogPage.value - 1) * ogPageSize.value,
  }
}

/** 重新请求后端；resetPage=true 时回到第 1 页（筛选条件变化时使用） */
async function reloadBrowsing(resetPage = false): Promise<void> {
  if (resetPage) ogPage.value = 1
  ogLoading.value = true
  ogError.value = ''
  try {
    const res = await getOrthogroupsBySpecies(buildQuery())
    ogTotal.value = res.total ?? 0
    ogList.value = res.orthogroups ?? []
    if (!res.found && ogList.value.length === 0) {
      ogError.value = ''
    }
  } catch {
    ogError.value = t('request_failed')
    ogTotal.value = 0
    ogList.value = []
  } finally {
    ogLoading.value = false
  }
}

/** 提交筛选按钮：应用所有输入框条件 */
function submitFilters(): void {
  void reloadBrowsing(true)
}

function resetFilters(): void {
  ogIdInput.value = ''
  ogIdMode.value = 'like'
  minGenes.value = null
  maxGenes.value = null
  minSpecies.value = null
  maxSpecies.value = null
  minCoverage.value = null
  maxCoverage.value = null
  singleCopyOnly.value = false
  speciesMode.value = 'all'
  sortBy.value = selectedSpecies.value.length ? 'selected_species' : 'og_code'
  void reloadBrowsing(true)
}

/** 基因组选择/交集模式变化：沿用旧行为立即重新查询 */
watch(selectedSpecies, () => {
  sortBy.value = selectedSpecies.value.length ? 'selected_species' : 'og_code'
  void reloadBrowsing(true)
}, { deep: true })
watch(speciesMode, () => {
  if (selectedSpecies.value.length) void reloadBrowsing(true)
})

/** 表格排序：后端只提供字段排序，无方向参数（交接文档 C.3） */
function handleSortChange(payload: { prop: string | null; order: 'ascending' | 'descending' | null }): void {
  const prop = payload?.prop
  if (prop === 'gene_count' || prop === 'species_count' || prop === 'og_code' || prop === 'selected_species_count') {
    sortBy.value = prop === 'selected_species_count' ? 'selected_species' : prop
    void reloadBrowsing(true)
  }
}

function onPageSizeChange(): void {
  void reloadBrowsing(true)
}

/** OG 覆盖情况：该 OG 覆盖的物种数 / 当前索引物种总数 */
function coveragePercent(row: OrthologOrthogroup): number {
  if (!totalSpecies.value) return 0
  return Math.min(100, Math.round((row.species_count / totalSpecies.value) * 100))
}

// ============ OG 抽屉（当前页内查看详情） ============
const drawerVisible = ref(false)
const drawerOgCode = ref('')

function openOgDrawer(ogCode: string): void {
  if (!ogCode) return
  drawerOgCode.value = ogCode
  drawerVisible.value = true
}

/** 在完整详情页打开（保留原路由与页面） */
function openOgDetailPage(ogCode: string): void {
  const query =
    selectedSpecies.value.length === allSpeciesNames.value.length
      ? undefined
      : { species: selectedSpecies.value.join(',') }
  router.push({ name: 'OrthogroupDetail', params: { og_code: ogCode }, query })
}

// ============ 统计区域（折叠，按需加载） ============
const statsCollapse = ref<string[]>([])

// ============ Tab「按基因查」（Meilisearch Orthologs 索引） ============
const geneInput = ref('')
const geneLoading = ref(false)
const geneError = ref('')
interface GeneOgEntry {
  og_code: string
  species: string
  geneid: string
  genemaster_geneid: string
}
const geneOgs = ref<GeneOgEntry[]>([])
const selectedOg = ref<string>('')
const memberGenes = ref<GeneOgEntry[]>([])
const memberTotal = ref(0)
const memberOffset = ref(0)
const memberLimit = ref(20)
const memberSafeLimit = computed(() => Math.max(1, Math.min(memberLimit.value, 1000 - memberOffset.value)))
const memberLoading = ref(false)
const memberGeneFilter = ref('')

const memberHasMore = computed(() => memberGenes.value.length < memberTotal.value)

async function searchByGene(): Promise<void> {
  const geneid = geneInput.value.trim()
  if (!geneid) {
    geneError.value = t('ortholog_gene_placeholder')
    return
  }
  geneLoading.value = true
  geneError.value = ''
  geneOgs.value = []
  selectedOg.value = ''
  memberGenes.value = []
  memberTotal.value = 0
  try {
    const res = await searchGenes({
      q: geneid,
      index: ORTHOLOG_INDEX,
      limit: 50,
      offset: 0,
      withFacets: false,
      attributesToRetrieve: ['geneid', 'genemaster_geneid', 'species', 'og_code'],
      attributesToHighlight: ['geneid', 'genemaster_geneid', 'og_code'],
    })
    const hits = (res.data?.hits ?? []) as unknown as Array<Record<string, any>>
    if (res.code !== 0 || hits.length === 0) {
      geneError.value = t('ortholog_not_found')
      return
    }
    geneOgs.value = hits.map((h) => ({
      og_code: h.og_code as string,
      species: h.species as string,
      geneid: h.geneid as string,
      genemaster_geneid: (h.genemaster_geneid as string) || (h.geneid as string),
    }))
  } catch {
    geneError.value = t('ortholog_not_found')
  } finally {
    geneLoading.value = false
  }
}

const geneOgCodes = computed(() => {
  const seen = new Set<string>()
  const out: string[] = []
  geneOgs.value.forEach((o) => {
    if (o.og_code && !seen.has(o.og_code)) {
      seen.add(o.og_code)
      out.push(o.og_code)
    }
  })
  return out
})

async function loadMembers(ogCode: string, reset = true): Promise<void> {
  if (!ogCode) return
  memberLoading.value = true
  if (reset) {
    memberOffset.value = 0
    memberGenes.value = []
  }
  try {
    const res = await searchGenes({
      q: '',
      index: ORTHOLOG_INDEX,
      limit: memberSafeLimit.value,
      offset: memberOffset.value,
      withFacets: false,
      filter: `og_code = "${ogCode}"`,
      attributesToRetrieve: ['geneid', 'genemaster_geneid', 'species', 'og_code'],
      attributesToHighlight: ['geneid', 'genemaster_geneid', 'og_code'],
    })
    const hits = (res.data?.hits ?? []) as unknown as Array<Record<string, any>>
    const items: GeneOgEntry[] = hits.map((h) => ({
      og_code: h.og_code as string,
      species: h.species as string,
      geneid: h.geneid as string,
      genemaster_geneid: (h.genemaster_geneid as string) || (h.geneid as string),
    }))
    memberTotal.value = res.data?.estimatedTotalHits ?? items.length
    memberGenes.value = reset ? items : [...memberGenes.value, ...items]
  } catch {
    memberGenes.value = []
    memberTotal.value = 0
  } finally {
    memberLoading.value = false
  }
}

function selectOg(ogCode: string): void {
  selectedOg.value = ogCode
  memberGeneFilter.value = ''
  void loadMembers(ogCode, true)
}

function loadMoreMembers(): void {
  if (!memberHasMore.value || memberLoading.value) return
  memberOffset.value += memberLimit.value
  void loadMembers(selectedOg.value, false)
}

const filteredMemberGenes = computed<GeneOgEntry[]>(() => {
  const kw = memberGeneFilter.value.trim().toLowerCase()
  if (!kw) return memberGenes.value
  return memberGenes.value.filter(
    (g) =>
      g.geneid.toLowerCase().includes(kw) ||
      g.genemaster_geneid.toLowerCase().includes(kw) ||
      g.species.toLowerCase().includes(kw),
  )
})

function openGene(genemasterGeneid: string | null): void {
  if (!genemasterGeneid) return
  router.push({ name: 'GenomeDetail', params: { key: genemasterGeneid } })
}

onMounted(async () => {
  const meta = await getOrthologMeta()
  metaList.value = meta
  await reloadBrowsing()
  // 主页 Orthologs 检索深链：?og=OGxxxx 直接跳到 OG 详情页（保留原行为）
  const og = route.query.og as string | undefined
  if (og) {
    openOgDetailPage(og)
  }
})
</script>

<template>
  <div class="container ortholog-page">
    <h2 class="ortholog-page__title">{{ t('orthogroup') }}</h2>

    <el-tabs v-model="activeTab" class="ortholog-tabs">
      <!-- Tab 1：浏览 Orthogroup -->
      <el-tab-pane :label="t('homology_browse')" name="browse">
        <el-row :gutter="16" class="ortholog-layout">
          <!-- 左侧：基因组树 -->
          <el-col :span="6" class="genome-col">
            <el-card class="genome-panel" shadow="never">
              <template #header>
                <div class="genome-panel__head">
                  <span>{{ t('ortholog_species') }}</span>
                  <el-button link type="primary" size="small" @click="toggleSelectAll">
                    {{ isAllSelected ? t('clear_all') : t('select_all') }}
                  </el-button>
                </div>
              </template>
              <el-input
                v-model="genomeKeyword"
                class="genome-panel__search"
                :placeholder="t('og_genome_search_placeholder')"
                clearable
                size="small"
              />
              <el-tree
                ref="treeRef"
                class="genome-panel__tree"
                :data="speciesTree"
                :props="{ children: 'children', label: 'label' }"
                node-key="id"
                show-checkbox
                check-on-click-node
                :default-expand-all="false"
                :expand-on-click-node="false"
                :filter-node-method="filterGenomeNode"
                @check="onTreeCheck"
              />
              <div class="genome-panel__count">
                {{ t('selected_genomes') }} {{ selectedSpecies.length }} / {{ totalSpecies }}
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：筛选 + 列表 -->
          <el-col :span="18">
            <el-card class="ortholog-card" shadow="never">
              <!-- 筛选条 1：OG 编号 / 交集模式 / 单拷贝 / 操作 -->
              <div class="browse-filters">
                <el-input
                  v-model="ogIdInput"
                  class="browse-filters__id"
                  :placeholder="t('og_id_filter_placeholder')"
                  clearable
                  size="default"
                  @keyup.enter="submitFilters"
                />
                <el-radio-group v-model="ogIdMode" size="small">
                  <el-radio-button value="like">{{ t('og_match_like') }}</el-radio-button>
                  <el-radio-button value="exact">{{ t('og_match_exact') }}</el-radio-button>
                </el-radio-group>
                <el-checkbox v-model="singleCopyOnly" size="default">
                  {{ t('homology_single_copy_only') }}
                </el-checkbox>
                <el-radio-group v-if="selectedSpecies.length" v-model="speciesMode" size="default">
                  <el-radio value="all">{{ t('shared_ogs') }}</el-radio>
                  <el-radio value="any">Any</el-radio>
                </el-radio-group>
                <el-button type="primary" size="default" :loading="ogLoading" @click="submitFilters">
                  <el-icon><Search /></el-icon>
                  {{ t('sty_query') }}
                </el-button>
                <el-button size="default" @click="resetFilters">{{ t('og_reset_filters') }}</el-button>
              </div>

              <!-- 筛选条 2：数值范围 / 排序 / 每页 -->
              <div class="browse-filters browse-filters--ranges">
                <div class="range-group">
                  <span class="range-label">{{ t('gene_count') }}</span>
                  <el-input-number v-model="minGenes" :min="0" :controls="false" size="small" class="range-input" :placeholder="t('og_min')" />
                  <span class="range-sep">–</span>
                  <el-input-number v-model="maxGenes" :min="0" :controls="false" size="small" class="range-input" :placeholder="t('og_max')" />
                </div>
                <div class="range-group">
                  <span class="range-label">{{ t('species_count') }}</span>
                  <el-input-number v-model="minSpecies" :min="0" :controls="false" size="small" class="range-input" :placeholder="t('og_min')" />
                  <span class="range-sep">–</span>
                  <el-input-number v-model="maxSpecies" :min="0" :controls="false" size="small" class="range-input" :placeholder="t('og_max')" />
                </div>
                <div class="range-group" v-if="selectedSpecies.length">
                  <span class="range-label">{{ t('og_selected_species_count') }}</span>
                  <el-input-number v-model="minCoverage" :min="0" :controls="false" size="small" class="range-input" :placeholder="t('og_min')" />
                  <span class="range-sep">–</span>
                  <el-input-number v-model="maxCoverage" :min="0" :controls="false" size="small" class="range-input" :placeholder="t('og_max')" />
                </div>
                <div class="range-group">
                  <span class="range-label">{{ t('og_sort') }}</span>
                  <el-select v-model="sortBy" size="small" class="range-select" @change="submitFilters">
                    <el-option :label="t('og_sort_selected')" value="selected_species" />
                    <el-option :label="t('gene_count')" value="gene_count" />
                    <el-option :label="t('species_count')" value="species_count" />
                    <el-option :label="t('og_code')" value="og_code" />
                  </el-select>
                </div>
                <div class="range-group range-group--right">
                  <span class="range-label">{{ t('og_page') }}</span>
                  <el-select v-model="ogPageSize" size="small" class="range-select" @change="onPageSizeChange">
                    <el-option v-for="s in [20, 50, 100, 200, 500]" :key="s" :label="String(s)" :value="s" />
                  </el-select>
                </div>
              </div>

              <el-alert v-if="ogError" type="warning" :title="ogError" show-icon class="mb-4" />

              <div class="ortholog-oglist__total">
                {{ t('total') }} {{ ogTotal }} {{ t('records') }}
              </div>

              <el-table
                v-loading="ogLoading"
                :data="ogList"
                stripe
                border
                size="small"
                :row-class-name="() => 'is-clickable'"
                @sort-change="handleSortChange"
                @row-click="(row: OrthologOrthogroup) => openOgDrawer(row.og_code)"
              >
                <el-table-column :label="t('og_code')" prop="og_code" min-width="170" sortable="custom">
                  <template #default="scope">
                    <a class="og-link" @click.stop="openOgDrawer(scope.row.og_code)">{{ scope.row.og_code }}</a>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('species_count')"
                  prop="species_count"
                  width="130"
                  align="center"
                  sortable="custom"
                />
                <el-table-column
                  v-if="selectedSpecies.length"
                  :label="t('og_selected_species_count')"
                  prop="selected_species_count"
                  width="150"
                  align="center"
                  sortable="custom"
                >
                  <template #default="scope">{{ scope.row.selected_species_count ?? '-' }}</template>
                </el-table-column>
                <el-table-column
                  :label="t('gene_count')"
                  prop="gene_count"
                  width="120"
                  align="center"
                  sortable="custom"
                />
                <el-table-column :label="t('og_coverage')" min-width="180">
                  <template #default="scope">
                    <div class="coverage-cell">
                      <el-progress
                        :percentage="coveragePercent(scope.row)"
                        :stroke-width="8"
                        :show-text="false"
                        class="coverage-cell__bar"
                      />
                      <span class="coverage-cell__text">{{ coveragePercent(scope.row) }}%</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column :label="t('homology_single_copy')" width="110" align="center">
                  <template #default="scope">
                    <el-tag v-if="scope.row.is_single_copy" size="small" type="success">
                      {{ t('yes') }}
                    </el-tag>
                    <span v-else>{{ t('no') }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('homology_annotation')" min-width="150">
                  <template #default="scope">{{ scope.row.annotation || '-' }}</template>
                </el-table-column>
                <el-table-column :label="t('og_actions')" width="150" align="center">
                  <template #default="scope">
                    <el-button link type="primary" size="small" @click.stop="openOgDrawer(scope.row.og_code)">
                      {{ t('og_open_panel') }}
                    </el-button>
                    <el-button link type="primary" size="small" @click.stop="openOgDetailPage(scope.row.og_code)">
                      {{ t('og_open_page') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <div class="ortholog-oglist__more">
                <el-pagination
                  v-model:current-page="ogPage"
                  v-model:page-size="ogPageSize"
                  :total="ogTotal"
                  :page-sizes="[20, 50, 100, 200, 500]"
                  layout="total, sizes, prev, pager, next, jumper"
                  background
                  :disabled="ogLoading"
                  @current-change="() => reloadBrowsing()"
                  @size-change="onPageSizeChange"
                />
              </div>

              <!-- 统计区域（折叠，展开后才请求） -->
              <el-collapse v-model="statsCollapse" class="stats-collapse">
                <el-collapse-item :title="t('stats_title')" name="stats">
                  <OrthofinderStatistics
                    v-if="statsCollapse.includes('stats')"
                    :species-list="allSpeciesNames"
                  />
                </el-collapse-item>
              </el-collapse>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 2：按基因查直系同源（Meilisearch Orthologs 索引） -->
      <el-tab-pane :label="t('ortholog_search')" name="gene">
        <el-card class="ortholog-card" shadow="never">
          <el-form inline @submit.prevent="searchByGene">
            <el-form-item class="ortholog-card__input">
              <el-input
                v-model="geneInput"
                :placeholder="t('ortholog_gene_placeholder')"
                clearable
                @keyup.enter="searchByGene"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="geneLoading" @click="searchByGene">
                <el-icon><Search /></el-icon>
                {{ t('search') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert v-if="geneError" type="warning" :title="geneError" show-icon class="mb-4" />

          <template v-if="geneOgs.length">
            <h4 class="ortholog-subhead">{{ t('ortholog_matched_ogs') }}</h4>
            <div class="ortholog-og-chips">
              <el-tag
                v-for="code in geneOgCodes"
                :key="code"
                class="ortholog-og-chip"
                size="large"
                :type="selectedOg === code ? 'primary' : 'info'"
                effect="plain"
                @click="selectOg(code)"
              >
                {{ code }}
              </el-tag>
            </div>

            <div class="mb-4 mt-4">
              <div class="browse-filters">
                <el-input
                  v-model="memberGeneFilter"
                  class="browse-filters__ann"
                  :placeholder="t('detail_gene_filter_placeholder')"
                  clearable
                  size="default"
                />
                <span class="ortholog-og__meta">
                  {{ t('ortholog_member_genes') }} · {{ t('og_code') }}: {{ selectedOg || t('ortholog_no_og_selected') }}
                </span>
              </div>

              <el-table
                v-loading="memberLoading"
                :data="filteredMemberGenes"
                stripe
                border
                size="small"
                class="mt-4"
              >
                <el-table-column :label="t('ortholog_species')" prop="species" min-width="220" />
                <el-table-column :label="t('ortholog_genes')" min-width="240">
                  <template #default="scope">
                    <a
                      v-if="scope.row.genemaster_geneid"
                      class="ortholog-gene__link"
                      @click="openGene(scope.row.genemaster_geneid)"
                    >{{ scope.row.genemaster_geneid }}</a>
                    <span v-else class="ortholog-gene__plain">{{ scope.row.geneid }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('og_code')" prop="og_code" min-width="180" />
              </el-table>

              <div class="ortholog-oglist__total">
                {{ t('total') }} {{ memberTotal }} {{ t('records') }}
              </div>
              <div class="ortholog-oglist__more">
                <el-button v-if="memberHasMore" :loading="memberLoading" @click="loadMoreMembers">
                  {{ t('load_more') }}
                </el-button>
                <span v-else class="ortholog-oglist__end">{{ t('no_more') }}</span>
              </div>
            </div>
          </template>

          <el-alert
            v-else-if="!geneLoading && !geneError"
            type="info"
            :closable="false"
            class="mb-4"
            :title="t('ortholog_select_og_hint')"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- OG 详情抽屉（当前页内查看；完整分析复用 OrthogroupAnalysis） -->
    <el-drawer
      v-model="drawerVisible"
      :title="drawerOgCode || t('og_code')"
      size="78%"
      destroy-on-close
    >
      <template #header>
        <div class="drawer-head">
          <span class="drawer-head__title">{{ drawerOgCode }}</span>
          <el-button
            v-if="drawerOgCode"
            link
            type="primary"
            size="small"
            :icon="Link"
            @click="openOgDetailPage(drawerOgCode)"
          >{{ t('og_open_page') }}</el-button>
        </div>
      </template>
      <OrthogroupAnalysis
        v-if="drawerOgCode"
        :og-code="drawerOgCode"
        :species-filter="selectedSpecies"
        compact
      />
    </el-drawer>
  </div>
</template>

<style scoped>
.ortholog-page {
  max-width: 1280px;
  margin: 0 auto;
  padding-bottom: 2rem;
}

.ortholog-page__title {
  margin-bottom: 1.25rem;
}

.ortholog-tabs {
  --el-color-primary: #3a6ea5;
}

.ortholog-layout {
  align-items: flex-start;
}

.genome-panel {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  position: sticky;
  top: 16px;
}

.genome-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.genome-panel__search {
  margin-bottom: 0.5rem;
}

.genome-panel__tree {
  max-height: 60vh;
  overflow-y: auto;
  border: 1px solid #eef1f4;
  border-radius: 8px;
  padding: 8px;
  --el-color-primary: #3a6ea5;
}

.genome-panel__tree :deep(.el-tree-node__content) {
  height: 28px;
}

.genome-panel__count {
  margin-top: 0.75rem;
  color: #6c757d;
  font-size: 0.85rem;
}

.ortholog-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
}

.browse-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.browse-filters--ranges {
  padding-top: 0.25rem;
}

.browse-filters__id {
  width: 240px;
}

.browse-filters__ann {
  width: 260px;
}

.range-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.range-group--right {
  margin-left: auto;
}

.range-label {
  color: #606266;
  font-size: 0.85rem;
}

.range-input {
  width: 76px;
}

.range-sep {
  color: #adb5bd;
}

.range-select {
  width: 150px;
}

.coverage-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.coverage-cell__bar {
  flex: 1;
}

.coverage-cell__text {
  color: #6c757d;
  font-size: 0.78rem;
  width: 38px;
  text-align: right;
}

.ortholog-oglist__total {
  margin-bottom: 0.75rem;
  color: #6c757d;
  font-weight: 500;
}

.ortholog-oglist__more {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.ortholog-oglist__end {
  color: #adb5bd;
  font-size: 0.85rem;
}

.og-link {
  color: #3a6ea5;
  cursor: pointer;
  text-decoration: none;
}

.og-link:hover {
  text-decoration: underline;
}

.stats-collapse {
  margin-top: 1.25rem;
  border-top: 1px solid #eef1f4;
}

.stats-collapse :deep(.el-collapse-item__header) {
  font-weight: 600;
  color: #2c3e50;
}

.ortholog-gene__link {
  color: #3a6ea5;
  cursor: pointer;
  text-decoration: none;
}

.ortholog-gene__link:hover {
  text-decoration: underline;
}

.ortholog-gene__plain {
  color: #495057;
}

.ortholog-card__input {
  width: 360px;
}

.ortholog-subhead {
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 0.75rem;
}

.ortholog-og-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.ortholog-og-chip {
  cursor: pointer;
}

.ortholog-og__meta {
  color: #6c757d;
  font-size: 0.85rem;
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.drawer-head__title {
  font-weight: 600;
  color: #3a6ea5;
}

.mt-4 {
  margin-top: 1.5rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

:deep(.is-clickable) {
  cursor: pointer;
}
</style>
