<template>
  <div class="oga" v-loading="detailLoading">
    <el-alert
      v-if="detailError"
      type="warning"
      :title="detailError"
      show-icon
      :closable="false"
    />
    <template v-else-if="detail">
      <el-alert
        v-if="speciesFilter.length"
        class="oga-alert"
        type="info"
        :closable="false"
        :title="t('og_filter_notice', { n: speciesFilter.length })"
      />

      <el-tabs v-model="activeTab" class="oga-tabs" @tab-change="onTabChange">
        <!-- ==================== 概览 ==================== -->
        <el-tab-pane :label="t('og_tab_overview')" name="overview">
          <el-descriptions :column="compact ? 2 : 3" border class="oga-desc">
            <el-descriptions-item :label="t('og_code')">{{ detail.og_code }}</el-descriptions-item>
            <el-descriptions-item :label="t('gene_count')">{{ detail.gene_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('species_count')">{{ detail.species_count }}</el-descriptions-item>
            <el-descriptions-item v-if="detail.selected_species_count != null" :label="t('og_selected_species_count')">
              {{ detail.selected_species_count }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_single_copy')">
              <el-tag v-if="detail.is_single_copy" size="small" type="success">{{ t('yes') }}</el-tag>
              <span v-else>{{ t('no') }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_annotation')">
              {{ detail.annotation || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <el-alert
            v-if="detail.is_single_copy === false"
            class="oga-alert"
            type="info"
            :closable="false"
            :title="t('stats_single_copy_note')"
          />

          <h4 class="oga-subhead">{{ t('og_genome_distribution') }}</h4>
          <div v-show="speciesDist.length" ref="distRef" class="oga-chart" />
          <el-table
            :data="speciesDist"
            stripe
            border
            size="small"
            max-height="320"
            class="oga-table"
          >
            <el-table-column :label="t('ortholog_species')" min-width="240">
              <template #default="scope">{{ speciesName(scope.row) }}</template>
            </el-table-column>
            <el-table-column :label="t('n_genes')" prop="n" width="110" align="center" />
          </el-table>
        </el-tab-pane>

        <!-- ==================== 成员 ==================== -->
        <el-tab-pane :label="t('og_tab_members')" name="members">
          <div class="oga-toolbar">
            <el-input
              v-model="memberSearch"
              class="oga-toolbar__input"
              :placeholder="t('og_member_search_placeholder')"
              clearable
              size="small"
            />
            <el-select v-model="memberPageSize" size="small" class="oga-toolbar__size" @change="reloadMembers">
              <el-option v-for="s in [20, 50, 100, 200]" :key="s" :label="`${s} / ${t('og_page')}`" :value="s" />
            </el-select>
            <span class="oga-toolbar__meta">{{ t('total') }} {{ membersTotal }} {{ t('records') }}</span>
            <el-button size="small" :loading="membersLoading" @click="reloadMembers">
              {{ t('refresh') }}
            </el-button>
          </div>

          <el-alert v-if="membersError" type="warning" :title="membersError" show-icon :closable="false" class="oga-alert" />

          <el-table
            v-loading="membersLoading"
            :data="filteredMemberRows"
            stripe
            border
            size="small"
            class="oga-table"
            max-height="520"
          >
            <el-table-column :label="t('ortholog_species')" min-width="200">
              <template #default="scope">{{ scope.row.display_name || scope.row.species }}</template>
            </el-table-column>
            <el-table-column :label="t('ortholog_genes')" min-width="200">
              <template #default="scope">
                <a
                  v-if="scope.row.genemaster_geneid"
                  class="oga-link"
                  @click="openGene(scope.row.genemaster_geneid)"
                >{{ scope.row.genemaster_geneid }}</a>
                <span v-else>{{ scope.row.ortho_gene }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('og_ortho_gene_id')" min-width="180">
              <template #default="scope">
                <span class="oga-mono">{{ scope.row.ortho_gene }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('og_actions')" width="190" align="center">
              <template #default="scope">
                <el-button link type="primary" size="small" @click="queryOrthologs(scope.row)">
                  {{ t('og_action_orthologs') }}
                </el-button>
                <el-button link type="primary" size="small" @click="queryHog(scope.row)">
                  {{ t('og_action_hog') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="oga-pager">
            <el-pagination
              v-model:current-page="memberPage"
              :page-size="memberPageSize"
              :total="membersTotal"
              layout="prev, pager, next, jumper"
              background
              small
              :disabled="membersLoading"
              @current-change="loadMembers"
            />
          </div>
        </el-tab-pane>

        <!-- ==================== 直系同源 ==================== -->
        <el-tab-pane :label="t('og_tab_orthologs')" name="orthologs">
          <el-alert
            class="oga-alert"
            type="info"
            :closable="false"
            :title="t('og_orthologs_note')"
          />
          <div class="oga-toolbar">
            <el-input
              v-model="orthologGene"
              class="oga-toolbar__input"
              :placeholder="t('og_gene_input_placeholder')"
              clearable
              size="small"
              @keyup.enter="runOrthologs"
            />
            <el-button type="primary" size="small" :loading="orthologLoading" @click="runOrthologs">
              {{ t('search') }}
            </el-button>
          </div>

          <el-alert v-if="orthologError" type="warning" :title="orthologError" show-icon :closable="false" class="oga-alert" />
          <el-alert
            v-else-if="orthologResult?.note"
            type="info"
            :title="orthologResult.note"
            :closable="false"
            class="oga-alert"
          />

          <template v-if="orthologResult?.results?.length">
            <div v-for="sp in orthologResult.results" :key="sp.species" class="oga-block">
              <h4 class="oga-subhead">{{ sp.species }}</h4>
              <el-alert
                v-if="sp.error"
                type="warning"
                :title="sp.error"
                show-icon
                :closable="false"
                class="oga-alert"
              />
              <el-table :data="flattenOrthologPartners(sp)" stripe border size="small" class="oga-table">
                <el-table-column :label="t('og_code')" prop="og_code" min-width="150" />
                <el-table-column :label="t('og_partner_species')" prop="species" min-width="200" />
                <el-table-column :label="t('og_partner_genes')" min-width="260">
                  <template #default="scope">
                    <span v-for="(g, i) in scope.row.genes" :key="g" class="oga-gene-inline">
                      {{ g }}<span v-if="i !== scope.row.genes.length - 1">, </span>
                    </span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('og_relation_type')" width="150" align="center">
                  <template #default="scope">
                    <el-tag size="small">{{ scope.row.relation_type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('og_query_partner_counts')" width="150" align="center">
                  <template #default="scope">
                    {{ scope.row.query_gene_count }} / {{ scope.row.partner_gene_count }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
          <el-empty
            v-else-if="orthologQueried && !orthologLoading && !orthologError"
            :description="t('og_orthologs_empty')"
          />
        </el-tab-pane>

        <!-- ==================== HOG ==================== -->
        <el-tab-pane :label="t('og_tab_hog')" name="hog">
          <div class="oga-toolbar">
            <el-input
              v-model="hogGene"
              class="oga-toolbar__input"
              :placeholder="t('og_gene_input_placeholder')"
              clearable
              size="small"
              @keyup.enter="runHog"
            />
            <el-button type="primary" size="small" :loading="hogLoading" @click="runHog">
              {{ t('search') }}
            </el-button>
          </div>

          <el-alert v-if="hogError" type="warning" :title="hogError" show-icon :closable="false" class="oga-alert" />

          <el-table
            v-if="hogResult?.hogs?.length"
            :data="hogResult.hogs"
            stripe
            border
            size="small"
            class="oga-table is-clickable"
            @row-click="(row: any) => openHog(row.hog_id)"
          >
            <el-table-column :label="t('og_hog_id')" min-width="170">
              <template #default="scope">
                <a class="oga-link">{{ scope.row.hog_id }}</a>
              </template>
            </el-table-column>
            <el-table-column :label="t('og_hog_node')" prop="node" width="90" align="center" />
            <el-table-column :label="t('og_code')" prop="og_code" min-width="140" />
            <el-table-column :label="t('og_hog_parent_clade')" prop="parent_clade" width="130" align="center" />
            <el-table-column :label="t('species_count')" prop="species_count" width="110" align="center" />
            <el-table-column :label="t('gene_count')" prop="gene_count" width="110" align="center" />
          </el-table>
          <el-empty
            v-else-if="hogQueried && !hogLoading && !hogError"
            :description="t('og_hog_empty')"
          />

          <el-card v-if="hogDetail" class="oga-card" shadow="never">
            <template #header>
              <div class="oga-card__head">
                <span>{{ t('og_hog_detail') }} · {{ hogDetail.hog_id }}</span>
                <el-button link type="primary" size="small" @click="hogDetail = null">
                  {{ t('close') }}
                </el-button>
              </div>
            </template>
            <el-alert v-if="hogDetail.error" type="warning" :title="hogDetail.error" show-icon :closable="false" />
            <template v-else>
              <el-descriptions :column="compact ? 2 : 3" border class="oga-desc">
                <el-descriptions-item :label="t('og_hog_node')">{{ hogDetail.node || '-' }}</el-descriptions-item>
                <el-descriptions-item :label="t('og_code')">{{ hogDetail.og_code || '-' }}</el-descriptions-item>
                <el-descriptions-item :label="t('og_hog_parent_clade')">{{ hogDetail.parent_clade || '-' }}</el-descriptions-item>
                <el-descriptions-item :label="t('species_count')">{{ hogDetail.species_count ?? '-' }}</el-descriptions-item>
                <el-descriptions-item :label="t('gene_count')">{{ hogDetail.gene_count ?? '-' }}</el-descriptions-item>
              </el-descriptions>
              <h4 class="oga-subhead">{{ t('og_hog_members') }}</h4>
              <el-table :data="hogDetail.members || []" stripe border size="small" class="oga-table" max-height="320">
                <el-table-column :label="t('ortholog_species')" prop="species" min-width="220" />
                <el-table-column :label="t('n_genes')" prop="n" width="100" align="center" />
                <el-table-column :label="t('ortholog_genes')" min-width="300">
                  <template #default="scope">{{ (scope.row.genes || []).join(', ') }}</template>
                </el-table-column>
              </el-table>
            </template>
          </el-card>
        </el-tab-pane>

        <!-- ==================== 复制事件 ==================== -->
        <el-tab-pane :label="t('og_tab_tandem')" name="tandem">
          <div class="oga-toolbar">
            <el-button size="small" :loading="tandemLoading" @click="loadTandem">
              {{ t('og_tandem_load') }}
            </el-button>
            <span v-if="tandemSummary" class="oga-toolbar__meta">
              {{ t('og_tandem_total_events') }}: {{ tandemSummary.total_events }}
            </span>
          </div>

          <el-alert v-if="tandemError" type="warning" :title="tandemError" show-icon :closable="false" class="oga-alert" />

          <template v-if="tandemSummary">
            <div class="oga-tags">
              <el-tag
                v-for="(count, type) in tandemSummary.by_type"
                :key="type"
                size="small"
                type="info"
              >{{ type }}: {{ count }}</el-tag>
            </div>

            <h4 class="oga-subhead">{{ t('og_tandem_species_summary') }}</h4>
            <el-table :data="tandemSpeciesRows" stripe border size="small" class="oga-table" max-height="280">
              <el-table-column :label="t('ortholog_species')" prop="species" min-width="220" />
              <el-table-column :label="t('ortholog_genes')" min-width="320">
                <template #default="scope">{{ scope.row.genes }}</template>
              </el-table-column>
              <el-table-column :label="t('og_tandem_dup_count')" prop="total" width="120" align="center" />
            </el-table>

            <div class="oga-toolbar oga-toolbar--gap">
              <el-button size="small" :loading="tandemEventsLoading" :disabled="!tandemSummary.total_events" @click="loadTandemEvents(true)">
                {{ t('og_tandem_load_events') }}
              </el-button>
            </div>

            <el-table
              v-if="tandemEvents.length"
              v-loading="tandemEventsLoading"
              :data="tandemEvents"
              stripe
              border
              size="small"
              class="oga-table"
              max-height="360"
            >
              <el-table-column :label="t('ortholog_species')" prop="species" min-width="200" />
              <el-table-column :label="t('og_tandem_type')" prop="type" width="140" />
              <el-table-column :label="t('og_tandem_support')" prop="support" width="100" align="center" />
              <el-table-column :label="t('og_tandem_node')" prop="gene_tree_node" width="130" />
              <el-table-column :label="t('ortholog_genes')" min-width="300">
                <template #default="scope">
                  {{ [...(scope.row.genes1 || []), ...(scope.row.genes2 || [])].join(', ') }}
                </template>
              </el-table-column>
            </el-table>
            <div v-if="tandemEvents.length" class="oga-toolbar oga-toolbar--gap">
              <el-button
                v-if="tandemSummary.has_more"
                size="small"
                :loading="tandemEventsLoading"
                @click="loadTandemEvents(false)"
              >{{ t('load_more') }}</el-button>
              <span v-else class="oga-toolbar__meta">{{ t('no_more') }}</span>
            </div>
          </template>
          <el-empty
            v-else-if="tandemLoaded && !tandemLoading && !tandemError"
            :description="t('og_tandem_empty')"
          />
        </el-tab-pane>

        <!-- ==================== MSA ==================== -->
        <el-tab-pane :label="t('og_tab_msa')" name="msa">
          <div class="oga-toolbar">
            <el-button
              v-if="!msaLoaded"
              size="small"
              :loading="msaLoading"
              @click="loadMsa"
            >{{ t('og_msa_load') }}</el-button>
            <el-button v-else size="small" :loading="msaLoading" @click="loadMsa">
              {{ t('refresh') }}
            </el-button>
            <a class="oga-download" :href="fileUrl('msa')" target="_blank" rel="noopener">
              {{ t('og_msa_download') }}
            </a>
          </div>

          <el-alert
            v-if="isLargeOg && !msaLoaded"
            class="oga-alert"
            type="warning"
            :closable="false"
            :title="t('og_msa_large_hint', { n: detail.gene_count })"
          />
          <el-alert v-if="msaError" type="info" :title="msaError" show-icon :closable="false" class="oga-alert" />
          <div v-loading="msaLoading">
            <MsaViewer v-if="msaText" :fasta="msaText" />
            <el-empty v-else-if="msaLoaded && !msaError && !msaLoading" :description="t('no_data')" />
          </div>
        </el-tab-pane>

        <!-- ==================== 基因树 ==================== -->
        <el-tab-pane :label="t('og_tab_tree')" name="tree">
          <div class="oga-toolbar">
            <el-button size="small" :loading="treeLoading" @click="loadTree">
              {{ treeText ? t('refresh') : t('og_tree_load') }}
            </el-button>
            <el-button size="small" :disabled="!treeText" @click="downloadTree">
              {{ t('og_tree_download') }}
            </el-button>
          </div>
          <el-alert v-if="treeError" type="info" :title="treeError" show-icon :closable="false" class="oga-alert" />
          <div v-loading="treeLoading">
            <PhylocanvasViewer v-if="treeText" :newick="treeText" />
            <el-empty v-else-if="treeLoaded && !treeError && !treeLoading" :description="t('no_data')" />
          </div>
        </el-tab-pane>

        <!-- ==================== 序列 ==================== -->
        <el-tab-pane :label="t('og_tab_sequence')" name="sequence">
          <div class="oga-toolbar">
            <el-button size="small" :loading="seqLoading" @click="loadSequence">
              {{ seqText ? t('refresh') : t('og_sequence_load') }}
            </el-button>
            <a class="oga-download" :href="fileUrl('sequences')" target="_blank" rel="noopener">
              {{ t('og_sequence_download') }}
            </a>
          </div>
          <el-alert v-if="seqError" type="info" :title="seqError" show-icon :closable="false" class="oga-alert" />
          <div v-loading="seqLoading">
            <pre v-if="seqText" class="oga-fasta">{{ seqText }}</pre>
            <el-empty v-else-if="seqLoaded && !seqError && !seqLoading" :description="t('no_data')" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
    <el-empty v-else :description="t('no_data')" />
  </div>
</template>

<script setup lang="ts">
/**
 * 单个 Orthogroup 的分析面板（概览 / 成员 / 直系同源 / HOG / 复制事件 / MSA / 基因树 / 序列）。
 *
 * 复用位置：
 *  - OrthologView 的 OG 抽屉（compact=true，在当前页面内查看详情）
 *  - OrthogroupDetailView 详情页（compact=false）
 *
 * 数据口径严格遵循后端 v1 契约（服务器 backend/docs/api/endpoints.md「orthofinder」段，
 * 前端整理版见 docs/COMPARATIVE_ANALYSIS_API_HANDOFF.md）：
 *  - “同一 OG 的成员”不是 Ortholog；只有 genes/orthologs 结果标注为直系同源。
 *  - 大 OG 成员用 orthogroups/members 分页；MSA / 基因树 / 序列按需加载。
 *  - 基因级接口（orthologs / hogs）只认 OrthoFinder 基因 ID（带转录本后缀，如 xxx.1），
 *    不带后缀的 Gene ID 先经 resolveOrthoGeneId 归一后再查。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import echarts from '@/utils/echarts'
import MsaViewer from '@/components/data-display/MsaViewer.vue'
import PhylocanvasViewer from '@/components/data-display/PhylocanvasViewer.vue'
import {
  getGeneHog,
  getGeneOrthologs,
  getHogDetail,
  getOgMembers,
  getOrthofinderTandem,
  getOrthogroupDetailV2,
  getOrthogroupMsa,
  getOrthogroupSequence,
  getOrthogroupTree,
  resolveOrthoGeneId,
  type GeneHogHit,
  type GeneOrthologSpeciesResult,
  type GeneOrthologsResponse,
  type HogDetailResponse,
  type OgMemberRow,
  type OrthofinderTandemEvent,
  type OrthofinderTandemSummary,
  type OrthologOrthogroup,
  type OrthologSpeciesMember,
} from '@/api/index'

const props = defineProps<{
  ogCode: string
  /** 浏览页所选基因组；为空表示展示全部成员 */
  speciesFilter?: string[]
  /** 抽屉内更紧凑的排版 */
  compact?: boolean
}>()

const { t } = useI18n()
const router = useRouter()

const speciesFilter = computed(() => props.speciesFilter ?? [])
const activeTab = ref('overview')

// ==================== 概览 ====================
const detailLoading = ref(false)
const detailError = ref('')
const detail = ref<OrthologOrthogroup | null>(null)

/** 各物种成员数（include_genes=0 时后端仍返回 species_members 的 n） */
const speciesDist = computed<OrthologSpeciesMember[]>(() => {
  const members = detail.value?.species_members ?? []
  return [...members].sort((a, b) => b.n - a.n)
})

const distRef = ref<HTMLElement | null>(null)
let distChart: ReturnType<typeof echarts.init> | null = null

function speciesName(member: { display_name?: string; species: string }): string {
  return member.display_name || member.species
}

function renderDistribution(): void {
  if (!distRef.value || speciesDist.value.length === 0) return
  if (!distChart) distChart = echarts.init(distRef.value)
  const top = speciesDist.value.slice(0, 20).slice().reverse()
  distChart.setOption({
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', name: t('n_genes'), minInterval: 1 },
    yAxis: {
      type: 'category',
      data: top.map((m) => speciesName(m)),
      axisLabel: { fontSize: 11, width: 180, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: top.map((m) => m.n),
      itemStyle: { color: '#3a6ea5', borderRadius: [0, 4, 4, 0] },
      barMaxWidth: 14,
    }],
  }, true)
}

function handleResize(): void {
  distChart?.resize()
}

async function loadDetail(): Promise<void> {
  detailLoading.value = true
  detailError.value = ''
  detail.value = null
  try {
    const data = await getOrthogroupDetailV2(props.ogCode, {
      species: speciesFilter.value.length ? speciesFilter.value : undefined,
      // 大 OG 只取物种与计数；成员统一走 og_members 分页
      includeGenes: false,
    })
    if (!data) {
      detailError.value = t('ortholog_not_found')
      return
    }
    detail.value = data
    await nextTick()
    renderDistribution()
  } catch {
    detailError.value = t('ortholog_not_found')
  } finally {
    detailLoading.value = false
  }
}

// ==================== 成员（og_members 分页） ====================
const memberRows = ref<OgMemberRow[]>([])
const membersTotal = ref(0)
const memberPage = ref(1)
const memberPageSize = ref(50)
const membersLoading = ref(false)
const membersError = ref('')
const memberSearch = ref('')

const filteredMemberRows = computed<OgMemberRow[]>(() => {
  const kw = memberSearch.value.trim().toLowerCase()
  if (!kw) return memberRows.value
  return memberRows.value.filter(
    (r) =>
      (r.ortho_gene || '').toLowerCase().includes(kw) ||
      (r.genemaster_geneid || '').toLowerCase().includes(kw) ||
      (r.species || '').toLowerCase().includes(kw) ||
      (r.display_name || '').toLowerCase().includes(kw),
  )
})

async function loadMembers(): Promise<void> {
  if (!props.ogCode) return
  membersLoading.value = true
  membersError.value = ''
  try {
    const res = await getOgMembers({
      og_code: props.ogCode,
      species: speciesFilter.value.length ? speciesFilter.value : undefined,
      limit: memberPageSize.value,
      offset: (memberPage.value - 1) * memberPageSize.value,
    })
    memberRows.value = res.members ?? []
    membersTotal.value = res.total ?? 0
  } catch (err) {
    membersError.value = (err as Error)?.message || t('request_failed')
    memberRows.value = []
    membersTotal.value = 0
  } finally {
    membersLoading.value = false
  }
}

function reloadMembers(): void {
  memberPage.value = 1
  void loadMembers()
}

function openGene(genemasterGeneid: string | null): void {
  if (!genemasterGeneid) return
  router.push({ name: 'GenomeDetail', params: { key: genemasterGeneid } })
}

// ==================== 直系同源（gene_orthologs） ====================
const orthologGene = ref('')
const orthologLoading = ref(false)
const orthologQueried = ref(false)
const orthologError = ref('')
const orthologResult = ref<GeneOrthologsResponse | null>(null)

interface OrthologFlatRow {
  og_code: string
  species: string
  genes: string[]
  relation_type: string
  query_gene_count: number
  partner_gene_count: number
}

function flattenOrthologPartners(sp: GeneOrthologSpeciesResult): OrthologFlatRow[] {
  const rows: OrthologFlatRow[] = []
  for (const og of sp.orthogroups ?? []) {
    for (const partner of og.partners ?? []) {
      rows.push({
        og_code: og.og_code,
        species: partner.species,
        genes: partner.genes ?? [],
        relation_type: partner.relation_type,
        query_gene_count: partner.query_gene_count,
        partner_gene_count: partner.partner_gene_count,
      })
    }
  }
  return rows
}

async function runOrthologs(): Promise<void> {
  const geneid = orthologGene.value.trim()
  if (!geneid) {
    orthologError.value = t('og_gene_input_placeholder')
    return
  }
  orthologLoading.value = true
  orthologError.value = ''
  orthologQueried.value = true
  orthologResult.value = null
  try {
    // OrthoFinder 基因级接口只认带转录本后缀的 ID，先归一再查
    const res = await getGeneOrthologs({ geneid: await resolveOrthoGeneId(geneid) })
    if (res.error) {
      orthologError.value = res.error
      return
    }
    orthologResult.value = res
  } finally {
    orthologLoading.value = false
  }
}

function queryOrthologs(row: OgMemberRow): void {
  // ortho_gene 是 OrthoFinder 蛋白 ID（带后缀），是后端基因级接口认的键
  orthologGene.value = row.ortho_gene || row.genemaster_geneid
  activeTab.value = 'orthologs'
  void runOrthologs()
}

// ==================== HOG（gene_hog / hog_detail） ====================
const hogGene = ref('')
const hogLoading = ref(false)
const hogQueried = ref(false)
const hogError = ref('')
const hogResult = ref<{ hogs: GeneHogHit[] } | null>(null)
const hogDetail = ref<HogDetailResponse | null>(null)

async function runHog(): Promise<void> {
  const geneid = hogGene.value.trim()
  if (!geneid) {
    hogError.value = t('og_gene_input_placeholder')
    return
  }
  hogLoading.value = true
  hogError.value = ''
  hogQueried.value = true
  hogResult.value = null
  hogDetail.value = null
  try {
    const res = await getGeneHog({ geneid: await resolveOrthoGeneId(geneid) })
    if (res.error) {
      hogError.value = res.error
      return
    }
    hogResult.value = res
  } finally {
    hogLoading.value = false
  }
}

function queryHog(row: OgMemberRow): void {
  hogGene.value = row.ortho_gene || row.genemaster_geneid
  activeTab.value = 'hog'
  void runHog()
}

async function openHog(hogId: string): Promise<void> {
  hogDetail.value = await getHogDetail(hogId)
}

// ==================== 复制事件（tandem 分页） ====================
const tandemSummary = ref<OrthofinderTandemSummary | null>(null)
const tandemLoading = ref(false)
const tandemLoaded = ref(false)
const tandemError = ref('')
const tandemEvents = ref<OrthofinderTandemEvent[]>([])
const tandemEventsLoading = ref(false)
const TANDEM_EVENT_PAGE = 100

/** species 汇总扁平行：{ species, genes: "gene1(2), gene2", total } */
const tandemSpeciesRows = computed(() => {
  const species = tandemSummary.value?.species ?? {}
  return Object.entries(species).map(([sp, genes]) => ({
    species: sp,
    genes: genes.map((g) => `${g.geneid}(${g.n})`).join(', '),
    total: genes.reduce((sum, g) => sum + g.n, 0),
  }))
})

async function loadTandem(): Promise<void> {
  tandemLoading.value = true
  tandemError.value = ''
  tandemLoaded.value = true
  tandemEvents.value = []
  try {
    // 先只取汇总，避免超大 OG 一次拉回全部事件
    tandemSummary.value = await getOrthofinderTandem(props.ogCode, { includeEvents: false })
  } catch (err) {
    tandemError.value = (err as Error)?.message || t('request_failed')
    tandemSummary.value = null
  } finally {
    tandemLoading.value = false
  }
}

async function loadTandemEvents(reset: boolean): Promise<void> {
  if (reset) tandemEvents.value = []
  tandemEventsLoading.value = true
  tandemError.value = ''
  try {
    const res = await getOrthofinderTandem(props.ogCode, {
      limit: TANDEM_EVENT_PAGE,
      offset: tandemEvents.value.length,
      includeEvents: true,
    })
    if (!res) return
    // 汇总字段始终以本次响应为准（与分页无关）
    tandemSummary.value = { ...(tandemSummary.value as OrthofinderTandemSummary), ...res }
    tandemEvents.value = reset ? (res.events ?? []) : [...tandemEvents.value, ...(res.events ?? [])]
  } catch (err) {
    tandemError.value = (err as Error)?.message || t('request_failed')
  } finally {
    tandemEventsLoading.value = false
  }
}

// ==================== MSA / 树 / 序列（按需加载） ====================
const msaText = ref('')
const msaLoading = ref(false)
const msaLoaded = ref(false)
const msaError = ref('')

const treeText = ref('')
const treeLoading = ref(false)
const treeLoaded = ref(false)
const treeError = ref('')

const seqText = ref('')
const seqLoading = ref(false)
const seqLoaded = ref(false)
const seqError = ref('')

/** 大 OG（成员数 > 300）默认不自动拉取 MSA，避免 100 MB 级响应阻塞页面 */
const isLargeOg = computed(() => (detail.value?.gene_count ?? 0) > 300)

async function loadMsa(): Promise<void> {
  msaLoading.value = true
  msaError.value = ''
  msaLoaded.value = true
  try {
    const txt = await getOrthogroupMsa(props.ogCode)
    if (!txt) msaError.value = t('og_module_not_ready')
    else msaText.value = txt
  } finally {
    msaLoading.value = false
  }
}

async function loadTree(): Promise<void> {
  treeLoading.value = true
  treeError.value = ''
  treeLoaded.value = true
  try {
    const txt = await getOrthogroupTree(props.ogCode)
    if (!txt) {
      treeError.value = t('og_tree_not_found')
      treeText.value = ''
    } else {
      treeText.value = txt.trim()
    }
  } finally {
    treeLoading.value = false
  }
}

async function loadSequence(): Promise<void> {
  seqLoading.value = true
  seqError.value = ''
  seqLoaded.value = true
  try {
    const txt = await getOrthogroupSequence(props.ogCode)
    if (!txt) seqError.value = t('og_module_not_ready')
    else seqText.value = txt
  } finally {
    seqLoading.value = false
  }
}

/** 文件接口直链（复用后端 FileResponse 下载能力，避免把大文件读进内存） */
function fileUrl(kind: 'msa' | 'sequences'): string {
  return `/CottonOGD_api/api/v1/orthofinder/og/${encodeURIComponent(props.ogCode)}/${kind}/`
}

function downloadTree(): void {
  if (!treeText.value) return
  const blob = new Blob([treeText.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.ogCode}.treefile`
  a.click()
  URL.revokeObjectURL(url)
}

// ==================== 标签页切换：按需加载 ====================
function onTabChange(name: string | number): void {
  if (name === 'members') void loadMembers()
  if (name === 'msa' && !msaLoaded.value && !isLargeOg.value) void loadMsa()
  if (name === 'tree' && !treeLoaded.value) void loadTree()
  if (name === 'sequence' && !seqLoaded.value) void loadSequence()
  if (name === 'tandem' && !tandemLoaded.value) void loadTandem()
}

// ==================== 重置 / 生命周期 ====================
function resetAll(): void {
  activeTab.value = 'overview'
  memberRows.value = []
  membersTotal.value = 0
  memberPage.value = 1
  memberSearch.value = ''
  membersError.value = ''
  orthologGene.value = ''
  orthologResult.value = null
  orthologError.value = ''
  orthologQueried.value = false
  hogGene.value = ''
  hogResult.value = null
  hogError.value = ''
  hogQueried.value = false
  hogDetail.value = null
  tandemSummary.value = null
  tandemLoaded.value = false
  tandemError.value = ''
  tandemEvents.value = []
  msaText.value = ''
  msaLoaded.value = false
  msaError.value = ''
  treeText.value = ''
  treeLoaded.value = false
  treeError.value = ''
  seqText.value = ''
  seqLoaded.value = false
  seqError.value = ''
  distChart?.dispose()
  distChart = null
}

async function initialize(): Promise<void> {
  resetAll()
  await loadDetail()
}

watch(() => props.ogCode, () => { void initialize() })
watch(() => props.speciesFilter, () => { void initialize() }, { deep: true })

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void initialize()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  distChart?.dispose()
  distChart = null
})
</script>

<style scoped>
.oga {
  min-height: 120px;
}
.oga-tabs {
  --el-color-primary: #3a6ea5;
}
.oga-alert {
  margin-bottom: 0.75rem;
}
.oga-desc {
  margin-bottom: 1rem;
}
.oga-subhead {
  font-size: 0.95rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 1rem 0 0.5rem;
}
.oga-chart {
  width: 100%;
  height: 320px;
  margin-bottom: 0.75rem;
}
.oga-table {
  width: 100%;
}
.oga-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
.oga-toolbar--gap {
  margin-top: 0.75rem;
}
.oga-toolbar__input {
  width: 280px;
}
.oga-toolbar__size {
  width: 130px;
}
.oga-toolbar__meta {
  color: #6c757d;
  font-size: 0.85rem;
}
.oga-pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.75rem;
}
.oga-link {
  color: #3a6ea5;
  cursor: pointer;
  text-decoration: none;
}
.oga-link:hover {
  text-decoration: underline;
}
.oga-mono {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.82rem;
  color: #495057;
}
.oga-gene-inline {
  font-size: 0.85rem;
}
.oga-block {
  margin-bottom: 1rem;
}
.oga-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.oga-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  margin-top: 1rem;
}
.oga-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
.oga-download {
  color: #3a6ea5;
  font-size: 0.85rem;
  text-decoration: none;
}
.oga-download:hover {
  text-decoration: underline;
}
.oga-fasta {
  max-height: 420px;
  overflow: auto;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 0.75rem;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.82rem;
  white-space: pre;
  color: #495057;
}
</style>
