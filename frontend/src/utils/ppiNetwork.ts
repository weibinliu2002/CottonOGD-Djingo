import type { ElementDefinition } from 'cytoscape'
import * as XLSX from '@e965/xlsx'

export interface PpiNetwork {
  elements: ElementDefinition[]
}

type JsonRecord = Record<string, unknown>
export type PpiUploadFormat = 'auto' | 'cytoscape' | 'table'

const EDGE_SOURCE_HEADERS = ['source', 'from', 'gene_a', 'gene1', 'node1', 'protein1', 'gene_a_id', 'shared_source']
const EDGE_TARGET_HEADERS = ['target', 'to', 'gene_b', 'gene2', 'node2', 'protein2', 'gene_b_id', 'shared_target']
const EDGE_ID_HEADERS = ['id', 'edge_id', 'interaction_id', 'shared_name']
const NODE_ID_HEADERS = ['id', 'node', 'gene', 'gene_id', 'protein', 'protein_id', 'shared_name']
const NODE_LABEL_HEADERS = ['label', 'name', 'gene_name', 'protein_name', 'description']
const EDGE_SCORE_HEADERS = ['score', 'weight', 'combined_score', 'confidence']

type TableRecord = Record<string, unknown>

function normalizedHeader(value: unknown): string {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_')
}

function findHeader(headers: string[], candidates: string[]): number {
  return headers.findIndex((header) => candidates.includes(header))
}

function makeTableNetwork(rows: TableRecord[], headers: string[]): PpiNetwork {
  const sourceIndex = findHeader(headers, EDGE_SOURCE_HEADERS)
  const targetIndex = findHeader(headers, EDGE_TARGET_HEADERS)
  const idIndex = findHeader(headers, NODE_ID_HEADERS)
  if (sourceIndex < 0 && targetIndex < 0 && idIndex < 0) {
    throw new Error(
      'Could not recognize columns. Include source/target columns for an edge list, or an id/gene_id column for a node list.',
    )
  }

  const nodes = new Map<string, ElementDefinition>()
  const edges: ElementDefinition[] = []
  const labelIndex = findHeader(headers, NODE_LABEL_HEADERS)
  const edgeIdIndex = findHeader(headers, EDGE_ID_HEADERS)
  const scoreIndex = findHeader(headers, EDGE_SCORE_HEADERS)
  const addNode = (rawId: unknown, rawLabel?: unknown): string => {
    const id = String(rawId ?? '').trim()
    if (!id) throw new Error('A row is missing a node ID.')
    if (!nodes.has(id)) {
      const label = String(rawLabel ?? '').trim()
      nodes.set(id, { data: { id, label: label || id } })
    }
    return id
  }

  if (sourceIndex >= 0 || targetIndex >= 0) {
    if (sourceIndex < 0 || targetIndex < 0) {
      throw new Error('An edge list must include both source and target columns.')
    }
    rows.forEach((row, index) => {
      const values = headers.map((header) => row[header])
      const source = addNode(values[sourceIndex] ?? '')
      const target = addNode(values[targetIndex] ?? '')
      const providedId = edgeIdIndex >= 0 ? String(values[edgeIdIndex] ?? '').trim() : ''
      const score = scoreIndex >= 0 ? Number(values[scoreIndex]) : undefined
      const data: Record<string, unknown> = {
        id: providedId || `edge-${index + 1}`,
        source,
        target,
      }
      if (score !== undefined && Number.isFinite(score)) data.score = score
      edges.push({ data } as ElementDefinition)
    })
  } else {
    rows.forEach((row) => {
      const values = headers.map((header) => row[header])
      addNode(values[idIndex] ?? '', labelIndex >= 0 ? values[labelIndex] : undefined)
    })
  }
  return parsePpiNetwork({ elements: [...nodes.values(), ...edges] })
}

function parseDelimitedText(text: string): PpiNetwork {
  const firstLine = text.split(/\r?\n/, 1)[0] || ''
  const delimiter = firstLine.includes('\t')
    ? '\t'
    : firstLine.includes(',')
      ? ','
      : firstLine.includes(';')
        ? ';'
        : 'whitespace'
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  for (let index = 0; index < text.length; index += 1) {
    const character = text.charAt(index)
    if (character === '"') {
      if (quoted && text[index + 1] === '"') {
        cell += '"'
        index += 1
      } else {
        quoted = !quoted
      }
    } else if (!quoted && (character === '\n' || character === '\r')) {
      if (character === '\r' && text[index + 1] === '\n') index += 1
      row.push(cell.trim())
      if (row.some(Boolean)) rows.push(row)
      row = []
      cell = ''
    } else if (!quoted && (character === delimiter || (delimiter === 'whitespace' && /\s/.test(character)))) {
      if (cell.trim() || delimiter !== 'whitespace') row.push(cell.trim())
      cell = ''
    } else {
      cell += character
    }
  }
  if (quoted) throw new Error('The delimited file contains an unterminated quoted field.')
  row.push(cell.trim())
  if (row.some(Boolean)) rows.push(row)
  if (rows.length === 0) throw new Error('The table is empty.')

  const firstRow = rows[0]
  if (!firstRow) throw new Error('The table is empty.')
  const headers = firstRow.map(normalizedHeader)
  const hasHeader =
    findHeader(headers, EDGE_SOURCE_HEADERS) >= 0 ||
    findHeader(headers, EDGE_TARGET_HEADERS) >= 0 ||
    findHeader(headers, NODE_ID_HEADERS) >= 0
  const dataRows = hasHeader ? rows.slice(1) : rows
  if (dataRows.length === 0) throw new Error('The table must contain at least one data row.')
  const resolvedHeaders = hasHeader
    ? headers
    : firstRow.length === 1
      ? ['id']
      : firstRow.length === 2
        ? ['source', 'target']
        : firstRow.length === 3
          ? ['source', 'interaction', 'target']
          : []
  if (!resolvedHeaders.length) {
    throw new Error(
      'Could not recognize a header. Headerless text files must contain one node ID or two interaction IDs per row.',
    )
  }
  if (resolvedHeaders.some((header) => !header)) throw new Error('Every table column must have a header.')
  return makeTableNetwork(
    dataRows.map((cells) => Object.fromEntries(resolvedHeaders.map((header, index) => [header, cells[index] ?? '']))),
    resolvedHeaders,
  )
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function normalizeElement(value: unknown, index: number): ElementDefinition {
  if (!isRecord(value) || !isRecord(value.data)) {
    throw new Error(`Network element ${index + 1} must contain a data object.`)
  }

  const data = { ...value.data }
  const id = data.id
  if ((typeof id !== 'string' && typeof id !== 'number') || String(id).trim() === '') {
    throw new Error(`Network element ${index + 1} is missing data.id.`)
  }
  data.id = String(id)

  const isEdge = 'source' in data || 'target' in data
  if (isEdge) {
    if (
      (typeof data.source !== 'string' && typeof data.source !== 'number') ||
      (typeof data.target !== 'string' && typeof data.target !== 'number')
    ) {
      throw new Error(`Network edge ${String(id)} must contain data.source and data.target.`)
    }
    data.source = String(data.source)
    data.target = String(data.target)
  } else if (data.label === undefined) {
    data.label = String(id)
  }

  return { ...value, data } as ElementDefinition
}

export function parsePpiNetwork(input: unknown): PpiNetwork {
  let payload = input
  if (isRecord(payload) && typeof payload.code === 'number' && 'data' in payload) {
    if (payload.code !== 0) {
      throw new Error(typeof payload.message === 'string' ? payload.message : 'Network request failed.')
    }
    payload = payload.data
  }

  if (!isRecord(payload)) {
    throw new Error('Expected a Cytoscape JSON object.')
  }

  const content = Array.isArray(payload.elements) || isRecord(payload.elements) ? payload.elements : payload
  let rawElements: unknown[]
  if (Array.isArray(content)) {
    rawElements = content
  } else if (isRecord(content) && Array.isArray(content.nodes) && Array.isArray(content.edges)) {
    rawElements = [...content.nodes, ...content.edges]
  } else {
    throw new Error('Expected elements as an array, or an object with nodes and edges arrays.')
  }

  const elements = rawElements.map(normalizeElement)
  const nodes = elements.filter((element) => !('source' in (element.data ?? {})))
  const edges = elements.filter((element) => 'source' in (element.data ?? {}))
  if (nodes.length === 0) {
    throw new Error('The network must contain at least one node.')
  }

  const nodeIds = new Set<string>()
  const elementIds = new Set<string>()
  for (const node of nodes) {
    const id = String(node.data.id)
    if (elementIds.has(id)) throw new Error(`Duplicate node id: ${id}`)
    elementIds.add(id)
    nodeIds.add(id)
  }
  for (const edge of edges) {
    const id = String(edge.data.id)
    if (elementIds.has(id)) throw new Error(`Duplicate element id: ${id}`)
    elementIds.add(id)
    if (!nodeIds.has(String(edge.data.source)) || !nodeIds.has(String(edge.data.target))) {
      throw new Error(`Network edge ${id} references a node that does not exist.`)
    }
  }

  return { elements }
}

function hasNetworkElements(input: unknown): boolean {
  if (!isRecord(input)) return false
  const payload = isRecord(input.data) ? input.data : input
  return (
    (Array.isArray(payload.elements) && payload.elements.length > 0) ||
    (isRecord(payload.elements) && Array.isArray(payload.elements.nodes) && Array.isArray(payload.elements.edges)) ||
    (Array.isArray(payload.nodes) && Array.isArray(payload.edges))
  )
}

export async function parsePpiUpload(file: File, format: PpiUploadFormat = 'auto'): Promise<PpiNetwork> {
  const extension = file.name.split('.').pop()?.toLowerCase() || ''
  const signature = new Uint8Array(await file.slice(0, 4).arrayBuffer())
  const isSpreadsheet =
    ['xls', 'xlsx'].includes(extension) ||
    file.type.includes('spreadsheet') ||
    file.type === 'application/vnd.ms-excel' ||
    (signature[0] === 0x50 && signature[1] === 0x4b) ||
    (signature[0] === 0xd0 && signature[1] === 0xcf && signature[2] === 0x11 && signature[3] === 0xe0)
  const selectedFormat =
    format === 'auto'
      ? isSpreadsheet
        ? 'table'
        : ['json', 'cyjs', 'graphml', 'xml', 'xgmml'].includes(extension)
          ? 'cytoscape'
          : ['csv', 'tsv', 'txt', 'sif'].includes(extension)
            ? 'table'
            : 'auto'
      : format
  if (selectedFormat === 'cytoscape' || selectedFormat === 'auto') {
    const bytes = await file.arrayBuffer()
    const text = new TextDecoder()
      .decode(bytes)
      .replace(/^\uFEFF/, '')
      .trim()
    if (text.startsWith('<')) return parseGraphMl(text)
    try {
      const parsed: unknown = JSON.parse(text)
      if (hasNetworkElements(parsed)) return parsePpiNetwork(parsed)
      if (selectedFormat === 'cytoscape') throw new Error('The JSON file does not contain Cytoscape network elements.')
      return parseDelimitedText(text)
    } catch (error) {
      if (selectedFormat === 'cytoscape') {
        if (error instanceof SyntaxError) {
          throw new Error('This is not valid Cytoscape JSON. For a table or edge list, select the Table format.')
        }
        throw error
      }
      try {
        return parseDelimitedText(text)
      } catch {
        if (extension && !['json', 'cyjs'].includes(extension)) {
          throw new Error(
            'Could not identify this file type. Select Cytoscape JSON or a delimited table and try again.',
          )
        }
        throw error
      }
    }
  }

  if (selectedFormat === 'table') {
    if (isSpreadsheet) {
      const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      const sheet = firstSheetName ? workbook.Sheets[firstSheetName] : undefined
      if (!sheet) throw new Error('The workbook contains no sheets.')
      const rows = XLSX.utils.sheet_to_json<TableRecord>(sheet, { defval: '' })
      const headers = Object.keys(rows[0] || {}).map(normalizedHeader)
      const normalizedRows = rows.map((row) =>
        Object.fromEntries(Object.entries(row).map(([key, value]) => [normalizedHeader(key), value])),
      )
      return makeTableNetwork(normalizedRows, headers)
    }
    return parseDelimitedText(new TextDecoder().decode(await file.arrayBuffer()).replace(/^\uFEFF/, ''))
  }

  throw new Error('Could not identify this file type. Select Cytoscape JSON or a delimited table and try again.')
}

function parseGraphMl(xml: string): PpiNetwork {
  if (typeof DOMParser === 'undefined') {
    throw new Error('GraphML files can only be parsed in a browser.')
  }
  const document = new DOMParser().parseFromString(xml, 'application/xml')
  if (document.querySelector('parsererror')) throw new Error('The GraphML file is invalid XML.')

  const keyNames = new Map(
    Array.from(document.querySelectorAll('key')).map((key) => [
      key.getAttribute('id') || '',
      key.getAttribute('attr.name') || key.getAttribute('id') || '',
    ]),
  )
  const valueFor = (element: Element, preferredNames: string[]): string => {
    for (const data of Array.from(element.querySelectorAll(':scope > data'))) {
      const key = keyNames.get(data.getAttribute('key') || '')?.toLowerCase()
      if (key && preferredNames.includes(key)) return data.textContent?.trim() || ''
    }
    for (const attribute of Array.from(element.querySelectorAll(':scope > att'))) {
      const name = attribute.getAttribute('name')?.toLowerCase()
      if (name && preferredNames.includes(name)) return attribute.getAttribute('value') || ''
    }
    return ''
  }
  const nodes = Array.from(document.querySelectorAll('graph > node')).map((node) => {
    const id = node.getAttribute('id') || ''
    return {
      data: {
        id,
        label: node.getAttribute('label') || valueFor(node, NODE_LABEL_HEADERS) || id,
      },
    }
  })
  const edges = Array.from(document.querySelectorAll('graph > edge')).map((edge, index) => {
    const id = edge.getAttribute('id') || `edge-${index + 1}`
    const data: Record<string, unknown> = {
      id,
      source: edge.getAttribute('source') || '',
      target: edge.getAttribute('target') || '',
    }
    const rawScore = valueFor(edge, EDGE_SCORE_HEADERS)
    if (rawScore) {
      const score = Number(rawScore)
      if (Number.isFinite(score)) data.score = score
    }
    return { data }
  })
  return parsePpiNetwork({ elements: [...nodes, ...edges] })
}
