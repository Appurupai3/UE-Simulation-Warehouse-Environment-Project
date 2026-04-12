<template>
  <div class="benchmark-panel">
    <div class="panel-header">
      <h2>Benchmark 結果總覽</h2>
      <p>不看程式碼也能直接比較演算法、預估步數、並一鍵銜接 3D 模擬。</p>
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

    <div v-if="batchOptimizationResult" class="result-split">
      <div class="left-list">
        <div class="best-result">
          <p><strong>最佳演算法:</strong> {{ batchOptimizationResult.best_algorithm }}</p>
          <p><strong>最少總步數:</strong> {{ batchOptimizationResult.best_total_steps }}</p>
          <p><strong>來源訂單數:</strong> {{ batchOptimizationResult.source_orders.length }}</p>
        </div>

        <div v-for="result in batchOptimizationResult.results" :key="result.algorithm_name" class="algorithm-batch-result">
          <div class="algorithm-header">
            <h4>{{ getAlgorithmLabel(result.algorithm_name) }}</h4>
            <button class="btn btn-preview" @click="selectPreview(result)">看 2D 模擬圖</button>
          </div>
          <div class="batch-summary">
            <span>總步數: {{ result.total_steps }}</span>
            <span>批次: {{ result.total_batches }}</span>
          </div>
          <div class="actions">
            <button @click="applyBatchesToWarehouse(result)" class="btn btn-apply" :disabled="applyingBatches">寫入訂單</button>
            <button @click="startSimulationFromBenchmark(result)" class="btn btn-primary" :disabled="applyingBatches">開始模擬</button>
          </div>
        </div>
      </div>

      <div class="right-sim2d">
        <h4>2D 倉庫模擬（5 x 10 網格）</h4>
        <p class="sim-caption">先畫出 5x10 網格與出貨口，再逐步模擬車輛移動路徑。</p>
        <canvas ref="simCanvasRef" class="sim-canvas" width="540" height="360"></canvas>

        <div class="sim-controls">
          <button class="btn btn-preview" @click="startAnimation" :disabled="!animationLegs.length || isAnimating">開始</button>
          <button class="btn btn-apply" @click="pauseAnimation" :disabled="!isAnimating">暫停</button>
          <button class="btn btn-primary" @click="resetAnimation" :disabled="!animationLegs.length">重置</button>
        </div>

        <p v-if="animationLegs.length" class="sim-status">
          進度：{{ Math.min(animationIndex + 1, animationLegs.length) }} / {{ animationLegs.length }} ｜ {{ currentLegLabel }}
        </p>
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
    const GRID_ROWS = 5
    const GRID_COLS = 10
    const DOCK_CELL = { col: 0, row: 0 }

    const selectedAlgorithms = ref(['original', 'greedy', 'astar'])
    const batchOptimizationResult = ref(null)
    const applyingBatches = ref(false)
    const selectedPreview = ref(null)
    const cargoLayout = ref([])
    const simCanvasRef = ref(null)

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

    const getAlgorithmLabel = (name) => availableAlgorithms.find(a => a.value === name)?.label || name

    const currentLegLabel = computed(() => {
      const leg = animationLegs.value[animationIndex.value]
      if (!leg) return '待機'
      return `批次 ${leg.batchNumber}・${leg.type === 'pickup' ? '去取貨' : '回出貨口'}`
    })

    const fetchCargoLayout = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/benchmark/cargo-layout')
        if (!response.ok) return
        const data = await response.json()
        cargoLayout.value = data?.cargo || []
      } catch (e) {
        console.warn('載入 cargo-layout 失敗', e)
      }
    }

    const buildWorldBounds = () => {
      const points = cargoLayout.value.map(c => c?.position).filter(Boolean)
      const xs = points.map(p => p.x)
      const zs = points.map(p => p.z)
      return {
        minX: Math.min(...xs, -1),
        maxX: Math.max(...xs, 1),
        minZ: Math.min(...zs, -1),
        maxZ: Math.max(...zs, 1)
      }
    }

    const toGridCell = (x, z, bounds) => {
      const nx = bounds.maxX === bounds.minX ? 0 : (x - bounds.minX) / (bounds.maxX - bounds.minX)
      const nz = bounds.maxZ === bounds.minZ ? 0 : (z - bounds.minZ) / (bounds.maxZ - bounds.minZ)
      return {
        col: Math.max(0, Math.min(GRID_COLS - 1, Math.round(nx * (GRID_COLS - 1)))),
        row: Math.max(0, Math.min(GRID_ROWS - 1, Math.round((1 - nz) * (GRID_ROWS - 1))))
      }
    }

    const buildGridPath = (from, to) => {
      const path = [{ ...from }]
      let col = from.col
      let row = from.row
      while (col !== to.col) {
        col += col < to.col ? 1 : -1
        path.push({ col, row })
      }
      while (row !== to.row) {
        row += row < to.row ? 1 : -1
        path.push({ col, row })
      }
      return path
    }

    const buildAnimationLegs = () => {
      if (!selectedPreview.value?.batches?.length) {
        animationLegs.value = []
        return
      }

      const bounds = buildWorldBounds()
      const legs = []

      selectedPreview.value.batches.forEach((batch) => {
        const positions = batch.positions || []
        positions.forEach((pos) => {
          const target = toGridCell(pos.x, pos.z, bounds)
          const routeA = buildGridPath(DOCK_CELL, target)
          const routeB = buildGridPath(target, DOCK_CELL)

          for (let i = 0; i < routeA.length - 1; i++) {
            legs.push({ batchNumber: batch.batch_number, type: 'pickup', from: routeA[i], to: routeA[i + 1] })
          }
          for (let i = 0; i < routeB.length - 1; i++) {
            legs.push({ batchNumber: batch.batch_number, type: 'return', from: routeB[i], to: routeB[i + 1] })
          }
        })
      })

      animationLegs.value = legs
      animationIndex.value = 0
    }

    const drawCanvas = () => {
      const canvas = simCanvasRef.value
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const w = canvas.width
      const h = canvas.height
      const pad = 24
      const cellW = (w - pad * 2) / GRID_COLS
      const cellH = (h - pad * 2) / GRID_ROWS

      const cellCenter = (cell) => ({
        x: pad + cell.col * cellW + cellW / 2,
        y: pad + cell.row * cellH + cellH / 2
      })

      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = '#0f172a'
      ctx.fillRect(0, 0, w, h)

      // 畫 5x10 網格
      ctx.strokeStyle = 'rgba(148,163,184,0.35)'
      for (let c = 0; c <= GRID_COLS; c++) {
        const x = pad + c * cellW
        ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, h - pad); ctx.stroke()
      }
      for (let r = 0; r <= GRID_ROWS; r++) {
        const y = pad + r * cellH
        ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke()
      }

      // 出貨口
      const dockCenter = cellCenter(DOCK_CELL)
      ctx.fillStyle = '#22d3ee'
      ctx.beginPath(); ctx.arc(dockCenter.x, dockCenter.y, 7, 0, Math.PI * 2); ctx.fill()
      ctx.fillStyle = '#e2e8f0'
      ctx.font = '12px sans-serif'
      ctx.fillText('出貨口', dockCenter.x + 10, dockCenter.y - 8)

      // 已完成路徑
      for (let i = 0; i < animationIndex.value && i < animationLegs.value.length; i++) {
        const leg = animationLegs.value[i]
        const from = cellCenter(leg.from)
        const to = cellCenter(leg.to)
        ctx.strokeStyle = leg.type === 'pickup' ? '#60a5fa' : '#34d399'
        ctx.lineWidth = 3
        ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(to.x, to.y); ctx.stroke()
      }

      // 當前車輛位置
      const current = animationLegs.value[animationIndex.value]
      if (current) {
        const to = cellCenter(current.to)
        ctx.fillStyle = '#f59e0b'
        ctx.beginPath(); ctx.arc(to.x, to.y, 6, 0, Math.PI * 2); ctx.fill()
      }
    }

    const startAnimation = () => {
      if (!animationLegs.value.length || isAnimating.value) return
      isAnimating.value = true
      timer = setInterval(() => {
        if (animationIndex.value >= animationLegs.value.length - 1) {
          clearInterval(timer); timer = null; isAnimating.value = false; return
        }
        animationIndex.value += 1
      }, 220)
    }

    const pauseAnimation = () => {
      if (timer) { clearInterval(timer); timer = null }
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

    const selectPreview = (result) => { selectedPreview.value = result }

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
        batches: algorithmResult.batches.map(batch => ({ batchNumber: batch.batch_number, stepCount: batch.step_count, items: batch.items }))
      }
      localStorage.setItem('benchmark-execution-bridge', JSON.stringify(payload))
    }

    const applyBatchesToWarehouse = async (algorithmResult) => {
      if (applyingBatches.value) return
      applyingBatches.value = true
      try {
        await writeOrdersFromAlgorithm(algorithmResult)
        saveBenchmarkBridge(algorithmResult)
        alert(`已寫入 ${algorithmResult.total_batches} 筆批次訂單`)
      } finally { applyingBatches.value = false }
    }

    const startSimulationFromBenchmark = async (algorithmResult) => {
      if (applyingBatches.value) return
      applyingBatches.value = true
      try {
        await writeOrdersFromAlgorithm(algorithmResult)
        saveBenchmarkBridge(algorithmResult)
        window.open('/three.html', '_blank')
      } finally { applyingBatches.value = false }
    }

    watch(selectedPreview, async () => {
      pauseAnimation()
      buildAnimationLegs()
      await nextTick()
      drawCanvas()
    }, { deep: true })

    watch(animationIndex, drawCanvas)
    onBeforeUnmount(pauseAnimation)
    fetchCargoLayout()

    return {
      selectedAlgorithms,
      availableAlgorithms,
      batchOptimizationResult,
      applyingBatches,
      loading,
      error,
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
.panel-header h2 { margin: 0; font-size: 24px; }
.input-section, .best-result, .algorithm-batch-result, .right-sim2d { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
.form-group { margin-bottom: 12px; }
.algorithm-checkboxes { display: flex; gap: 10px; flex-wrap: wrap; }
.checkbox-label { display: flex; align-items: center; gap: 6px; }
.result-split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 12px; }
.left-list { display: flex; flex-direction: column; gap: 10px; }
.algorithm-header { display: flex; justify-content: space-between; align-items: center; }
.batch-summary { margin-top: 6px; display: flex; gap: 12px; font-size: 13px; color: #475569; }
.actions { display: flex; gap: 8px; margin-top: 10px; }
.btn { padding: 8px 12px; border: 0; border-radius: 6px; color: white; cursor: pointer; }
.btn-success { background: #10b981; }
.btn-preview { background: #0ea5e9; }
.btn-apply { background: #8b5cf6; }
.btn-primary { background: #3b82f6; }
.error-message { color: #dc2626; margin-top: 8px; }
.sim-caption { font-size: 13px; color: #64748b; }
.sim-canvas { width: 100%; background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; }
.sim-controls { display: flex; gap: 8px; margin-top: 10px; }
.sim-status { margin-top: 8px; font-size: 13px; color: #334155; }
@media (max-width: 1100px) { .result-split { grid-template-columns: 1fr; } }
</style>
