<template>
  <div class="algorithm-benchmark-page">
    <header class="page-header">
      <h1>演算法 Benchmark 測試</h1>
      <p class="subtitle">測試和比較不同演算法的效能</p>
    </header>
    
    <div class="content-layout">
      <div class="left-panel">
        <CodeEditor
          :test-order="testOrder"
          @execution-success="handleExecutionSuccess"
        />
      </div>
      
      <div class="right-panel">
        <BenchmarkPanel />
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import CodeEditor from '../components/AlgorithmBenchmark/CodeEditor.vue'
import BenchmarkPanel from '../components/AlgorithmBenchmark/BenchmarkPanel.vue'

export default {
  name: 'AlgorithmBenchmarkPage',
  components: {
    CodeEditor,
    BenchmarkPanel
  },
  setup() {
    const testOrder = ref({
      items: [75, 12, 43]
    })
    
    const handleExecutionSuccess = (result) => {
      console.log('程式碼執行成功:', result)
      // 可以在這裡處理執行成功的邏輯
      // 例如：更新測試訂單、顯示通知等
    }
    
    return {
      testOrder,
      handleExecutionSuccess
    }
  }
}
</script>

<style scoped>
.algorithm-benchmark-page {
  height: 100vh;
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
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.left-panel,
.right-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 1200px) {
  .content-layout {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
}
</style>
