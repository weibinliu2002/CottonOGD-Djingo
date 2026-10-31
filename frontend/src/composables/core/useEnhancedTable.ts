/**
 * 增强表格组合式函数（阶段 3.2）
 *
 * 对标 SoyOmics 的结果表格：排序 + 关键词筛选 + 分页 + 导出。
 * 本项目 9 个结果页此前均为「裸表格」：无排序、无筛选，
 * 分页写法三种并存（el-pagination / 手写 slice / 无分页），导出能力各不相同。
 *
 * 本函数只做「数据视图层」的包装，不触碰任何数据获取逻辑，
 * 因此对既有数据流零侵入：把原来的全量数组传进来，拿 pagedData 去渲染即可。
 *
 * 典型用法：
 *   const table = useEnhancedTable(allResults, { pageSize: 10, searchFields: ['go_id', 'description'] })
 *   // 模板：:data="table.pagedData"  @sort-change="table.handleSortChange"
 *   //       v-model="table.keyword"
 *   //       :current-page="table.currentPage" :page-size="table.pageSize" :total="table.total"
 */
import { ref, computed, watch, reactive, type Ref } from 'vue'
import { useTablePagination, type UseTablePaginationOptions } from './useTablePagination'
import { exportCsv, type ExportColumn } from '@/utils/exportTable'

/** 排序方向，取值与 Element Plus el-table 的 sort-change 事件一致 */
export type SortOrder = 'ascending' | 'descending' | null

export interface EnhancedTableOptions extends UseTablePaginationOptions {
  /** 关键词筛选命中的字段名；留空表示不启用关键词筛选 */
  searchFields?: string[]
}

/** 判断单元格值是否为空（空值统一排在末尾，不受升降序影响） */
function isEmpty(value: unknown): boolean {
  return value === null || value === undefined || value === ''
}

/** 通用比较器：能转数字则按数值比，否则按本地化字符串比（支持中文、数字自然序） */
function compareValues(a: unknown, b: unknown): number {
  if (a === b) return 0
  const na = Number(a)
  const nb = Number(b)
  const bothNumeric =
    String(a).trim() !== '' &&
    String(b).trim() !== '' &&
    !Number.isNaN(na) &&
    !Number.isNaN(nb)
  if (bothNumeric) return na - nb
  return String(a).localeCompare(String(b), 'zh-Hans-CN', { numeric: true })
}

/**
 * 给已有表格套上排序 / 关键词筛选 / 分页 / 导出。
 *
 * @param source 全量数据（ref 或 getter），保持原有数据来源不变
 * @param options 每页条数、可选条数、关键词命中字段
 */
export function useEnhancedTable<T extends Record<string, any>>(
  source: Ref<T[]> | (() => T[]),
  options: EnhancedTableOptions = {},
) {
  const { searchFields = [] } = options

  /** 关键词筛选框的值 */
  const keyword = ref('')
  /** 当前排序列 */
  const sortProp = ref('')
  /** 当前排序方向 */
  const sortOrder = ref<SortOrder>(null)

  const rows = computed<T[]>(() => (typeof source === 'function' ? source() : source.value))

  /** 关键词筛选后的数据 */
  const filteredRows = computed<T[]>(() => {
    const kw = keyword.value.trim().toLowerCase()
    if (!kw || searchFields.length === 0) return rows.value
    return rows.value.filter((row) =>
      searchFields.some((field) => String(row?.[field] ?? '').toLowerCase().includes(kw)),
    )
  })

  /** 排序后的数据 */
  const sortedRows = computed<T[]>(() => {
    if (!sortProp.value || !sortOrder.value) return filteredRows.value
    const dir = sortOrder.value === 'ascending' ? 1 : -1
    return [...filteredRows.value].sort((a, b) => {
      const va = a?.[sortProp.value]
      const vb = b?.[sortProp.value]
      // 空值恒排末尾：不受升序/降序切换影响，避免翻页时用户误判
      if (isEmpty(va) && isEmpty(vb)) return 0
      if (isEmpty(va)) return 1
      if (isEmpty(vb)) return -1
      return compareValues(va, vb) * dir
    })
  })

  const pagination = useTablePagination<T>(sortedRows, options)

  /** 绑定 el-table 的 @sort-change；排序后回到第一页 */
  function handleSortChange(payload: { prop: string | null; order: SortOrder }): void {
    sortProp.value = payload?.prop ?? ''
    sortOrder.value = payload?.order ?? null
    pagination.resetPage()
  }

  // 筛选条件变化时回到第一页，避免停在空页
  watch(keyword, () => {
    pagination.resetPage()
  })

  /** 导出当前筛选+排序后的全部结果（不是仅当前页） */
  function exportRows(columns: ExportColumn<T>[], filename?: string): void {
    exportCsv(sortedRows.value, columns, filename)
  }

  return reactive({
    /** 关键词筛选框绑定值 */
    keyword,
    sortProp,
    sortOrder,
    filteredRows,
    sortedRows,
    ...pagination,
    handleSortChange,
    exportRows,
  })
}
