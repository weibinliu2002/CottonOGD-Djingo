<template>
  <div class="container mt-4">
    <h1>JBrowse 可视化</h1>
    <div class="card">
      <div class="card-body">
        <h2 class="card-title mb-4">选择基因组</h2>
        <table class="table table-bordered table-hover">
          <thead class="thead-light">
            <tr>
              <th>基因组名称</th>
              <th>描述</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="genome in genomes" :key="genome.id">
              <td>{{ genome.name }}</td>
              <td>{{ genome.description }}</td>
              <td>
                <a :href="`/assets/jbrowse/index.html?config=config.json&assembly=${genome.assembly}&tracks=${genome.track}&loc=Ghir_A01:1-1000000`" target="_blank" class="btn btn-primary mr-2">
          新窗口打开
        </a>
                <button @click="openGenome(genome)" class="btn btn-secondary">
                  嵌入查看
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <h2 class="card-title mt-5 mb-4">JBrowse 可视化</h2>
        <div class="embed-container">
          <iframe :key="iframeKey" :src="currentIframeUrl" width="100%" height="600px" frameborder="0"></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'JbrowseView',
  data() {
    return {
      genomes: [
        {
          id: 1,
          name: '陆地棉基因组 (Ghirsutum)',
          description: '陆地棉（Gossypium hirsutum）基因组序列，版本为HAU v1.0',
          assembly: 'Ghirsutum_genome_HAU_v1.0',
          track: 'TM-1.gff'
        }
      ],
      currentIframeUrl: '/assets/jbrowse/index.html?assembly=Ghirsutum_genome_HAU_v1.0&tracks=TM-1.gff&loc=Ghir_A01:1-1000000',
      iframeKey: 0
    }
  },
  mounted() {
    // 组件挂载时强制刷新iframe
    this.refreshIframe();
  },
  watch: {
    // 监听路由变化，确保iframe正确加载
    $route() {
      this.refreshIframe();
    }
  },
  methods: {
    openGenome(genome) {
      this.currentIframeUrl = `/assets/jbrowse/index.html?assembly=${genome.assembly}&tracks=${genome.track}&loc=Ghir_A01:1-1000000`;
      this.refreshIframe();
    },
    refreshIframe() {
      // 使用key属性强制重新渲染iframe
      this.iframeKey++;
    }
  }
}
</script>

<style scoped>
.embed-container {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}
</style>
