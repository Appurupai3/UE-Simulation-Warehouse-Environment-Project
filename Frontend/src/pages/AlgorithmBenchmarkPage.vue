<template>
  <div class="algorithm-benchmark-page">
    <header class="page-header">
      <h1>演算法 Benchmark 測試</h1>
      <p class="subtitle">用圖像化方式比較演算法，並直接銜接到 3D 模擬</p>
    </header>

    <div class="content-layout">
      <BenchmarkPanel />
    </div>
  </div>
</template>

<script>
import BenchmarkPanel from '../components/AlgorithmBenchmark/BenchmarkPanel.vue'

export default {
  name: 'AlgorithmBenchmarkPage',
  components: {
    BenchmarkPanel
  }
}
</script>

<style scoped>
.algorithm-benchmark-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

.page-header {
  padding: 24px 32px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: #1a1a1a;
  font-weight: 600;
}

.subtitle {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.content-layout {
  flex: 1;
  padding: 20px;
  overflow: hidden;
}
</style>
