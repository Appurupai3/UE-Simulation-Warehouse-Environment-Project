<template>
  <div class="benchmark-panel">
    <div class="panel-header">
      <h2>Benchmark 結果總覽</h2>
      <p>不看程式碼也能直接比較演算法、預估步數、並一鍵銜接 3D 模擬。</p>
    </div>

    <div class="explain-card">
      <h3>步數是怎麼算的？</h3>
      <ul>
        <li>搬運路徑：每件貨都從出貨口 <strong>(0, 0, 0)</strong> 出發。</li>
        <li>回程距離：每搬完一件都要計入「回到出貨口」距離。</li>
        <li>堆疊搬離：若同一欄位有更上層貨物，會加上「搬離阻擋物」的估算步數。</li>
      </ul>
      <p class="explain-note">公式（概念）：總步數 = Σ(出貨口→貨位 + 貨位→出貨口) + 堆疊搬離成本</p>
    </div>

    <div class="input-section">
      <div class="form-group">
        <label>選擇演算法</label>
        <div class="algorithm-checkboxes">
          <label v-for="algo in availableAlgorithms" :key="algo.value" class="checkbox-label">
            <input type="checkbox" :value="algo.value" v-model="selectedAlgorithms" />
            {{ algo.label }}
          </label>
        </div>
      </div>

      <button @click="handleOptimizeAllOrders" :disabled="loading || selectedAlgorithms.length === 0" class="btn btn-success">
        {{ loading ? '計算中...' : '重新計算 Benchmark' }}
      </button>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="batchOptimizationResult" class="batch-optimization-section">
      <h3>本次最佳結果</h3>
      <div class="best-result">
        <p><strong>最佳演算法:</strong> {{ batchOptimizationResult.best_algorithm }}</p>
        <p><strong>最少總步數:</strong> {{ batchOptimizationResult.best_total_steps }}</p>
        <p><strong>來源訂單數:</strong> {{ batchOptimizationResult.source_orders.length }}</p>
      </div>

      <div class="result-split">
        <div class="left-list">
          <div v-for="result in batchOptimizationResult.results" :key="result.algorithm_name" class="algorithm-batch-result">
            <div class="algorithm-header">
              <h4>{{ getAlgorithmLabel(result.algorithm_name) }}</h4>
              <button class="btn btn-preview" @click="selectPreview(result)">看 2D 模擬圖</button>
            </div>

            <div class="batch-summary">
              <span>總批次數: {{ result.total_batches }}</span>
              <span>總項目數: {{ result.total_items }}</span>
              <span>總步數: {{ result.total_steps }}</span>
              <span>執行時間: {{ result.execution_time_ms.toFixed(2) }} ms</span>
            </div>

            <div class="actions">
              <button @click="applyBatchesToWarehouse(result)" class="btn btn-apply" :disabled="applyingBatches">
                {{ applyingBatches ? '寫入中...' : '寫入訂單' }}
              </button>
              <button @click="startSimulationFromBenchmark(result)" class="btn btn-primary" :disabled="applyingBatches">
                開始模擬（銜接 Benchmark）
              </button>
            </div>
          </div>
        </div>

        <div class="right-sim2d">
          <h4>2D 倉庫模擬畫布（{{ previewLabel }}）</h4>
          <p class="sim-caption">從倉庫初始佈局開始，逐步播放「去取貨 → 回出貨口」搬運過程。</p>

          <canvas ref="simCanvasRef" class="sim-canvas" width="540" height="360"></canvas>

          <div class="sim-controls">
            <button class="btn btn-preview" @click="startAnimation" :disabled="!animationLegs.length || isAnimating">開始</button>
            <button class="btn btn-apply" @click="pauseAnimation" :disabled="!isAnimating">暫停</button>
            <button class="btn btn-primary" @click="resetAnimation" :disabled="!animationLegs.length">重置</button>
          </div>

          <p v-if="animationLegs.length" class="sim-status">
            進度：{{ Math.min(animationIndex + 1, animationLegs.length) }} / {{ animationLegs.length }}
            ｜目前：{{ currentLegLabel }}
          </p>
          <p v-else class="empty-preview">請先在左側點選「看 2D 模擬圖」。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useBenchmark } from '../../composables/useBenchmark'

export default {
  name: 'BenchmarkPanel',
  setup() {
    const selectedAlgorithms = ref(['original', 'greedy', 'astar'])
    const batchOptimizationResult = ref(null)
    const applyingBatches = ref(false)
    const selectedPreview = ref(null)
    const simCanvasRef = ref(null)
    const cargoLayout = ref([])
    const animationLegs = ref([])
    const animationIndex = ref(0)
    const isAnimating = ref(false)
    let timer = null

    const availableAlgorithms = [
      { value: 'original', label: '原始順序（不整理）' },
      { value: 'greedy', label: '貪婪演算法' },
      { value: 'astar', label: 'A* 演算法' }
    ]

    const { loading, error, optimizeAllOrders } = useBenchmark()

    const getAlgorithmLabel = (name) => {
      const algo = availableAlgorithms.find(a => a.value === name)
      return algo ? algo.label : name
    }

    const previewLabel = computed(() => {
      if (!selectedPreview.value) return '尚未選擇'
      return getAlgorithmLabel(selectedPreview.value.algorithm_name)
    })

    const currentLegLabel = computed(() => {
      const leg = animationLegs.value[animationIndex.value]
      if (!leg) return '待機'
      return `批次 ${leg.batchNumber}・${leg.type === 'pickup' ? '前往取貨' : '返回出貨口'}`
    })

    const fetchCargoLayout = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/benchmark/cargo-layout')
        if (!response.ok) return
        const data = await response.json()
        cargoLayout.value = data?.cargo || []
      } catch (err) {
        console.warn('讀取 cargo layout 失敗', err)
      }
    }

    const buildAnimationLegs = () => {
      if (!selectedPreview.value?.batches) {
        animationLegs.value = []
        return
      }

      const dock = { x: 0, z: 0 }
      const legs = []
      selectedPreview.value.batches.forEach((batch) => {
        const positions = batch.positions || []
        positions.forEach((pos) => {
          legs.push({ batchNumber: batch.batch_number, type: 'pickup', from: dock, to: { x: pos.x, z: pos.z } })
          legs.push({ batchNumber: batch.batch_number, type: 'return', from: { x: pos.x, z: pos.z }, to: dock })
        })
      })
      animationLegs.value = legs
      animationIndex.value = 0
    }

    const normalizePoint = (x, z, bounds, width, height) => {
      const padding = 30
      const drawW = width - padding * 2
      const drawH = height - padding * 2
      const nx = bounds.maxX === bounds.minX ? 0.5 : (x - bounds.minX) / (bounds.maxX - bounds.minX)
      const nz = bounds.maxZ === bounds.minZ ? 0.5 : (z - bounds.minZ) / (bounds.maxZ - bounds.minZ)
      return { x: padding + nx * drawW, y: padding + (1 - nz) * drawH }
    }

    const drawCanvas = () => {
      const canvas = simCanvasRef.value
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const width = canvas.width
      const height = canvas.height

      const cargoPoints = cargoLayout.value
        .map(item => item?.position)
        .filter(Boolean)
        .map(pos => ({ x: pos.x, z: pos.z }))

      const routePoints = animationLegs.value.flatMap(leg => [leg.from, leg.to])
      const allPoints = [...cargoPoints, ...routePoints, { x: 0, z: 0 }]
      const xs = allPoints.map(p => p.x)
      const zs = allPoints.map(p => p.z)
      const bounds = {
        minX: Math.min(...xs, -1),
        maxX: Math.max(...xs, 1),
        minZ: Math.min(...zs, -1),
        maxZ: Math.max(...zs, 1)
      }

      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = '#0b1020'
      ctx.fillRect(0, 0, width, height)

      // 倉庫初始貨位
      cargoPoints.forEach((point) => {
        const p = normalizePoint(point.x, point.z, bounds, width, height)
        ctx.fillStyle = 'rgba(148, 163, 184, 0.55)'
        ctx.beginPath()
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2)
        ctx.fill()
      })

      // 出貨口
      const dock = normalizePoint(0, 0, bounds, width, height)
      ctx.fillStyle = '#22d3ee'
      ctx.beginPath()
      ctx.arc(dock.x, dock.y, 6, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = '#e2e8f0'
      ctx.font = '12px sans-serif'
      ctx.fillText('出貨口', dock.x + 8, dock.y - 8)

      // 已完成路徑
      for (let i = 0; i < animationIndex.value && i < animationLegs.value.length; i++) {
        const leg = animationLegs.value[i]
        const from = normalizePoint(leg.from.x, leg.from.z, bounds, width, height)
        const to = normalizePoint(leg.to.x, leg.to.z, bounds, width, height)
        ctx.strokeStyle = leg.type === 'pickup' ? '#60a5fa' : '#34d399'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(from.x, from.y)
        ctx.lineTo(to.x, to.y)
        ctx.stroke()
      }

      // 當前路徑
      const current = animationLegs.value[animationIndex.value]
      if (current) {
        const from = normalizePoint(current.from.x, current.from.z, bounds, width, height)
        const to = normalizePoint(current.to.x, current.to.z, bounds, width, height)
        ctx.strokeStyle = '#f59e0b'
        ctx.lineWidth = 3
        ctx.beginPath()
        ctx.moveTo(from.x, from.y)
        ctx.lineTo(to.x, to.y)
        ctx.stroke()

        ctx.fillStyle = '#f8fafc'
        ctx.beginPath()
        ctx.arc(to.x, to.y, 4, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const startAnimation = () => {
      if (!animationLegs.value.length || isAnimating.value) return
      isAnimating.value = true
      timer = setInterval(() => {
        if (animationIndex.value >= animationLegs.value.length - 1) {
          clearInterval(timer)
          timer = null
          isAnimating.value = false
          return
        }
        animationIndex.value += 1
      }, 600)
    }

    const pauseAnimation = () => {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
      isAnimating.value = false
    }

    const resetAnimation = () => {
      pauseAnimation()
      animationIndex.value = 0
      drawCanvas()
    }

    const handleOptimizeAllOrders = async () => {
      const result = await optimizeAllOrders(selectedAlgorithms.value, 20)
      if (result) {
        batchOptimizationResult.value = result
        selectedPreview.value = result.results?.[0] || null
      }
    }

    const selectPreview = (result) => {
      selectedPreview.value = result
    }

    const writeOrdersFromAlgorithm = async (algorithmResult) => {
      await fetch('http://localhost:8000/orders', { method: 'DELETE' })
      for (const batch of algorithmResult.batches) {
        const orderContent = batch.items.join('-')
        await fetch('http://localhost:8000/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: orderContent, items: batch.items })
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

    watch(selectedPreview, async () => {
      pauseAnimation()
      buildAnimationLegs()
      await nextTick()
      drawCanvas()
    }, { deep: true })

    watch(animationIndex, () => {
      drawCanvas()
    })

    onBeforeUnmount(() => {
      pauseAnimation()
    })

    fetchCargoLayout()

    return {
      selectedAlgorithms,
      availableAlgorithms,
      batchOptimizationResult,
      applyingBatches,
      loading,
      error,
      previewLabel,
      animationLegs,
      animationIndex,
      isAnimating,
      currentLegLabel,
      simCanvasRef,
      handleOptimizeAllOrders,
      selectPreview,
      getAlgorithmLabel,
      startAnimation,
      pauseAnimation,
      resetAnimation,
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
.btn-preview { background: #0ea5e9; color: white; padding: 8px 12px; }
.error-message { background: #fee2e2; color: #dc2626; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
.batch-optimization-section h3 { margin-bottom: 12px; }
.best-result { background: #ecfeff; border: 1px solid #a5f3fc; border-radius: 6px; padding: 12px; margin-bottom: 16px; }
.result-split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start; }
.left-list { display: flex; flex-direction: column; gap: 12px; }
.algorithm-batch-result { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
.algorithm-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.algorithm-header h4 { margin: 0; }
.batch-summary { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 10px 18px; color: #4b5563; font-size: 14px; }
.actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.right-sim2d { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; min-height: 260px; }
.right-sim2d h4 { margin: 0; }
.sim-caption { margin: 6px 0 12px; font-size: 13px; color: #6b7280; }
.sim-canvas { width: 100%; border-radius: 8px; background: #0b1020; border: 1px solid #1e293b; margin-bottom: 10px; }
.sim-controls { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.sim-status { margin: 0; font-size: 13px; color: #334155; }
.empty-preview { color: #6b7280; font-size: 13px; }

@media (max-width: 1100px) {
  .result-split { grid-template-columns: 1fr; }
}
</style>
