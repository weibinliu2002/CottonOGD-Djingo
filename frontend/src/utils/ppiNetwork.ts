import type { ElementDefinition } from 'cytoscape'

export interface PpiNetwork {
  elements: ElementDefinition[]
}

type JsonRecord = Record<string, unknown>

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

  const content =
    Array.isArray(payload.elements) || isRecord(payload.elements) ? payload.elements : payload
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
