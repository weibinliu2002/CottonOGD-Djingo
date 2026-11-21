/**
 * ECharts 按需引入：只注册项目实际用到的渲染器与图表组件。
 * 相比 `import * as echarts from 'echarts'` 全量引入，可显著减小打包体积。
 * 用法：import echarts from '@/utils/echarts' （默认导出，API 与全量引入一致；
 *       不要写 import * as echarts，那样拿到的是模块命名空间对象，没有 init）
 */
import * as echarts from 'echarts/core'
import { BarChart, HeatmapChart, LineChart, PieChart, SankeyChart, ScatterChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  // 图表
  BarChart,
  LineChart,
  PieChart,
  SankeyChart,
  ScatterChart,
  // 统计页：Ortholog 物种两两矩阵热图
  HeatmapChart,
  // 组件
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  VisualMapComponent,
  // 渲染器
  CanvasRenderer,
])

export default echarts
export { echarts }
