/**
 * 表格导出工具（阶段 2）
 *
 * 统一 16 处 el-table 的导出能力。此前各页面实现五花八门：
 * 有的用 Blob + createElement('a')，有的手写字符串拼接，有的根本没有导出。
 * 这里统一为 CSV（带 BOM，Excel 直接打开不乱码；含字段转义）。
 */

/** 列定义：key 为行对象字段名，label 为表头 */
export interface ExportColumn<T = Record<string, unknown>> {
  key: string
  label: string
  /** 自定义取值/格式化；不传则取 row[key] */
  formatter?: (row: T) => string | number | null | undefined
}

/** 把单元格值转成安全的 CSV 文本 */
function escapeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  let text = String(value)
  // 防止 CSV 公式注入：以 = + - @ 开头的内容前置单引号
  if (/^[=+\-@]/.test(text)) text = `'${text}`
  if (/[",\r\n]/.test(text)) {
    text = `"${text.replace(/"/g, '""')}"`
  }
  return text
}

/**
 * 生成 CSV 文本。
 * 表头用 label，数据行按 ExportColumn 顺序取值。
 */
export function buildCsv<T extends Record<string, unknown>>(
  rows: T[],
  columns: ExportColumn<T>[],
): string {
  const header = columns.map((c) => escapeCsvCell(c.label)).join(',')
  const body = rows.map((row) =>
    columns
      .map((c) => {
        const raw = c.formatter ? c.formatter(row) : row[c.key]
        return escapeCsvCell(raw)
      })
      .join(','),
  )
  return [header, body].filter(Boolean).join('\r\n')
}

/** 触发浏览器下载 */
export function downloadBlob(content: string, filename: string, mime = 'text/csv;charset=utf-8'): void {
  // BOM：保证 Excel 以 UTF-8 打开
  const blob = new Blob(['﻿', content], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 导出表格为 CSV 并下载。
 * @param filename 建议以 .csv 结尾；不传时自动补时间戳
 */
export function exportCsv<T extends Record<string, unknown>>(
  rows: T[],
  columns: ExportColumn<T>[],
  filename?: string,
): void {
  const csv = buildCsv(rows, columns)
  const name =
    filename ??
    `export_${new Date().toISOString().split('T')[0]}.csv`
  downloadBlob(csv, name)
}

/** 导出纯文本（FASTA / GFF 等） */
export function exportText(content: string, filename: string): void {
  downloadBlob(content, filename, 'text/plain;charset=utf-8')
}

/**
 * 从表格行数组自动推断列（取所有行字段的并集）。
 * 适合快速给"没有显式列定义"的表格加导出。
 */
export function inferColumns<T extends Record<string, unknown>>(
  rows: T[],
  labelMap?: Record<string, string>,
): ExportColumn<T>[] {
  const keys = new Set<string>()
  rows.forEach((r) => Object.keys(r).forEach((k) => keys.add(k)))
  return Array.from(keys).map((k) => ({
    key: k,
    label: labelMap?.[k] ?? k,
    formatter: (row: T) => {
      const v = row[k]
      // 对象/数组序列化，避免出现 [object Object]
      if (v !== null && typeof v === 'object') return JSON.stringify(v)
      return v as string | number | null | undefined
    },
  }))
}
