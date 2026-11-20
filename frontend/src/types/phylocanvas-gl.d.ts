// @phylocanvas/phylocanvas.gl 为 WebGL（deck.gl）进化树库，官方包不带类型声明。
// 这里按项目实际用到的 API 面声明最小类型；未覆盖的选项通过索引签名兜底。
declare module '@phylocanvas/phylocanvas.gl' {
  /** 树节点（getGraphAfterLayout 返回的图结构） */
  export interface PhylocanvasNode {
    id: string
    label?: string
    /** 内部节点的原始标签（newick 里的支持度/bootstrap 值） */
    name?: string
    isLeaf?: boolean
    children?: PhylocanvasNode[]
    branchLength?: number
    distanceFromRoot?: number
    totalLeaves?: number
    totalNodes?: number
    isCollapsed?: boolean
    /** 布局后的世界坐标（getGraphAfterLayout 返回时有效） */
    x?: number
    y?: number
    /** 父节点被折叠时该节点不可见 */
    isHidden?: boolean
    parent?: PhylocanvasNode
  }

  /** 布局后的图：root 为根节点，ids 为 id -> 节点 的映射 */
  export interface PhylocanvasGraph {
    root: PhylocanvasNode
    ids: Record<string, PhylocanvasNode>
  }

  export interface PhylocanvasNodeStyle {
    shape?: string
    fillColour?: string | number[]
    strokeColour?: string | number[]
    label?: string
  }

  export interface PhylocanvasProps {
    /** Newick 字符串（或 {type:'newick', data} 等解析后的源） */
    source?: string | { type: string; data: unknown; original?: unknown }
    /** 布局类型，取值见 TreeTypes */
    type?: string
    /** 画布尺寸，缺省取容器的 getBoundingClientRect */
    size?: { width: number; height: number }
    showLabels?: boolean
    showLeafLabels?: boolean
    showInternalLabels?: boolean
    showBranchLengths?: boolean
    showShapes?: boolean
    showEdges?: boolean
    /** 交互开关：true 全开，或按 pan/zoom/tooltip/highlight 分别开启 */
    interactive?: boolean | { pan?: boolean; zoom?: boolean; tooltip?: boolean; highlight?: boolean }
    alignLabels?: boolean
    fontSize?: number
    fontFamily?: string
    fontColour?: string | number[]
    fillColour?: string | number[]
    strokeColour?: string | number[]
    highlightColour?: string | number[]
    nodeShape?: string
    nodeSize?: number
    padding?: number
    centre?: [number, number]
    zoom?: number
    /** 按节点 id 覆盖样式 */
    styles?: Record<string, PhylocanvasNodeStyle>
    selectedIds?: string[]
    collapsedIds?: string[]
    rotatedIds?: string[]
    pinnedIds?: string[]
    [key: string]: unknown
  }

  export class PhylocanvasGL {
    constructor(
      el: HTMLElement | string,
      props?: PhylocanvasProps,
      plugins?: unknown[]
    )
    setSource(source: string | { type: string; data: unknown; original?: unknown }, original?: string): void
    setProps(props: Partial<PhylocanvasProps>): void
    setTreeType(type: string): void
    getTreeType(): string
    getZoom(): number
    setZoom(zoom: number, centre?: unknown): void
    fitInCanvas(): void
    getGraphAfterLayout(): PhylocanvasGraph
    getGraphBeforeLayout(): PhylocanvasGraph
    /** 折叠/展开内部节点（切换 collapsedIds） */
    collapseNode(id: string): void
    /** 画布坐标（CSS 像素，相对画布左上角）拾取节点 */
    pickNodeAtCanvasPoint(x: number, y: number): PhylocanvasNode | null
    /** 世界坐标 -> 画布坐标（CSS 像素） */
    projectPoint(point: [number, number], scale?: number): [number, number]
    /** 按子树节点数排序（深支靠下 / 靠上），内部通过重设 newick 实现 */
    ascendingNodeOrder(): void
    descendingNodeOrder(): void
    /** 枝长方向 / 叶子行距方向的独立缩放（zoom 单位，scale = 2^zoom） */
    setBranchZoom(zoom: number, screenPoint?: unknown): void
    setStepZoom(zoom: number, screenPoint?: unknown): void
    getBranchZoom(): number
    getStepZoom(): number
    /** 重新渲染（平移/缩放/属性变更后由库内部调用） */
    render(): void
    setTooltip(text: string): void
    exportNewick(): string
    exportSVG(includeBackground?: boolean): Blob | string
    /** 返回 PNG dataURL */
    exportPNG(): string
    resize(width: number, height: number): void
    destroy(): void
  }

  export const TreeTypes: {
    Circular: string
    Diagonal: string
    Hierarchical: string
    Radial: string
    Rectangular: string
  }

  export const plugins: Record<string, unknown>
  export const Utils: Record<string, unknown>
  export default PhylocanvasGL
}

// 包内自带的独立打包版本（内联 deck.gl），主入口与项目的 deck.gl 版本冲突时使用
declare module '@phylocanvas/phylocanvas.gl/dist/bundle.min.js' {
  export {
    PhylocanvasGL,
    PhylocanvasGL as default,
    TreeTypes,
    plugins,
    Utils
  } from '@phylocanvas/phylocanvas.gl'
  export type {
    PhylocanvasNode,
    PhylocanvasGraph,
    PhylocanvasProps,
    PhylocanvasNodeStyle
  } from '@phylocanvas/phylocanvas.gl'
}
