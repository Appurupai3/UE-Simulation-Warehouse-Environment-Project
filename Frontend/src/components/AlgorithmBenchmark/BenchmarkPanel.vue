<template>
  <div class="benchmark-panel">
    <div class="panel-header">
      <h2>Benchmark 結果總覽</h2>
      <p>不看程式碼也能直接比較演算法、預估步數、並一鍵銜接 3D 模擬。</p>
    </div>

    <div class="explain-card">
      <h3>步數是怎麼算的？</h3>
      <ul>
        <li>起點固定在 <strong>(0, 0, 0)</strong>。</li>
        <li>每個貨物點位使用 3D 距離：<code>√((dx² + dy² + dz²))</code>。</li>
        <li>每段距離都做 <strong>無條件進位</strong>（ceil）後再加總。</li>
      </ul>
      <p class="explain-note">公式：總步數 = Σ ceil(上一點 → 下一點 的 3D 距離)</p>
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
        {{ loading ? '計算中...' : '重新計算 Benchmark' }}
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="batchOptimizationResult" class="batch-optimization-section">
      <h3>本次最佳結果</h3>

      <div class="best-result">
        <p><strong>最佳演算法:</strong> {{ batchOptimizationResult.best_algorithm }}</p>
        <p><strong>最少總步數:</strong> {{ batchOptimizationResult.best_total_steps }}</p>
        <p><strong>來源訂單數:</strong> {{ batchOptimizationResult.source_orders.length }}</p>
      </div>

      <div v-for="result in batchOptimizationResult.results" :key="result.algorithm_name" class="algorithm-batch-result">
        <div class="algorithm-header">
          <h4>{{ getAlgorithmLabel(result.algorithm_name) }}</h4>
          <div class="actions">
            <button
              @click="applyBatchesToWarehouse(result)"
              class="btn btn-apply"
              :disabled="applyingBatches"
            >
              {{ applyingBatches ? '寫入中...' : '寫入訂單' }}
            </button>
            <button
              @click="startSimulationFromBenchmark(result)"
              class="btn btn-primary"
              :disabled="applyingBatches"
            >
              開始模擬（銜接 Benchmark）
            </button>
          </div>
        </div>

        <div class="batch-summary">
          <span>總批次數: {{ result.total_batches }}</span>
          <span>總項目數: {{ result.total_items }}</span>
          <span>總步數: {{ result.total_steps }}</span>
          <span>執行時間: {{ result.execution_time_ms.toFixed(2) }} ms</span>
        </div>

        <div class="sim2d">
          <h5>2D 模擬圖（批次路線概念）</h5>
          <div class="flow-row">
            <template v-for="(batch, index) in result.batches" :key="`flow-${batch.batch_number}`">
              <div class="flow-node">
                <div class="node-title">批次 {{ batch.batch_number }}</div>
                <div class="node-step">{{ batch.step_count }} 步</div>
                <div class="node-items">{{ batch.items.join(' → ') }}</div>
              </div>
              <div v-if="index < result.batches.length - 1" class="flow-arrow">→</div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
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
      if (result) batchOptimizationResult.value = result
    }

    const getAlgorithmLabel = (name) => {
      const algo = availableAlgorithms.find(a => a.value === name)
      return algo ? algo.label : name
    }

    const writeOrdersFromAlgorithm = async (algorithmResult) => {
      await fetch('http://localhost:8000/orders', { method: 'DELETE' })

      for (const batch of algorithmResult.batches) {
        const orderContent = batch.items.join('-')
        await fetch('http://localhost:8000/orders', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            content: orderContent,
            items: batch.items
          })
        })
      }
    }

    const saveBenchmarkBridge = (algorithmResult) => {
      const payload = {
        source: 'benchmark',
        generatedAt: new Date().toISOString(),
        algorithm: algorithmResult.algorithm_name,
        totalSteps: algorithmResult.total_steps,
        totalBatches: algorithmResult.total_batches,
        batches: algorithmResult.batches.map(batch => ({
          batchNumber: batch.batch_number,
          stepCount: batch.step_count,
          items: batch.items
        }))
      }

      localStorage.setItem('benchmark-execution-bridge', JSON.stringify(payload))
    }

    const applyBatchesToWarehouse = async (algorithmResult) => {
      if (applyingBatches.value) return

      applyingBatches.value = true
      try {
        await writeOrdersFromAlgorithm(algorithmResult)
        saveBenchmarkBridge(algorithmResult)
        alert(`已寫入 ${algorithmResult.total_batches} 筆批次訂單，並建立 Benchmark 銜接資料。`)
      } catch (err) {
        console.error('應用批次失敗:', err)
        alert(`應用批次失敗: ${err.message}`)
      } finally {
        applyingBatches.value = false
      }
    }

    const startSimulationFromBenchmark = async (algorithmResult) => {
      if (applyingBatches.value) return
      applyingBatches.value = true

      try {
        await writeOrdersFromAlgorithm(algorithmResult)
        saveBenchmarkBridge(algorithmResult)
        window.open('/three.html', '_blank')
      } catch (err) {
        console.error('銜接模擬失敗:', err)
        alert(`銜接模擬失敗: ${err.message}`)
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
      applyBatchesToWarehouse,
      startSimulationFromBenchmark
    }
  }
}
</script>

<style scoped>
.benchmark-panel { padding: 20px; background: #f8f9fa; border-radius: 8px; height: 100%; overflow-y: auto; }
.panel-header h2 { margin: 0; color: #333; font-size: 24px; }
.panel-header p { margin: 8px 0 16px; color: #666; }
.explain-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 16px; }
.explain-card h3 { margin: 0 0 8px; font-size: 16px; }
.explain-card ul { margin: 0; padding-left: 18px; color: #4b5563; }
.explain-note { margin: 10px 0 0; color: #1f2937; font-size: 13px; }
.input-section { background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 8px; font-weight: 500; color: #555; }
.algorithm-checkboxes { display: flex; flex-direction: column; gap: 8px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 0; }
.btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-success { background: #10b981; color: white; }
.btn-success:hover:not(:disabled) { background: #059669; }
.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-apply { background: #8b5cf6; color: white; }
.btn-apply:hover:not(:disabled) { background: #7c3aed; }
.error-message { background: #fee2e2; color: #dc2626; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
.batch-optimization-section h3 { margin-bottom: 12px; }
.best-result { background: #ecfeff; border: 1px solid #a5f3fc; border-radius: 6px; padding: 12px; margin-bottom: 16px; }
.algorithm-batch-result { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.algorithm-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.algorithm-header h4 { margin: 0; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.batch-summary { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 10px 18px; color: #4b5563; font-size: 14px; }
.sim2d { margin-top: 12px; border-top: 1px dashed #d1d5db; padding-top: 12px; }
.sim2d h5 { margin: 0 0 10px; font-size: 14px; color: #374151; }
.flow-row { display: flex; align-items: stretch; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.flow-node { min-width: 190px; background: #f8fafc; border: 1px solid #dbeafe; border-radius: 8px; padding: 8px; }
.node-title { font-weight: 700; color: #1d4ed8; }
.node-step { font-size: 13px; color: #0f766e; margin-top: 4px; }
.node-items { font-size: 12px; color: #4b5563; margin-top: 6px; line-height: 1.3; }
.flow-arrow { font-size: 20px; color: #94a3b8; align-self: center; }
</style>
