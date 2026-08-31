<template>
  <div class="container mt-4">
    <h2>PPI Network</h2>
    <p>此页面正在开发中...</p>
    <div id="msa-container" style="width: 100%; min-height: 500px;"></div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const msaLoaded = ref(false)

onMounted(() => {
  const script = document.createElement('script')
  script.src = 'https://s3.eu-central-1.amazonaws.com/cdn.bio.sh/msa/latest/msa.min.gz.js'
  script.onload = () => {
    msaLoaded.value = true
    initMSA()
  }
  document.head.appendChild(script)
})

function initMSA() {
  if (!window.msa) {
    console.error('MSA library not loaded')
    return
  }

  const fasta = `>seq1
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN
>seq2
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN
>seq3
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN`

  const seqs = window.msa.io.fasta.parse(fasta)

  const m = window.msa({
    el: document.getElementById('msa-container'),
    seqs: seqs,
    vis: {
      conserv: true,
      overviewbox: true,
      seqlogo: true
    },
    zoomer: {
      alignmentWidth: 'auto',
      alignmentHeight: 400,
      autoResize: true
    },
    conf: {
      registerMouseHover: true,
      registerMouseClicks: true
    }
  })

  m.render()
}
</script>

<style scoped>
.container {
  padding: 20px;
}
</style>
