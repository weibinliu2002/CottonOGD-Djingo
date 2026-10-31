<script setup lang="ts">
/**
 * 表格工具栏（阶段 3.2）
 *
 * 对标 SoyOmics 结果表格上方的一体化工具条：关键词筛选 + 结果计数 + 导出。
 * 本项目 9 个结果页的筛选/导出此前各自为政（或完全没有），
 * 这里抽成统一组件，保证外观与交互一致。
 *
 * 用法（与 useEnhancedTable 组合）：
 *   <TableToolbar
 *     v-model="table.keyword"
 *     :total="table.total"
 *     :columns="exportColumns"
 *     :rows="table.sortedRows"
 *     filename="go_annotation.csv"
 *   />
 *
 * 注意：导出的 rows 应传「筛选+排序后的全量数据」而非当前页，
 * 这样用户导出的是整份结果，而不是眼睛看到的那一页。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import { exportCsv, type ExportColumn } from '@/utils/exportTable'

type Row = Record<string, unknown>

const props = withDefaults(
  defineProps<{
    /** v-model：关键词 */
    modelValue?: string
    /** 当前筛选后总条数，用于展示 "Total N records" */
    total?: number
    /** 导出列定义；为空则隐藏导出按钮 */
    columns?: ExportColumn<Row>[]
    /** 导出数据源（建议传筛选+排序后的全量数据） */
    rows?: Row[]
    /** 导出文件名，需带 .csv；不传则自动按日期生成 */
    filename?: string
    /** 占位文案覆盖 */
    placeholder?: string
  }>(),
  {
    modelValue: '',
    total: 0,
    columns: () => [],
    rows: () => [],
    filename: '',
    placeholder: '',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const { t } = useI18n()

/** 是否可导出：同时具备列定义与数据 */
const exportable = computed(() => props.columns.length > 0 && props.rows.length > 0)

/** 关键词双向绑定 */
const keyword = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

/** 导出为 CSV（含筛选与排序结果） */
function onExport(): void {
  if (!props.columns.length) return
  if (!props.rows.length) {
    ElMessage.warning(t('table_export_empty'))
    return
  }
  exportCsv(props.rows, props.columns, props.filename || undefined)
  ElMessage.success(t('table_export_success'))
}
</script>

<template>
  <div class="table-toolbar">
    <el-input
      v-model="keyword"
      class="table-toolbar__search"
      :placeholder="placeholder || t('table_keyword_placeholder')"
      clearable
      size="small"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <span class="table-toolbar__count">
      {{ t('total') }} {{ total }} {{ t('records') }}
    </span>

    <el-button
      v-if="columns.length"
      type="primary"
      size="small"
      :disabled="!exportable"
      @click="onExport"
    >
      <el-icon><Download /></el-icon>
      {{ t('export') }}
    </el-button>
  </div>
</template>

<style scoped>
.table-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-toolbar__search {
  width: 220px;
}

.table-toolbar__count {
  font-size: 13px;
  color: #6c757d;
  margin-right: auto;
}
</style>
