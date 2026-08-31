<template>
  <div class="container mt-4 mb-5">
    <h1 class="page-title">Genome Browser</h1>
    <p class="page-subtitle mb-4">Browse and filter all available cotton genome assemblies</p>

    <!-- 筛选区 -->
    <el-card shadow="never" class="filter-card mb-4">
      <el-form :inline="true" :model="filters" class="filter-form" size="default">
        <el-form-item label="Keyword">
          <el-input
            v-model="filters.keyword"
            placeholder="Name, Species, Article..."
            clearable
            style="width: 240px"
            @keyup.enter="currentPage = 1"
            @clear="currentPage = 1"
          />
        </el-form-item>

        <el-form-item label="Cotton Species">
          <el-select
            v-model="filters.cottonSpecies"
            placeholder="All species"
            clearable
            filterable
            style="width: 240px"
            @change="currentPage = 1"
          >
            <el-option
              v-for="opt in cottonSpeciesOptions"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Genome Type">
          <el-select
            v-model="filters.genomeType"
            placeholder="All types"
            clearable
            filterable
            style="width: 160px"
            @change="currentPage = 1"
          >
            <el-option
              v-for="opt in genomeTypeOptions"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Category">
          <el-select
            v-model="filters.category"
            placeholder="All categories"
            clearable
            filterable
            style="width: 180px"
            @change="currentPage = 1"
          >
            <el-option
              v-for="opt in categoryOptions"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Ploidy">
          <el-select
            v-model="filters.ploidy"
            placeholder="All ploidies"
            clearable
            filterable
            style="width: 140px"
            @change="currentPage = 1"
          >
            <el-option
              v-for="opt in ploidyOptions"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Institution">
          <el-select
            v-model="filters.institution"
            placeholder="All institutions"
            clearable
            filterable
            style="width: 260px"
            @change="currentPage = 1"
          >
            <el-option
              v-for="opt in institutionOptions"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="currentPage = 1">Search</el-button>
          <el-button @click="resetFilters">Reset</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 加载状态 -->
    <el-skeleton v-if="genomeStore.loading" :rows="12" animated class="mb-4" />

    <template v-else>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <span class="table-info">
          Showing {{ startIndex }} to {{ endIndex }} of {{ filteredData.length }} genomes
        </span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredData.length"
        />
      </div>

      <el-table
        :data="pagedData"
        stripe
        border
        style="width: 100%"
        class="genome-table"
        :row-class-name="() => 'row-clickable'"
        @row-click="handleRowClick"
        empty-text="No genomes match the current filters"
      >
        <el-table-column label="No." type="index" width="60" align="center">
          <template #default="scope">
            {{ (currentPage - 1) * pageSize + scope.$index + 1 }}
          </template>
        </el-table-column>

        <el-table-column label="Genome Alias" min-width="240" prop="alias">
          <template #default="scope">
            <el-link type="primary" :underline="false" @click.stop="goDetail(scope.row)">
              {{ scope.row.alias || scope.row.name || '-' }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column label="Cotton Species" min-width="200" prop="Cotton_Species">
          <template #default="scope">
            {{ scope.row.Cotton_Species || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="Type" width="100" prop="Genome_type" align="center">
          <template #default="scope">
            <el-tag size="small" type="success">{{ scope.row.Genome_type || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Ploidy" width="100" prop="Ploidy" align="center">
          <template #default="scope">
            <el-tag size="small" type="warning">{{ scope.row.Ploidy || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Category" width="150" prop="Category">
          <template #default="scope">
            {{ scope.row.Category || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="Genome Size (Gb)" width="150" prop="Genome_size" align="right">
          <template #default="scope">
            {{ formatGenomeSize(scope.row.Genome_size) }}
          </template>
        </el-table-column>

        <el-table-column label="BUSCO" width="110" prop="Busco" align="center" sortable :sort-method="buscoSort">
          <template #default="scope">
            <el-tag
              size="small"
              :type="buscoTagType(scope.row.Busco)"
            >
              {{ formatBusco(scope.row.Busco) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="LAI" width="100" prop="LAI_value" align="center">
          <template #default="scope">
            {{ scope.row.LAI_value || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="Assembling Institution" min-width="220" prop="Assembling_institution">
          <template #default="scope">
            {{ scope.row.Assembling_institution || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="Article" min-width="160" prop="Article">
          <template #default="scope">
            {{ scope.row.Article || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="90" fixed="right" align="center">
          <template #default="scope">
            <el-button type="primary" link size="small" @click.stop="goDetail(scope.row)">
              Detail
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="d-flex justify-content-end mt-3">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredData.length"
        />
      </div>
    </template>

    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useGenomeStore } from '@/stores/modules/genome'
import type { Species } from '@/stores/modules/genome'

const router = useRouter()
const genomeStore = useGenomeStore()

// ============ 筛选条件 ============
interface Filters {
  keyword: string
  cottonSpecies: string
  genomeType: string
  category: string
  ploidy: string
  institution: string
}
const filters = reactive<Filters>({
  keyword: '',
  cottonSpecies: '',
  genomeType: '',
  category: '',
  ploidy: '',
  institution: '',
})

function resetFilters(): void {
  filters.keyword = ''
  filters.cottonSpecies = ''
  filters.genomeType = ''
  filters.category = ''
  filters.ploidy = ''
  filters.institution = ''
  currentPage.value = 1
}

// ============ 筛选下拉选项（从 speciesData 去重） ============
const cottonSpeciesOptions = computed(() =>
  [...new Set(genomeStore.speciesData.map((s) => s.Cotton_Species).filter(Boolean) as string[])].sort(),
)
const genomeTypeOptions = computed(() =>
  [...new Set(genomeStore.speciesData.map((s) => s.Genome_type).filter(Boolean) as string[])].sort(),
)
const categoryOptions = computed(() =>
  [...new Set(genomeStore.speciesData.map((s) => s.Category).filter(Boolean) as string[])].sort(),
)
const ploidyOptions = computed(() =>
  [...new Set(genomeStore.speciesData.map((s) => s.Ploidy).filter(Boolean) as string[])].sort(),
)
const institutionOptions = computed(() =>
  [...new Set(genomeStore.speciesData.map((s) => s.Assembling_institution).filter(Boolean) as string[])].sort(),
)

// ============ 筛选后数据 ============
const filteredData = computed<Species[]>(() => {
  const kw = filters.keyword.trim().toLowerCase()
  return genomeStore.speciesData.filter((row) => {
    if (filters.cottonSpecies && row.Cotton_Species !== filters.cottonSpecies) return false
    if (filters.genomeType && row.Genome_type !== filters.genomeType) return false
    if (filters.category && row.Category !== filters.category) return false
    if (filters.ploidy && row.Ploidy !== filters.ploidy) return false
    if (filters.institution && row.Assembling_institution !== filters.institution) return false
    if (kw) {
      const haystack = [
        row.name,
        row.alias,
        row.Cotton_Species,
        row.Article,
        row.Accession ?? undefined,
        row.Genome_type,
        row.Assembling_institution,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    return true
  })
})

// ============ 分页 ============
const currentPage = ref(1)
const pageSize = ref(20)

const startIndex = computed(() => {
  if (filteredData.value.length === 0) return 0
  return (currentPage.value - 1) * pageSize.value + 1
})
const endIndex = computed(() => Math.min(currentPage.value * pageSize.value, filteredData.value.length))

const pagedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

// 切换筛选/页大小后，若当前页超出范围则回到第一页
watch([filteredData, pageSize], () => {
  nextTick(() => {
    if (startIndex.value > endIndex.value && endIndex.value > 0) {
      currentPage.value = 1
    }
  })
})

// ============ 格式化工具 ============
function formatGenomeSize(size: number | null | undefined): string {
  if (size === null || size === undefined || isNaN(size as number)) return '-'
  // 转为 Gb，保留两位小数
  return (Number(size) / 1_000_000_000).toFixed(3)
}

function parseBusco(busco: string | undefined | null): number {
  if (!busco) return NaN
  const n = Number(String(busco).trim())
  if (isNaN(n)) return NaN
  // 0.952 => 95.2% 形式，若是 <1 的小数按百分比换算；>1 直接用
  return n <= 1 ? n * 100 : n
}

function formatBusco(busco: string | undefined | null): string {
  const n = parseBusco(busco)
  if (isNaN(n)) return '-'
  return `${n.toFixed(1)}%`
}

function buscoSort(a: Species, b: Species): number {
  const av = parseBusco(a.Busco)
  const bv = parseBusco(b.Busco)
  if (isNaN(av) && isNaN(bv)) return 0
  if (isNaN(av)) return -1
  if (isNaN(bv)) return 1
  return av - bv
}

function buscoTagType(busco: string | undefined | null): '' | 'success' | 'warning' | 'danger' | 'info' {
  const n = parseBusco(busco)
  if (isNaN(n)) return 'info'
  if (n >= 95) return 'success'
  if (n >= 90) return ''
  if (n >= 80) return 'warning'
  return 'danger'
}

// ============ 跳转详情 ============
function goDetail(row: Species): void {
  if (!row.name && !row.id) {
    ElMessage.warning('Cannot identify this genome')
    return
  }
  // 优先用 name 作为路径参数（更可读），name 不存在时退化为 id
  const key = row.name ?? String(row.id)
  router.push({
    path: `/genome/detail/${encodeURIComponent(key)}`,
  })
}

function handleRowClick(row: Species): void {
  goDetail(row)
}

// ============ 初始化 ============
onMounted(async () => {
  if (genomeStore.speciesData.length === 0) {
    await genomeStore.fetchGenomes()
  }
})
</script>

<style scoped>
.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}
.page-subtitle {
  color: #666;
}
.filter-card :deep(.el-card__body) {
  padding: 16px 20px 4px;
}
.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}
.table-info {
  color: #666;
  font-size: 0.875rem;
}
.genome-table :deep(.row-clickable) {
  cursor: pointer;
  transition: background-color 0.15s;
}
.genome-table :deep(.row-clickable:hover > td) {
  background-color: #ecf5ff !important;
}
.d-flex {
  display: flex;
}
.justify-content-between {
  justify-content: space-between;
}
.justify-content-end {
  justify-content: flex-end;
}
.align-items-center {
  align-items: center;
}
.mb-3 {
  margin-bottom: 1rem;
}
.mb-4 {
  margin-bottom: 1.5rem;
}
.mb-5 {
  margin-bottom: 3rem;
}
.mt-3 {
  margin-top: 1rem;
}
.mt-4 {
  margin-top: 1.5rem;
}
</style>
