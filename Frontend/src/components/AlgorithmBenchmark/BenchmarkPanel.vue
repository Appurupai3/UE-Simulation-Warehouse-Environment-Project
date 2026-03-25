<template>
  <div class="benchmark-panel">
    <div class="panel-header">
      <h2>Benchmark 測試</h2>
    </div>
    
    <div class="input-section">
      <div class="form-group">
        <label>選擇演算法</label>
        <div class="algorithm-checkboxes">
          <label v-for="algo in availableAlgorithms" :key="algo.value" class="checkbox-label">
            <input
              type="checkbox"
              :value="algo.value"
              v-model="selectedAlgorithms"
            />
            {{ algo.label }}
          </label>
        </div>
      </div>
      
      <button
        @click="handleOptimizeAllOrders"
        :disabled="loading || selectedAlgorithms.length === 0"
        class="btn btn-success"
      >
        {{ loading ? '優化中...' : '執行批次優化' }}
      </button>
    </div>
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
    
    <div v-if="batchOptimizationResult" class="batch-optimization-section">
      <h3>批次優化結果</h3>
      
      <div class="best-result">
        <p><strong>最佳演算法:</strong> {{ batchOptimizationResult.best_algorithm }}</p>
        <p><strong>最少總步數:</strong> {{ batchOptimizationResult.best_total_steps }}</p>
        <p><strong>來源訂單數:</strong> {{ batchOptimizationResult.source_orders.length }}</p>
      </div>
      
      <div v-for="result in batchOptimizationResult.results" :key="result.algorithm_name" class="algorithm-batch-result">
        <div class="algorithm-header">
          <h4>{{ getAlgorithmLabel(result.algorithm_name) }}</h4>
          <button
            @click="applyBatchesToWarehouse(result)"
            class="btn btn-apply"
            :disabled="applyingBatches"
          >
            {{ applyingBatches ? '應用中...' : '應用到倉儲 →' }}
          </button>
        </div>
        <div class="batch-summary">
          <span>總批次數: {{ result.total_batches }}</span>
          <span>總項目數: {{ result.total_items }}</span>
          <span>總步數: {{ result.total_steps }}</span>
          <span>執行時間: {{ result.execution_time_ms.toFixed(2) }} ms</span>
        </div>
        
        <table class="batch-table">
          <thead>
            <tr>
              <th>批次</th>
              <th>項目數</th>
              <th>步數</th>
              <th>項目列表</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="batch in result.batches" :key="batch.batch_number">
              <td>批次 {{ batch.batch_number }}</td>
              <td>{{ batch.items.length }}</td>
              <td>{{ batch.step_count }}</td>
              <td class="path-cell">{{ batch.items.join(' → ') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useBenchmark } from '../../composables/useBenchmark'

export default {
  name: 'BenchmarkPanel',
  setup() {
    const selectedAlgorithms = ref(['original', 'greedy', 'astar'])
    const batchOptimizationResult = ref(null)
    const applyingBatches = ref(false)
    
    const availableAlgorithms = [
      { value: 'original', label: '原始順序（不整理）' },
      { value: 'greedy', label: '貪婪演算法' },
      { value: 'astar', label: 'A* 演算法' }
    ]
    
    const {
      loading,
      error,
      optimizeAllOrders
    } = useBenchmark()
    
    const handleOptimizeAllOrders = async () => {
      const result = await optimizeAllOrders(selectedAlgorithms.value, 20)
      
      if (result) {
        batchOptimizationResult.value = result
      }
    }
    
    const getAlgorithmLabel = (name) => {
      const algo = availableAlgorithms.find(a => a.value === name)
      return algo ? algo.label : name
    }
    
    const applyBatchesToWarehouse = async (algorithmResult) => {
      if (applyingBatches.value) return
      
      applyingBatches.value = true
      
      try {
        // 1. 清除現有訂單
        await fetch('http://localhost:8000/orders', {
          method: 'DELETE'
        })
        
        // 2. 為每個批次創建新訂單
        for (const batch of algorithmResult.batches) {
          const orderContent = batch.items.join('-')
          await fetch('http://localhost:8000/orders', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              content: orderContent,
              items: batch.items
            })
          })
        }
        
        // 3. 顯示成功訊息
        alert(`成功應用 ${getAlgorithmLabel(algorithmResult.algorithm_name)} 的批次優化結果！\n已創建 ${algorithmResult.total_batches} 個新訂單。\n請前往 Three.js 場景執行訂單。`)
        
        // 4. 可選：自動跳轉到 Three.js 場景
        const shouldNavigate = confirm('是否立即前往 Three.js 場景？')
        if (shouldNavigate) {
          window.open('/three.html', '_blank')
        }
        
      } catch (err) {
        console.error('應用批次失敗:', err)
        alert(`應用批次失敗: ${err.message}`)
      } finally {
        applyingBatches.value = false
      }
    }
    
    return {
      selectedAlgorithms,
      availableAlgorithms,
      batchOptimizationResult,
      applyingBatches,
      loading,
      error,
      handleOptimizeAllOrders,
      getAlgorithmLabel,
      applyBatchesToWarehouse
    }
  }
}
</script>

<style scoped>
.benchmark-panel {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  height: 100%;
  overflow-y: auto;
}

.panel-header h2 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 24px;
}

.input-section {
  background: white;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #555;
}

.order-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.order-input:focus {
  outline: none;
  border-color: #007acc;
}

.order-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.order-select:focus {
  outline: none;
  border-color: #007acc;
}

.algorithm-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 0;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #007acc;
  color: white;
  width: 100%;
}

.btn-primary:hover:not(:disabled) {
  background: #005a9e;
}

.btn-success {
  background: #28a745;
  color: white;
  width: 100%;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-info {
  background: #17a2b8;
  color: white;
  width: 100%;
}

.btn-info:hover:not(:disabled) {
  background: #138496;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  margin-bottom: 12px;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.error-message {
  padding: 12px;
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  margin-bottom: 20px;
}

.result-section,
.history-section {
  background: white;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.result-section h3,
.history-section h3 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 18px;
}

.best-result {
  background: #d4edda;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  border: 1px solid #c3e6cb;
}

.best-result p {
  margin: 4px 0;
  color: #155724;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
}

.results-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

.results-table .best-row {
  background: #d4edda;
  font-weight: 500;
}

.path-cell {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #666;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: 500;
}

.history-index {
  color: #007acc;
}

.history-time {
  color: #6c757d;
  font-size: 12px;
}

.history-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: #495057;
}

.batch-optimization-section {
  background: white;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.batch-optimization-section h3 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 18px;
}

.algorithm-batch-result {
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
}

.algorithm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.algorithm-batch-result h4 {
  margin: 0;
  color: #007acc;
  font-size: 16px;
}

.btn-apply {
  background: #ff6b35;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-apply:hover:not(:disabled) {
  background: #e55a2b;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
}

.btn-apply:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.batch-summary {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  font-size: 14px;
}

.batch-summary span {
  color: #495057;
}

.batch-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.batch-table th,
.batch-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
}

.batch-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
}
</style>
