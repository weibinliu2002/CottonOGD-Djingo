<script setup lang="ts">
/**
 * 同源分析 / Orthogroup 统一查询页（阶段 5.1，合并 HomologyView + OrthologView）
 *
 * 对标 SoyOmics 的 Homology 模块，单页承载两类入口：
 *  - Tab「浏览 Orthogroup」：左侧基因组复选框 + 顶部 OG id / 注释筛选 + 单拷贝开关，
 *    默认展示若干 OG（后端 orthogroups_by_species：未选基因组时按 any + 全部基因组取默认列表）；
 *    点击 OG 行 → 抽屉展示该簇跨物种成员（行=物种，列=成员基因，可链接跳基因详情）。
 *  - Tab「按基因查」：保留原 OrthologView 的基因→OG 跨物种检索（不丢失已有功能）。
 *
 * 数据源：全部走真实后端 /CottonOGD_api/orthofinder/，无 mock。
 *
 * ⚠️ 后端约定说明：orthogroup 的列表与明细目前**不返回 annotation 字段**。
 * 因此「注释筛选」在列表层退化为对 og_code 的匹配（后端补齐 annotation 后自动切换为按注释匹配）；
 * 真正的「按成员基因/注释筛选」放在 OG 明细抽屉内（成员基因 id 在明细中可用）。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import {
  getOrthogroupDetailV2,
  getOrthogroupsBySpecies,
  getOrthologMeta,
  searchGenes,
  ORTHOLOG_INDEX,
  type OrthologOrthogroup,
  type OrthologSpeciesMember,
  type OrthologSpeciesMeta,
} from '@/api/index'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const activeTab = ref<'browse' | 'gene'>('browse')

// ============ 物种元数据（左侧复选框 + 默认列表用） ============
const metaList = ref<OrthologSpeciesMeta[]>([])
const allSpeciesNames = computed(() => metaList.value.map((m) => m.name))
/** 物种层级树：父节点 = Genome_type 分组（可批量选中），子节点 = 单个基因组 */
interface SpeciesTreeNode {
  id: string
  label: string
  children?: SpeciesTreeNode[]
}

const treeRef = ref<any>(null)
const selectedSpecies = ref<string[]>([])

/** 按 Genome_type 将 61 个基因组聚合成「分组 → 单个基因组」的树结构 */
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

/** 选中「全选」= 未勾选任何基因组 → 默认列表（any + 全部） */
const isAllSelected = computed(
  () => selectedSpecies.value.length === allSpeciesNames.value.length,
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

/** 树勾选变化：仅取叶子（单个基因组）key，勾选父分组会自动级联勾选其下所有基因组 */
function onTreeCheck(): void {
  const tree = treeRef.value
  if (!tree) return
  selectedSpecies.value = (tree.getCheckedKeys(true) as string[]) ?? []
}

// ============ 浏览 Tab：筛选 + 列表 ============
const ogIdFilter = ref('')
const annotationFilter = ref('')
const singleCopyOnly = ref(false)
const ogLimit = ref(20)
const ogOffset = ref(0)
const ogList = ref<OrthologOrthogroup[]>([])
const ogTotal = ref(0)
const ogLoading = ref(false)
const ogError = ref('')
const sortProp = ref('')
const sortOrder = ref<'ascending' | 'descending' | null>(null)

/** 真正发给后端的物种参数：未选则传全部（默认列表），有选则直接用 */
function resolveQuerySpecies(): string[] {
  return selectedSpecies.value.length ? selectedSpecies.value : allSpeciesNames.value
}
/** 未选任何基因组时，mode 用 any（默认列表）；有选时按 speciesMode */
const speciesMode = ref<'all' | 'any'>('all')
function resolveQueryMode(): 'all' | 'any' {
  return selectedSpecies.value.length ? speciesMode.value : 'any'
}

/** 客户端筛选 + 排序（应用于已加载的页面数据） */
const filteredOgs = computed<OrthologOrthogroup[]>(() => {
  const idKw = ogIdFilter.value.trim().toLowerCase()
  const annKw = annotationFilter.value.trim().toLowerCase()
  let list = ogList.value
  if (singleCopyOnly.value) list = list.filter((o) => o.is_single_copy)
  if (idKw) list = list.filter((o) => o.og_code.toLowerCase().includes(idKw))
  // 注释字段后端暂未提供，退化为对 og_code 匹配；补齐 annotation 后自动改为按注释匹配
  if (annKw) {
    list = list.filter(
      (o) =>
        (o.annotation ?? o.og_code).toLowerCase().includes(annKw),
    )
  }
  if (sortProp.value && sortOrder.value) {
    const dir = sortOrder.value === 'ascending' ? 1 : -1
    const prop = sortProp.value as keyof OrthologOrthogroup
    list = [...list].sort((a, b) => {
      const va = a[prop] as number | string
      const vb = b[prop] as number | string
      if (va === vb) return 0
      return (va > vb ? 1 : -1) * dir
    })
  }
  return list
})

const ogHasMore = computed(() => ogList.value.length < ogTotal.value)

/** 拉取 OG 列表：reset=true 时回到首页 */
async function loadOgs(reset = true): Promise<void> {
  ogLoading.value = true
  ogError.value = ''
  if (reset) {
    ogOffset.value = 0
    ogList.value = []
  }
  // 防护：未取到任何物种名（meta 解析失败）时不发空 species 请求，避免后端 400
  const querySpecies = resolveQuerySpecies()
  if (querySpecies.length === 0) {
    ogLoading.value = false
    ogError.value = t('ortholog_not_found')
    return
  }
  try {
    const res = await getOrthogroupsBySpecies({
      species: querySpecies,
      mode: resolveQueryMode(),
      limit: ogLimit.value,
      offset: ogOffset.value,
    })
    ogTotal.value = res.total ?? 0
    const items = res.orthogroups ?? []
    ogList.value = reset ? items : [...ogList.value, ...items]
    if (!res.found && ogList.value.length === 0) {
      ogError.value = t('ortholog_not_found')
    }
  } catch {
    ogError.value = t('ortholog_not_found')
  } finally {
    ogLoading.value = false
  }
}

function loadMore(): void {
  if (!ogHasMore.value || ogLoading.value) return
  ogOffset.value += ogLimit.value
  loadOgs(false)
}

function handleSortChange(payload: { prop: string | null; order: 'ascending' | 'descending' | null }): void {
  sortProp.value = payload?.prop ?? ''
  sortOrder.value = payload?.order ?? null
}

watch(selectedSpecies, () => loadOgs(true), { deep: true })
watch(speciesMode, () => {
  if (selectedSpecies.value.length) loadOgs(true)
})

// ============ 明细抽屉 ============
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<OrthologOrthogroup | null>(null)
const detailGeneFilter = ref('')

const filteredMembers = computed<OrthologSpeciesMember[]>(() => {
  if (!detailData.value) return []
  const kw = detailGeneFilter.value.trim().toLowerCase()
  if (!kw) return detailData.value.species_members
  return detailData.value.species_members
    .map((m) => ({
      ...m,
      genes: m.genes.filter(
        (g) =>
          (g.ortho_gene || '').toLowerCase().includes(kw) ||
          (g.genemaster_geneid || '').toLowerCase().includes(kw),
      ),
    }))
    .filter((m) => m.genes.length > 0)
})

async function openDetail(ogCode: string): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detailData.value = null
  detailGeneFilter.value = ''
  try {
    detailData.value = await getOrthogroupDetailV2(ogCode)
  } finally {
    detailLoading.value = false
  }
}

function speciesName(member: OrthologSpeciesMember): string {
  return member.display_name || member.species
}

/** genemaster_geneid 有值则跳基因详情页 */
function openGene(genemasterGeneid: string | null): void {
  if (!genemasterGeneid) return
  router.push({ name: 'GenomeDetail', params: { key: genemasterGeneid } })
}

/** 点 OG id → 跳独立详情页（含 MSA / 树 / WGS / 串联重复）
 * 若左侧已筛选了特定基因组，则通过 query.species 传入选中基因组，
 * 详情页据此只展示这些基因组的成员（保持浏览筛选语义一致）。 */
function openOgDetail(ogCode: string): void {
  if (!ogCode) return
  const query =
    selectedSpecies.value.length === allSpeciesNames.value.length
      ? undefined
      : { species: selectedSpecies.value.join(',') }
  router.push({ name: 'OrthogroupDetail', params: { og_code: ogCode }, query })
}

// ============ Tab「按基因查」（走 Meilisearch Orthologs 索引） ============
// 设计：用户输入基因 id → 在 Orthologs 索引检索，命中按所属 og_code 聚合，
// 得到该基因参与的若干 OG；点击某个 OG → 用 og_code 过滤 + 分页拉取成员基因
// （替代 orthofinder 巨型 payload 接口，前端只取展示所需的分页窗口）。
const geneInput = ref('')
const geneLoading = ref(false)
const geneError = ref('')
/** 该基因命中的 OG 聚合条目（来自 Meilisearch 命中里提取去重的 og_code） */
interface GeneOgEntry {
  og_code: string
  species: string
  geneid: string
  genemaster_geneid: string
}
const geneOgs = ref<GeneOgEntry[]>([])
/** 选中的 OG（点击后用于加载成员基因） */
const selectedOg = ref<string>('')
const memberGenes = ref<GeneOgEntry[]>([])
const memberTotal = ref(0)
const memberOffset = ref(0)
const memberLimit = ref(20)
/** Meilisearch 代理限制 offset+limit ≤ 1000，分页拉取时不越界 */
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
    // 基因 id 检索：精确命中该基因，从 _formatted/字段取 og_code
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

/** 去重后的 og_code 列表（按首次出现顺序） */
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
  loadMembers(ogCode, true)
}

function loadMoreMembers(): void {
  if (!memberHasMore.value || memberLoading.value) return
  memberOffset.value += memberLimit.value
  loadMembers(selectedOg.value, false)
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

onMounted(async () => {
  const meta = await getOrthologMeta()
  metaList.value = meta
  await loadOgs(true)
  // 主页 Orthologs 检索深链：?og=OG0000001 直接跳到 OG 详情页
  const og = route.query.og as string | undefined
  if (og) {
    openOgDetail(og)
  }
})
</script>

<template>
  <div class="container ortholog-page">
    <h2 class="ortholog-page__title">{{ t('orthogroup') }}</h2>

    <el-tabs v-model="activeTab" class="ortholog-tabs">
      <!-- Tab 1：浏览 Orthogroup（合并后的主入口） -->
      <el-tab-pane :label="t('homology_browse')" name="browse">
        <el-row :gutter="16" class="ortholog-layout">
          <!-- 左侧：基因组复选框 -->
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
                @check="onTreeCheck"
              />
              <div class="genome-panel__count">
                {{ t('selected_genomes') }} {{ selectedSpecies.length }} / {{ allSpeciesNames.length }}
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：筛选 + 列表 -->
          <el-col :span="18">
            <el-card class="ortholog-card" shadow="never">
              <div class="browse-filters">
                <el-input
                  v-model="ogIdFilter"
                  class="browse-filters__id"
                  :placeholder="t('og_id_filter_placeholder')"
                  clearable
                  size="default"
                />
                <el-input
                  v-model="annotationFilter"
                  class="browse-filters__ann"
                  :placeholder="t('annotation_filter_placeholder')"
                  clearable
                  size="default"
                />
                <el-checkbox v-model="singleCopyOnly" size="default">
                  {{ t('homology_single_copy_only') }}
                </el-checkbox>
                <el-radio-group v-if="selectedSpecies.length" v-model="speciesMode" size="default">
                  <el-radio value="all">{{ t('shared_ogs') }}</el-radio>
                  <el-radio value="any">Any</el-radio>
                </el-radio-group>
              </div>

              <el-alert v-if="ogError" type="warning" :title="ogError" show-icon class="mb-4" />

              <div class="ortholog-oglist__total">
                {{ t('total') }} {{ ogTotal }} {{ t('records') }}
              </div>

              <el-table
                v-loading="ogLoading"
                :data="filteredOgs"
                stripe
                border
                size="small"
                :row-class-name="() => 'is-clickable'"
                @sort-change="handleSortChange"
                @row-click="(row: any) => openOgDetail(row.og_code)"
              >
                <el-table-column :label="t('og_code')" prop="og_code" min-width="160">
                  <template #default="scope">
                    <a class="og-link" @click="openOgDetail(scope.row.og_code)">{{ scope.row.og_code }}</a>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('species_count')"
                  prop="species_count"
                  width="140"
                  align="center"
                  sortable="custom"
                />
                <el-table-column
                  :label="t('gene_count')"
                  prop="gene_count"
                  width="130"
                  align="center"
                  sortable="custom"
                />
                <el-table-column :label="t('homology_single_copy')" width="120" align="center">
                  <template #default="scope">
                    <el-tag v-if="scope.row.is_single_copy" size="small" type="success">
                      {{ t('yes') }}
                    </el-tag>
                    <span v-else>{{ t('no') }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('homology_annotation')" min-width="180">
                  <template #default="scope">{{ scope.row.annotation || '-' }}</template>
                </el-table-column>
              </el-table>

              <div class="ortholog-oglist__more">
                <el-button v-if="ogHasMore" :loading="ogLoading" @click="loadMore">
                  {{ t('load_more') }}
                </el-button>
                <span v-else class="ortholog-oglist__end">{{ t('no_more') }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 2：按基因查直系同源（走 Meilisearch Orthologs 索引） -->
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

          <!-- 命中的 OG 列表（点击加载成员基因） -->
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

            <!-- 成员基因表（分页，替代重型明细接口） -->
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

    <!-- OG 成员明细抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="(detailData?.og_code || t('og_code'))"
      size="62%"
    >
      <div v-loading="detailLoading">
        <template v-if="detailData">
          <el-descriptions :column="2" border class="mb-4">
            <el-descriptions-item :label="t('og_code')">{{ detailData.og_code }}</el-descriptions-item>
            <el-descriptions-item :label="t('species_count')">{{ detailData.species_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('gene_count')">{{ detailData.gene_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('homology_single_copy')">
              {{ detailData.is_single_copy ? t('yes') : t('no') }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="browse-filters mb-4">
            <el-input
              v-model="detailGeneFilter"
              class="browse-filters__ann"
              :placeholder="t('detail_gene_filter_placeholder')"
              clearable
              size="default"
            />
          </div>

          <h4>{{ t('ortholog_genes') }}</h4>
          <el-table :data="filteredMembers" stripe border size="small">
            <el-table-column :label="t('ortholog_species')" min-width="220">
              <template #default="scope">{{ speciesName(scope.row) }}</template>
            </el-table-column>
            <el-table-column :label="t('n_genes')" prop="n" width="100" align="center" />
            <el-table-column :label="t('ortholog_genes')" min-width="420">
              <template #default="scope">
                <span v-for="(g, idx) in scope.row.genes" :key="g.ortho_gene" class="ortholog-gene">
                  <a
                    v-if="g.genemaster_geneid"
                    class="ortholog-gene__link"
                    @click="openGene(g.genemaster_geneid)"
                  >{{ g.genemaster_geneid }}</a>
                  <span v-else class="ortholog-gene__plain">{{ g.ortho_gene }}</span>
                  <span v-if="idx !== scope.row.genes.length - 1" class="ortholog-gene__sep">, </span>
                </span>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else :description="t('no_data')" />
      </div>
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
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.browse-filters__id {
  width: 240px;
}

.browse-filters__ann {
  width: 260px;
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

.ortholog-results {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.ortholog-og {
  border: 1px solid #e9ecef;
  border-radius: 12px;
}

.ortholog-og__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.ortholog-og__code {
  font-weight: 600;
  font-size: 1.05rem;
  color: #3a6ea5;
}

.ortholog-og__meta {
  margin-left: auto;
  color: #6c757d;
  font-size: 0.85rem;
}

.ortholog-gene {
  font-size: 0.9rem;
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

.ortholog-gene__sep {
  color: #adb5bd;
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

.mt-4 {
  margin-top: 1.5rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}
</style>
