/**
 * 表格分页组合式函数（阶段 2）
 *
 * 统一项目内三种分页写法：
 * - el-pagination（9 处，标准）
 * - GeneExpressionResultView 的手写切片（paginatedResults）
 * - HomeView 的手写页码（currentPage / hasNextPage）
 *
 * 提供：分页状态、分页后的数据、页码变化回调、重置、序号计算。
 */
import { ref, computed, watch, type Ref } from 'vue'

export interface UseTablePaginationOptions {
  /** 每页条数，默认 20 */
  pageSize?: number
  /** 可选的每页条数，默认 [10, 20, 50, 100] */
  pageSizes?: number[]
}

export interface UseTablePaginationReturn<T> {
  currentPage: Ref<number>
  pageSize: Ref<number>
  pageSizes: number[]
  /** 当前页数据（前端切片） */
  pagedData: Ref<T[]>
  /** 总数（取传入数据长度） */
  total: Ref<number>
  /** 当前页起始序号（1-based，用于展示 "No." 列） */
  startIndex: Ref<number>
  /** 当前页结束序号 */
  endIndex: Ref<number>
  /** 每页条数变化 */
  handleSizeChange: (size: number) => void
  /** 页码变化 */
  handleCurrentChange: (page: number) => void
  /** 回到第一页 */
  resetPage: () => void
}

/**
 * 前端分页。适合数据已全量加载到本地的表格（如 BrowseGenomeView、TFView）。
 * @param source 全量数据的 ref 或 computed
 */
export function useTablePagination<T>(
  source: Ref<T[]> | (() => T[]),
  options: UseTablePaginationOptions = {},
): UseTablePaginationReturn<T> {
  const { pageSize: initialPageSize = 20, pageSizes = [10, 20, 50, 100] } = options

  const currentPage = ref(1)
  const pageSize = ref(initialPageSize)

  const rows = computed<T[]>(() => (typeof source === 'function' ? source() : source.value))

  const total = computed(() => rows.value.length)

  /** 数据变少时避免停在空页 */
  watch(total, (t) => {
    const maxPage = Math.max(1, Math.ceil(t / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
    }
  })

  const startIndex = computed(() => {
    if (total.value === 0) return 0
    return (currentPage.value - 1) * pageSize.value + 1
  })

  const endIndex = computed(() => Math.min(currentPage.value * pageSize.value, total.value))

  const pagedData = computed<T[]>(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return rows.value.slice(start, start + pageSize.value)
  })

  function handleSizeChange(size: number): void {
    pageSize.value = size
    currentPage.value = 1
  }

  function handleCurrentChange(page: number): void {
    currentPage.value = page
  }

  function resetPage(): void {
    currentPage.value = 1
  }

  return {
    currentPage,
    pageSize,
    pageSizes,
    pagedData,
    total,
    startIndex,
    endIndex,
    handleSizeChange,
    handleCurrentChange,
    resetPage,
  }
}
