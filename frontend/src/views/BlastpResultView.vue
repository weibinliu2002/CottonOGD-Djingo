<template>
  <div class="container mt-4">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="18">
        <h2>BLASTP Results</h2>
      </el-col>
      <el-col :span="6" class="text-right">
        <el-tag type="info" v-if="executionTime">Executed in {{ executionTime }} seconds</el-tag>
      </el-col>
    </el-row>
    
    <!-- 查询序列显示 -->
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>Query Sequence</span>
        </div>
      </template>
      <div class="sequence-box">
        <pre class="mb-0">{{ truncateSequence(querySequence, 200) }}</pre>
        <small class="text-muted" v-if="querySequence.length > 200">(truncated - full sequence used for search)</small>
      </div>
    </el-card>
    
    <!-- 和弦图 -->
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>Chord Diagram</span>
        </div>
      </template>
      <div v-loading="!chordData" element-loading-text="Loading..." class="chord-chart-container">
        <div id="chord-chart" v-if="chordData"></div>
      </div>
    </el-card>
    
    <!-- 每页显示控制 -->
    <el-form @submit.prevent="handlePerPageChange" class="mb-3">
      <el-row :gutter="20" align="middle">
        <el-col :span="4">
          <el-form-item label="每页显示:" label-width="80px">
            <el-select v-model.number="perPage" class="w-32" @change="handlePerPageChange">
              <el-option value="5" label="5"></el-option>
              <el-option value="10" label="10"></el-option>
              <el-option value="25" label="25"></el-option>
              <el-option value="50" label="50"></el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <span class="text-gray-500">条记录</span>
        </el-col>
      </el-row>
    </el-form>
    
    <div v-loading="loading" element-loading-text="Loading results...">
      <div v-if="results.length > 0">
        <!-- BLASTP结果表格 -->
        <el-card class="mb-4">
          <template #header>
            <div class="d-flex justify-content-between align-items-center">
              <span>BLASTP Hits (E-value ≤ {{ eValue }})</span>
              <el-tag type="primary">{{ total }} results</el-tag>
            </div>
          </template>
          <el-table :data="results" style="width: 100%">
            <el-table-column prop="subject" label="Protein ID" width="200">
              <template #default="scope">
                <code>{{ truncateText(scope.row.subject, 15) }}</code>
              </template>
            </el-table-column>
            <el-table-column label="E-value" align="right">
              <template #default="scope">
                {{ formatEvalue(scope.row.evalue) }}
              </template>
            </el-table-column>
            <el-table-column label="Bit Score" align="right">
              <template #default="scope">
                {{ scope.row.bit_score.toFixed(0) }}
              </template>
            </el-table-column>
            <el-table-column label="Identity (%)" align="right">
              <template #default="scope">
                {{ scope.row.identity.toFixed(2) }}%
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 本地数据库匹配结果 -->
        <el-card class="mb-4" v-if="localMatches.length > 0">
          <template #header>
            <div class="card-header">
              <span>Local Database Matches</span>
            </div>
          </template>
          <el-table :data="localMatches" style="width: 100%">
            <el-table-column prop="protein_id" label="Protein ID" width="180">
              <template #default="scope">
                <code>{{ scope.row.protein_id }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="gene_id" label="Gene ID" width="150"></el-table-column>
            <el-table-column prop="description" label="Description">
              <template #default="scope">
                {{ truncateText(scope.row.description, 50) }}
              </template>
            </el-table-column>
            <el-table-column prop="file_source" label="Source" width="180">
              <template #default="scope">
                {{ truncateText(scope.row.file_source, 20) }}
              </template>
            </el-table-column>
            <el-table-column label="Actions" width="180" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" circle>
                  <el-icon><View /></el-icon>
                </el-button>
                <el-button type="success" size="small" circle>
                  <el-icon><Download /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 分页控制 -->
        <el-pagination
          v-if="total > perPage"
          v-model:current-page="currentPage"
          v-model:page-size="perPage"
          :page-sizes="[5, 10, 25, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handlePerPageChange"
          @current-change="changePage"
          class="mt-4"
        />
      </div>
      
      <el-alert
        v-else
        type="info"
        title="未找到匹配结果"
        show-icon
        class="mb-4"
      />
    </div>
    
    <div class="mt-3">
      <router-link to="/tools/blastp">
        <el-button type="default">返回搜索</el-button>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as d3 from 'd3'
import { View, Download } from '@element-plus/icons-vue'

const route = useRoute()

// 页面数据
const perPage = ref(10)
const querySequence = ref('')
const dbChoice = ref('')
const eValue = ref(0.01)
const results = ref<any[]>([])
const allResults = ref<any[]>([])
const localMatches = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)
const executionTime = ref(0)
const chordData = ref<any>(null)
const lineChartData = ref<any[]>([])

// 总页数
const totalPages = computed(() => Math.ceil(total.value / perPage.value))

// 格式化E-value
const formatEvalue = (evalue: number) => {
  if (evalue < 0.001) {
    return evalue.toExponential(2)
  }
  return evalue.toFixed(4)
}

// 截断文本过滤器
  const truncateText = (text: string | undefined, maxLength: number): string => {
    if (!text) return ''
    if (typeof text !== 'string') return String(text)
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  }
  
  // 截断序列过滤器
  const truncateSequence = (sequence: string | undefined, maxLength: number): string => {
    if (!sequence) return ''
    if (typeof sequence !== 'string') return String(sequence)
    return sequence.length > maxLength ? sequence.substring(0, maxLength) + '...' : sequence
  }

// 处理每页显示条数变更
const handlePerPageChange = () => {
  currentPage.value = 1
  paginateResults()
}

// 切换页面
const changePage = (page: number) => {
  currentPage.value = page
  paginateResults()
}

// 分页处理结果
const paginateResults = () => {
  const startIndex = (currentPage.value - 1) * perPage.value
  const endIndex = startIndex + perPage.value
  results.value = allResults.value.slice(startIndex, endIndex)
}

// 加载结果数据
const loadResults = async () => {
  loading.value = true
  
  try {
    // 从路由查询参数中获取结果数据
    if (route.query.results) {
      const decodedResults = JSON.parse(decodeURIComponent(route.query.results as string))
      console.log('Received BLASTP results:', decodedResults)
      
      // 处理API返回的结果格式
      if (decodedResults.hits) {
        // 将API返回的hits数组转换为组件需要的格式
        const formattedResults = decodedResults.hits.map((hit: any, index: number) => ({
          query: 'Query_Protein',
          subject: hit.protein_id,
          identity: hit.identity,
          alignment_length: hit.length,
          mismatches: 0, // API未返回该字段，默认为0
          gaps: 0, // API未返回该字段，默认为0
          query_start: hit.qStart,
          query_end: hit.qEnd,
          subject_start: 0, // API未返回该字段，默认为0
          subject_end: hit.length, // 使用蛋白质全长
          evalue: hit.evalue,
          bit_score: hit.score
        }))
        
        // 去重处理：根据subject ID去重
        const uniqueResults = [...new Map(formattedResults.map((item: any) => [item.subject, item])).values()]
        
        // 按bit_score降序排序
        uniqueResults.sort((a: any, b: any) => b.bit_score - a.bit_score)
        
        allResults.value = uniqueResults
        total.value = uniqueResults.length
        
        // 设置查询序列
        querySequence.value = decodedResults.query_sequence || ''
        
        // 设置执行时间
        executionTime.value = decodedResults.execution_time || 0
        
        // 设置E-value阈值
        eValue.value = decodedResults.evalue || 0.01
        
        // 设置本地匹配结果
        localMatches.value = decodedResults.local_matches || []
        
        // 设置线图数据
        lineChartData.value = uniqueResults.map((result: any) => ({
          identity: result.identity,
          evalue: result.evalue,
          bitScore: result.bit_score,
          subject: result.subject
        }))
        
        // 分页处理
        paginateResults()
        
        // 准备和弦图数据
        prepareChordData(decodedResults)
      }
    } else {
      console.error('No results found in route query')
      results.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('加载结果失败:', error)
    results.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 准备和弦图数据
const prepareChordData = (decodedResults: any) => {
  if (!decodedResults.hits || decodedResults.hits.length === 0) {
    chordData.value = null
    return
  }
  
  // 构造和弦图需要的数据格式
  const chordDataObj = {
    query: 'Query_Protein',
    queryLength: decodedResults.query_length || 0,
    proteins: [
      { id: 'Query_Protein', length: decodedResults.query_length || 0 },
      ...decodedResults.hits.map((hit: any) => ({ 
        id: hit.protein_id, 
        length: hit.length 
      }))
    ],
    hits: decodedResults.hits.map((hit: any) => ({
      query: hit.protein_id,
      target: 'Query_Protein',
      score: hit.score,
      evalue: hit.evalue,
      identity: hit.identity,
      qStart: hit.qStart,
      qEnd: hit.qEnd
    }))
  }
  
  chordData.value = chordDataObj
}

// 渲染和弦图
const renderChordDiagram = () => {
  if (!chordData.value) return
  
  const data = chordData.value
  
  function createMatrix(data: any) {
    const proteins = [data.query, ...data.proteins.map((p: any) => p.id)]
    const lengths = [data.queryLength, ...data.proteins.map((p: any) => p.length)]
    const totalLength = lengths.reduce((a: number, b: number) => a + b, 0)
    
    const matrix = Array(proteins.length).fill(0)
      .map(() => Array(proteins.length).fill(0))
    
    data.hits.forEach((hit: any) => {
      const i = proteins.indexOf(hit.query)
      const j = proteins.indexOf(hit.target)
      if (i !== -1 && j !== -1 && i < matrix.length && j < matrix.length && matrix[i] && matrix[j]) {
        matrix[i][j] = hit.score
        matrix[j][i] = hit.score
      }
    })
    
    return { matrix, proteins, lengths, totalLength, hits: data.hits }
  }

  const processedData = createMatrix(data)
  const proteinIdentityMap: Record<string, number> = {}
  processedData.proteins.forEach((protein: string) => {
    proteinIdentityMap[protein] = 0
  })
  processedData.hits.forEach((hit: any) => {
    if (hit.query !== data.query) {
      proteinIdentityMap[hit.query] += hit.identity
    }
    if (hit.target !== data.query) {
      proteinIdentityMap[hit.target] += hit.identity
    }
  })

  const proteinCounts: Record<string, number> = {}
  processedData.hits.forEach((hit: any) => {
    if (hit.query !== data.query) {
      proteinCounts[hit.query] = (proteinCounts[hit.query] || 0) + 1
    }
    if (hit.target !== data.query) {
      proteinCounts[hit.target] = (proteinCounts[hit.target] || 0) + 1
    }
  })
  
  Object.keys(proteinIdentityMap).forEach((protein: string) => {
    if (protein !== data.query) {
      const count = proteinCounts[protein] || 1
      if (count && proteinIdentityMap[protein] !== undefined) {
        proteinIdentityMap[protein] = proteinIdentityMap[protein] / count
      }
    }
  })
  
  const queryProtein = data.query
  const otherProteins = processedData.proteins.filter((p: string) => p !== queryProtein)
  const sortedOtherProteins = [...otherProteins].sort((a: string, b: string) => {
    const identityA = proteinIdentityMap[a] || 0
    const identityB = proteinIdentityMap[b] || 0
    return identityB - identityA
  })
  const newProteinOrder = [queryProtein, ...sortedOtherProteins]
  const newOrder = newProteinOrder.map((protein: string) => processedData.proteins.indexOf(protein))
  
  const sortedMatrix = newOrder.map((i: number) => 
    newOrder.map((j: number) => {
      if (processedData.matrix && i >= 0 && i < processedData.matrix.length && processedData.matrix[i] && j >= 0 && j < processedData.matrix[i].length) {
        return processedData.matrix[i][j]
      }
      return 0
    })
  )
  
  const sortedLengths = newOrder.map((i: number) => processedData.lengths[i])
  const sortedProteinsList = newOrder.map((i: number) => processedData.proteins[i])
  
  processedData.matrix = sortedMatrix
  processedData.lengths = sortedLengths
  processedData.proteins = sortedProteinsList
  
  // 原始模板中没有filteredChords，直接使用chords数据

  const container = document.getElementById('chord-chart')
  if (!container) return
  
  // 清空容器
  container.innerHTML = ''
  
  const width = container.clientWidth
  const height = 800
  const outerRadius = Math.min(width, height) * 0.5 - 40
  const innerRadius = outerRadius - 30

  const svg = d3.select('#chord-chart')
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', `translate(${width/2},${height/2})`)

  const chord = d3.chord()
    .padAngle(0.1)
    .sortSubgroups(d3.descending)

  const chords = chord(processedData.matrix)
  const cumulativeAngles = [0]
  let cumulativeSum = 0
  
  cumulativeSum += processedData.lengths[0]
  cumulativeAngles.push(cumulativeSum / processedData.totalLength * 2 * Math.PI)

  for (let i = 1; i < processedData.lengths.length; i++) {
    cumulativeSum += processedData.lengths[i]
    cumulativeAngles.push(cumulativeSum / processedData.totalLength * 2 * Math.PI)
  }

  const arc = d3.arc()
    .innerRadius(innerRadius)
    .outerRadius(outerRadius)
    .startAngle((d: any) => (cumulativeAngles[d.index] || 0) + 0.02)
    .endAngle((d: any) => (cumulativeAngles[d.index + 1] || 0) - 0.02)

  // 创建颜色比例尺
  const colorScale = d3.scaleOrdinal<string, string>()
    .domain(processedData.proteins)
    .range(d3.schemeCategory10.concat(d3.schemeTableau10))

  const group = svg.append('g')
    .selectAll('g')
    .data(chords.groups)
    .enter().append('g')

  group.append('path')
    .attr('class', 'chord-group')
    .style('fill', (d: any) => {
      // 使用颜色比例尺为每个组分配唯一颜色
      return colorScale(processedData.proteins[d.index])
    })
    .style('stroke', '#000')
    .style('stroke-width', '0.5px')
    .attr('d', (d: any) => arc(d as any))
    .append('title')
    .text((d: any) => {
      const protein = processedData.proteins[d.index]
      const length = processedData.lengths[d.index]
      const identity = proteinIdentityMap[protein] || 0
      return `${protein} (Length: ${length}, Avg Identity: ${identity.toFixed(2)}%)`
    })

  group.append('text')
          .each((d: any) => {
            const startAngle = cumulativeAngles[d.index] || 0
            const endAngle = cumulativeAngles[d.index + 1] || 0
            d.angle = (startAngle + endAngle) / 2
          })
          .attr('class', 'protein-label')
          .attr('dy', '.35em')
          .attr('transform', (d: any) => `
            rotate(${d.angle * 180 / Math.PI - 90})
            translate(${innerRadius - 5})
            ${d.angle > Math.PI ? 'rotate(180)' : ''}
          `)
          .style('text-anchor', (d: any) => d.angle > Math.PI ? 'end' : null)
          .text((d: any) => {
            const maxLength = 4
            const proteinName = processedData.proteins[d.index]
            return proteinName.length > maxLength ? 
              proteinName.substring(0, maxLength) + '...' : 
              proteinName
          })

  const ribbon = d3.ribbon()
    .radius(innerRadius)
  const tooltip = d3.select('body')
    .append('div')
    .attr('class', 'tooltip')
    .style('opacity', 0)
    .style('position', 'absolute')
    .style('background', 'rgba(0, 0, 0, 0.8)')
    .style('color', 'white')
    .style('padding', '8px')
    .style('border-radius', '4px')
    .style('font-size', '12px')
    .style('pointer-events', 'none')

  // 绘制和弦图的线条（ribbons）
  svg.append('g')
    .selectAll('path')
    .data(chords)
    .enter()
    .append('path')
    .attr('class', 'chord-ribbon')
    .style('fill', (d: any) => {
      // 根据源蛋白质的颜色来填充线条
      return colorScale(processedData.proteins[d.source.index])
    })
    .style('stroke', (d: any) => {
      // 根据源蛋白质的颜色来设置线条颜色
      return colorScale(processedData.proteins[d.source.index])
    })
    .attr('d', ribbon as any)
    .style('opacity', 0.8)
    .on('mouseover', (event: MouseEvent) => {
      d3.selectAll('.chord-ribbon')
        .style('opacity', 0.1)
      const currentTarget = event.currentTarget as HTMLElement
      if (currentTarget) {
        d3.select(currentTarget)
          .style('opacity', 1)
          .style('stroke', '#000')
          .style('stroke-width', '1px')
      }
      
      // 获取当前chord数据，使用类型断言处理__data__属性
      const target = event.currentTarget as any
      const d = target?.__data__
      if (d) {
        const sourceProtein = processedData.proteins[d.source.index]
        const targetProtein = processedData.proteins[d.target.index]
        
        // 查找对应的hit数据
        const hit = processedData.hits.find((h: any) => 
          (h.query === sourceProtein && h.target === targetProtein) ||
          (h.query === targetProtein && h.target === sourceProtein)
        )
        
        tooltip.transition()
          .duration(200)
          .style('opacity', 0.9)
          
        tooltip.html(`
          <strong>Query Protein → ${targetProtein}</strong><br>
          ${hit ? `E-value: ${hit.evalue}<br>Identity: ${hit.identity}%<br>Alignment region: ${hit.qStart}-${hit.qEnd}` : ''}
        `)
          .style('left', (event.pageX + 15) + 'px')
          .style('top', (event.pageY - 28) + 'px')
      }
    })
    .on('mouseout', () => {
      d3.selectAll('.chord-ribbon')
        .style('opacity', 0.8)
        .style('stroke', 'none')
      tooltip.style('opacity', 0)
    })
    .on('mousemove', (event: MouseEvent) => {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
}

// 渲染线图
const renderLineChart = () => {
  if (lineChartData.value.length === 0) return
  
  const container = document.getElementById('line-chart')
  if (!container) return
  
  const width = container.clientWidth
  const height = 400
  const margin = { top: 20, right: 30, bottom: 40, left: 60 }
  
  // 清空容器
  container.innerHTML = ''
  
  // 创建SVG
  const svg = d3.select('#line-chart')
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)
  
  const chartWidth = width - margin.left - margin.right
  const chartHeight = height - margin.top - margin.bottom
  
  // 数据转换：将E-value取对数以便更好地可视化
  const data = lineChartData.value.map(d => ({
    ...d,
    logEvalue: -Math.log10(d.evalue + 1e-100) // 添加一个很小的值以避免log(0)
  }))
  
  // X轴：Identity (%)
  const xScale = d3.scaleLinear()
    .domain([0, 100])
    .range([0, chartWidth])
  
  // Y轴：-log10(E-value)
  const yScale = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.logEvalue) || 0])
    .range([chartHeight, 0])
  
  // 创建X轴
  svg.append('g')
    .attr('transform', `translate(0,${chartHeight})`)
    .call(d3.axisBottom(xScale))
    .append('text')
    .attr('x', chartWidth / 2)
    .attr('y', 30)
    .style('text-anchor', 'middle')
    .style('font-size', '12px')
    .text('Identity (%)')
  
  // 创建Y轴
  svg.append('g')
    .call(d3.axisLeft(yScale))
    .append('text')
    .attr('transform', 'rotate(-90)')
    .attr('x', -chartHeight / 2)
    .attr('y', -40)
    .style('text-anchor', 'middle')
    .style('font-size', '12px')
    .text('-log10(E-value)')
  
  // 创建散点
  svg.selectAll('.dot')
    .data(data)
    .enter()
    .append('circle')
    .attr('class', 'dot')
    .attr('cx', d => xScale(d.identity))
    .attr('cy', d => yScale(d.logEvalue))
    .attr('r', 4)
    .style('fill', '#49B7CF')
    .style('opacity', 0.7)
    .style('stroke', '#000')
    .style('stroke-width', '1px')
    .on('mouseover', function(event, d) {
      d3.select(this)
        .style('opacity', 1)
        .style('stroke', '#000')
        .style('stroke-width', '2px')
      
      // 创建tooltip
      const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0)
        .style('position', 'absolute')
        .style('background', 'rgba(0, 0, 0, 0.8)')
        .style('color', 'white')
        .style('padding', '8px')
        .style('border-radius', '4px')
        .style('font-size', '12px')
        .style('pointer-events', 'none')
        .style('z-index', '1000')
      
      tooltip.transition()
        .duration(200)
        .style('opacity', 0.9)
      
      tooltip.html(`
        <strong>${d.subject}</strong><br>
        Identity: ${d.identity.toFixed(2)}%<br>
        E-value: ${d.evalue < 0.001 ? d.evalue.toExponential(2) : d.evalue.toFixed(4)}<br>
        Bit Score: ${d.bitScore.toFixed(0)}
      `)
      .style('left', (event.pageX + 15) + 'px')
      .style('top', (event.pageY - 28) + 'px')
      
      // 存储tooltip引用
      d3.select(this).datum({ tooltip })
    })
    .on('mouseout', function() {
        d3.select(this)
          .style('opacity', 0.7)
          .style('stroke', '#000')
          .style('stroke-width', '1px')
        
        // 移除tooltip
        const data = d3.select(this).datum() as { tooltip?: any }
        if (data.tooltip && typeof data.tooltip.remove === 'function') {
          data.tooltip.remove()
        }
        d3.select(this).datum(null)
      })
  
  // 添加网格线
  svg.append('g')
    .attr('class', 'grid')
    .attr('transform', `translate(0,${chartHeight})`)
    .call(d3.axisBottom(xScale)
      .ticks(10)
      .tickSize(-chartHeight)
      .tickFormat(() => '')
    )
  
  svg.append('g')
    .attr('class', 'grid')
    .call(d3.axisLeft(yScale)
      .ticks(10)
      .tickSize(-chartWidth)
      .tickFormat(() => '')
    )
}

// 组件挂载时加载数据
onMounted(() => {
  loadResults()
})

// 监听和弦图数据变化，渲染图表
watch(chordData, (newVal) => {
  if (newVal) {
    // 延迟渲染，确保DOM已经更新
    setTimeout(() => {
      renderChordDiagram()
    }, 100)
  }
})

// 监听线图数据变化，重新渲染
watch(lineChartData, () => {
  renderLineChart()
}, { deep: true })
</script>

<style scoped>
.pagination {
  margin-top: 1rem;
}

.btn-secondary {
  background-color: #6c757d;
  border-color: #6c757d;
}

.btn-secondary:hover {
  background-color: #5a6268;
  border-color: #545b62;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
}

.sequence-box {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #eee;
}

#chord-chart {
  width: 100%;
  height: 800px;
  margin: 0 auto;
}

#chord-chart svg {
  display: block !important;
  overflow: visible !important;
}

.line-chart-container {
  width: 100%;
  height: 400px;
}

.line-chart-container svg {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
}

.grid line {
  stroke: #e0e0e0;
  stroke-opacity: 0.7;
  shape-rendering: crispEdges;
}

.grid path {
  stroke-width: 0;
}

.dot {
  transition: all 0.3s ease;
}

.chord-path {
  opacity: 0.8;
  stroke: #000;
  stroke-width: 0.5px;
  transition: opacity 0.3s;
}

.protein-label {
  font-size: 12px;
  font-weight: bold;
}

.tooltip {
  position: absolute;
  padding: 8px;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  border-radius: 4px;
  pointer-events: none;
  font-size: 12px;
  max-width: 300px;
}
</style>