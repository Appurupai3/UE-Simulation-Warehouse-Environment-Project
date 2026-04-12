<template>
  <div class="benchmark-panel">
    <div class="panel-header">
      <h2>Benchmark 結果總覽</h2>
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
      <button @click="handleOptimizeAllOrders" :disabled="loading || selectedAlgorithms.length === 0" class="btn btn-success">{{ loading ? '計算中...' : '重新計算 Benchmark' }}</button>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="batchOptimizationResult" class="result-split">
      <div class="left-list">
        <div class="best-result">
          <p><strong>最佳演算法:</strong> {{ batchOptimizationResult.best_algorithm }}</p>
          <p><strong>最少總步數:</strong> {{ batchOptimizationResult.best_total_steps }}</p>
        </div>

        <div v-for="result in batchOptimizationResult.results" :key="result.algorithm_name" class="algorithm-batch-result">
          <div class="algorithm-header">
            <h4>{{ getAlgorithmLabel(result.algorithm_name) }}</h4>
            <button class="btn btn-preview" @click="selectPreview(result)">看 2D 模擬圖</button>
          </div>
          <div class="batch-summary"><span>總步數: {{ result.total_steps }}</span><span>批次: {{ result.total_batches }}</span></div>
          <div class="batch-sequences">
            <div v-for="batch in result.batches" :key="`seq-${result.algorithm_name}-${batch.batch_number}`" class="seq-row">
              <strong>批次 {{ batch.batch_number }}:</strong> {{ batch.items.join(' → ') }}
            </div>
          </div>
          <div class="actions">
            <button @click="applyBatchesToWarehouse(result)" class="btn btn-apply" :disabled="applyingBatches">寫入訂單</button>
            <button @click="startSimulationFromBenchmark(result)" class="btn btn-primary" :disabled="applyingBatches">開始模擬</button>
          </div>
        </div>
      </div>

      <div class="right-sim2d">
        <h4>2D 倉庫模擬（5 x 10 網格）</h4>
        <p class="sim-caption">藍色：取貨、綠色：回出貨口、紫色：搬離堆疊物；方形框：目標貨物與上層堆疊物。</p>
        <canvas ref="simCanvasRef" class="sim-canvas" width="540" height="360"></canvas>
        <div class="sim-controls">
          <button class="btn btn-preview" @click="startAnimation" :disabled="!animationLegs.length || isAnimating">開始</button>
          <button class="btn btn-apply" @click="pauseAnimation" :disabled="!isAnimating">暫停</button>
          <button class="btn btn-primary" @click="resetAnimation" :disabled="!animationLegs.length">重置</button>
        </div>
        <p v-if="animationLegs.length" class="sim-status">進度：{{ Math.min(animationIndex + 1, animationLegs.length) }} / {{ animationLegs.length }} ｜ {{ currentLegLabel }}</p>
        <div v-if="simulationEvents.length" class="state-log">
          <div v-for="(log, idx) in simulationEvents.slice(0, 6)" :key="`log-${idx}`" class="log-row">{{ log }}</div>
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
    const simulationEvents = ref([])
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
      if (leg.type === 'clear') return `批次 ${leg.batchNumber}・搬離堆疊物（貨物 ${leg.cargoLabel || '?'}）`
      return `批次 ${leg.batchNumber}・${leg.type === 'pickup' ? '去取貨' : '回出貨口'}（貨物 ${leg.cargoLabel || '?'}）`
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

    const getGridMapper = () => {
      const points = cargoLayout.value.map(c => c?.position).filter(Boolean)
      const xLevels = [...new Set(points.map(p => Number(p.x)).filter(Number.isFinite))].sort((a, b) => a - b)
      const zLevels = [...new Set(points.map(p => Number(p.z)).filter(Number.isFinite))].sort((a, b) => b - a)

      if (xLevels.length === 0 || zLevels.length === 0) {
        return () => ({ ...DOCK_CELL })
      }

      const nearest = (arr, value) => {
        let bestIdx = 0
        let bestDist = Number.POSITIVE_INFINITY
        arr.forEach((num, idx) => {
          const d = Math.abs(num - value)
          if (d < bestDist) { bestDist = d; bestIdx = idx }
        })
        return bestIdx
      }

      return (x, z) => {
        const safeX = Number(x)
        const safeZ = Number(z)
        if (!Number.isFinite(safeX) || !Number.isFinite(safeZ)) {
          return { ...DOCK_CELL }
        }
        return {
          col: Math.max(0, Math.min(GRID_COLS - 1, nearest(xLevels, safeX))),
          row: Math.max(0, Math.min(GRID_ROWS - 1, nearest(zLevels, safeZ)))
        }
      }
    }

    const buildGridPath = (from, to) => {
      const path = [{ ...from }]
      let col = from.col
      let row = from.row
      while (col !== to.col) { col += col < to.col ? 1 : -1; path.push({ col, row }) }
      while (row !== to.row) { row += row < to.row ? 1 : -1; path.push({ col, row }) }
      return path
    }

    const getBlockers = (targetPos) => {
      if (!targetPos || !Number.isFinite(Number(targetPos.x)) || !Number.isFinite(Number(targetPos.z)) || !Number.isFinite(Number(targetPos.y))) {
        return []
      }
      return cargoLayout.value
        .map(c => c?.position)
        .filter(Boolean)
        .filter(pos => Number.isFinite(Number(pos.x)) && Number.isFinite(Number(pos.z)) && Number.isFinite(Number(pos.y)))
        .filter(pos => Math.abs(pos.x - targetPos.x) < 0.0001 && Math.abs(pos.z - targetPos.z) < 0.0001 && pos.y > targetPos.y)
    }

    const keyOf = (cell) => `${cell.col}-${cell.row}`

    const initSimulationState = (worldToGrid) => {
      const occupancy = new Map()
      cargoLayout.value.forEach((c) => {
        const pos = c?.position
        if (!pos) return
        const cell = worldToGrid(pos.x, pos.z)
        const key = keyOf(cell)
        occupancy.set(key, (occupancy.get(key) || 0) + 1)
      })
      return { occupancy, maxPerCell: 4 }
    }

    const findAvailableStagingCell = (targetCell, state) => {
      for (let distance = 1; distance <= Math.max(GRID_COLS, GRID_ROWS); distance++) {
        for (let dc = -distance; dc <= distance; dc++) {
          const drAbs = distance - Math.abs(dc)
          const candidates = [
            { col: targetCell.col + dc, row: targetCell.row + drAbs },
            { col: targetCell.col + dc, row: targetCell.row - drAbs }
          ]

          for (const cell of candidates) {
            if (cell.col < 0 || cell.col >= GRID_COLS || cell.row < 0 || cell.row >= GRID_ROWS) continue
            if (cell.col === targetCell.col && cell.row === targetCell.row) continue
            if (cell.col === DOCK_CELL.col && cell.row === DOCK_CELL.row) continue
            const used = state.occupancy.get(keyOf(cell)) || 0
            if (used < state.maxPerCell) return cell
          }
        }
      }
      return null
    }

    const moveOccupancy = (state, fromCell, toCell) => {
      const fromKey = keyOf(fromCell)
      const toKey = keyOf(toCell)
      state.occupancy.set(fromKey, Math.max(0, (state.occupancy.get(fromKey) || 0) - 1))
      state.occupancy.set(toKey, (state.occupancy.get(toKey) || 0) + 1)
    }

    const pushPathLegs = (legs, route, batchNumber, type, cargoLabel = '') => {
      for (let i = 0; i < route.length - 1; i++) legs.push({ batchNumber, type, cargoLabel, from: route[i], to: route[i + 1] })
    }

    const buildAnimationLegs = () => {
      if (!selectedPreview.value?.batches?.length) { animationLegs.value = []; return }

      const worldToGrid = getGridMapper()
      const simulationState = initSimulationState(worldToGrid)
      const legs = []
      const logs = []

      selectedPreview.value.batches.forEach((batch) => {
        const positions = batch.positions || []
        positions.forEach((pos, posIndex) => {
          if (!Number.isFinite(Number(pos?.x)) || !Number.isFinite(Number(pos?.z)) || !Number.isFinite(Number(pos?.y))) {
            return
          }
          const cargoLabel = String(batch.items?.[posIndex] ?? '?')
          const target = worldToGrid(pos.x, pos.z)

          // 1) 先去取貨
          pushPathLegs(legs, buildGridPath(DOCK_CELL, target), batch.batch_number, 'pickup', cargoLabel)

          // 2) 取貨後、回出貨口前，演示搬離堆疊物
          const blockers = getBlockers(pos).slice(0, 4)
          blockers.forEach((_, blockerIndex) => {
            const staging = findAvailableStagingCell(target, simulationState)
            if (!staging) {
              logs.unshift(`批次 ${batch.batch_number} 貨物 ${cargoLabel}: 無可用暫存空間`) 
              return
            }
            pushPathLegs(legs, buildGridPath(target, staging), batch.batch_number, 'clear', cargoLabel)
            moveOccupancy(simulationState, target, staging)
            logs.unshift(`批次 ${batch.batch_number} 貨物 ${cargoLabel}: 搬離阻擋物 #${blockerIndex + 1} 到 (${staging.col + 1},${staging.row + 1})`)
          })

          // 3) 最後回到出貨口
          pushPathLegs(legs, buildGridPath(target, DOCK_CELL), batch.batch_number, 'return', cargoLabel)
          if (legs.length > 4000) return
        })
      })

      animationLegs.value = legs.slice(0, 4000)
      simulationEvents.value = logs
      animationIndex.value = 0
    }

    const parseCargoId = (rawId) => {
      const text = String(rawId ?? '')
      if (text.startsWith('case ')) return Number(text.replace('case ', ''))
      return Number(text)
    }

    const getCargoPositionByLabel = (cargoLabel) => {
      const targetId = Number(cargoLabel)
      if (!Number.isFinite(targetId)) return null
      const hit = cargoLayout.value.find((item) => parseCargoId(item?.id) === targetId)
      return hit?.position || null
    }

    const getBlockerCellsByCargoLabel = (cargoLabel, worldToGrid) => {
      const targetPos = getCargoPositionByLabel(cargoLabel)
      if (!targetPos) return []
      return getBlockers(targetPos)
        .slice(0, 4)
        .map(pos => worldToGrid(pos.x, pos.z))
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
      const center = (cell) => ({ x: pad + cell.col * cellW + cellW / 2, y: pad + cell.row * cellH + cellH / 2 })
      const worldToGrid = getGridMapper()
      const current = animationLegs.value[animationIndex.value]

      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = '#0f172a'
      ctx.fillRect(0, 0, w, h)

      ctx.strokeStyle = 'rgba(148,163,184,0.35)'
      for (let c = 0; c <= GRID_COLS; c++) { const x = pad + c * cellW; ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, h - pad); ctx.stroke() }
      for (let r = 0; r <= GRID_ROWS; r++) { const y = pad + r * cellH; ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke() }

      const dockCenter = center(DOCK_CELL)
      ctx.fillStyle = '#22d3ee'; ctx.beginPath(); ctx.arc(dockCenter.x, dockCenter.y, 7, 0, Math.PI * 2); ctx.fill()
      ctx.fillStyle = '#e2e8f0'; ctx.font = '12px sans-serif'; ctx.fillText('出貨口', dockCenter.x + 10, dockCenter.y - 8)

      // 方形標出要取的貨物目標格與上層堆疊物
      if (current?.cargoLabel) {
        const targetPos = getCargoPositionByLabel(current.cargoLabel)
        if (targetPos) {
          const targetCell = worldToGrid(targetPos.x, targetPos.z)
          const targetX = pad + targetCell.col * cellW
          const targetY = pad + targetCell.row * cellH
          ctx.strokeStyle = '#fbbf24'
          ctx.lineWidth = 3
          ctx.strokeRect(targetX + 2, targetY + 2, cellW - 4, cellH - 4)
        }

        const blockerCells = getBlockerCellsByCargoLabel(current.cargoLabel, worldToGrid)
        blockerCells.forEach((cell) => {
          const x = pad + cell.col * cellW
          const y = pad + cell.row * cellH
          ctx.strokeStyle = '#a78bfa'
          ctx.lineWidth = 2
          ctx.strokeRect(x + 6, y + 6, cellW - 12, cellH - 12)
        })
      }

      for (let i = 0; i < animationIndex.value && i < animationLegs.value.length; i++) {
        const leg = animationLegs.value[i]
        const from = center(leg.from)
        const to = center(leg.to)
        ctx.strokeStyle = leg.type === 'clear' ? '#c084fc' : (leg.type === 'pickup' ? '#60a5fa' : '#34d399')
        ctx.lineWidth = 3
        ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(to.x, to.y); ctx.stroke()
      }

      if (current) {
        const to = center(current.to)
        ctx.fillStyle = '#f59e0b'; ctx.beginPath(); ctx.arc(to.x, to.y, 6, 0, Math.PI * 2); ctx.fill()

        if (current.cargoLabel) {
          ctx.fillStyle = '#fef08a'
          ctx.font = '12px sans-serif'
          ctx.fillText(`貨物 ${current.cargoLabel}`, to.x + 8, to.y - 10)
        }
      }
    }

    const startAnimation = () => {
      if (!animationLegs.value.length || isAnimating.value) return
      isAnimating.value = true
      timer = setInterval(() => {
        if (animationIndex.value >= animationLegs.value.length - 1) { clearInterval(timer); timer = null; isAnimating.value = false; return }
        animationIndex.value += 1
      }, 220)
    }
    const pauseAnimation = () => { if (timer) { clearInterval(timer); timer = null }; isAnimating.value = false }
    const resetAnimation = () => { pauseAnimation(); animationIndex.value = 0; drawCanvas() }

    const handleOptimizeAllOrders = async () => {
      const result = await optimizeAllOrders(selectedAlgorithms.value, 20)
      if (result) { batchOptimizationResult.value = result; selectedPreview.value = result.results?.[0] || null }
    }
    const selectPreview = (result) => { selectedPreview.value = result }

    const writeOrdersFromAlgorithm = async (algorithmResult) => {
      await fetch('http://localhost:8000/orders', { method: 'DELETE' })
      for (const batch of algorithmResult.batches) {
        await fetch('http://localhost:8000/orders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: batch.items.join('-'), items: batch.items }) })
      }
    }
    const saveBenchmarkBridge = (algorithmResult) => {
      localStorage.setItem('benchmark-execution-bridge', JSON.stringify({
        source: 'benchmark', generatedAt: new Date().toISOString(), algorithm: algorithmResult.algorithm_name,
        totalSteps: algorithmResult.total_steps, totalBatches: algorithmResult.total_batches,
        batches: algorithmResult.batches.map(batch => ({ batchNumber: batch.batch_number, stepCount: batch.step_count, items: batch.items }))
      }))
    }
    const applyBatchesToWarehouse = async (algorithmResult) => { if (applyingBatches.value) return; applyingBatches.value = true; try { await writeOrdersFromAlgorithm(algorithmResult); saveBenchmarkBridge(algorithmResult) } finally { applyingBatches.value = false } }
    const startSimulationFromBenchmark = async (algorithmResult) => { if (applyingBatches.value) return; applyingBatches.value = true; try { await writeOrdersFromAlgorithm(algorithmResult); saveBenchmarkBridge(algorithmResult); window.open('/three.html', '_blank') } finally { applyingBatches.value = false } }

    watch(selectedPreview, async () => { pauseAnimation(); buildAnimationLegs(); await nextTick(); drawCanvas() }, { deep: true })
    watch(animationIndex, drawCanvas)
    onBeforeUnmount(pauseAnimation)
    fetchCargoLayout()

    return {
      selectedAlgorithms, availableAlgorithms, batchOptimizationResult, applyingBatches, loading, error,
      animationLegs, animationIndex, isAnimating, simulationEvents, currentLegLabel, simCanvasRef,
      handleOptimizeAllOrders, selectPreview, getAlgorithmLabel, startAnimation, pauseAnimation, resetAnimation,
      applyBatchesToWarehouse, startSimulationFromBenchmark
    }
  }
}
</script>

<style scoped>
.benchmark-panel { padding: 20px; background: #f8f9fa; border-radius: 8px; height: 100%; overflow-y: auto; }
.input-section, .best-result, .algorithm-batch-result, .right-sim2d { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
.form-group { margin-bottom: 12px; }
.algorithm-checkboxes { display: flex; gap: 10px; flex-wrap: wrap; }
.result-split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 12px; }
.left-list { display: flex; flex-direction: column; gap: 10px; }
.algorithm-header { display: flex; justify-content: space-between; align-items: center; }
.batch-summary { margin-top: 6px; display: flex; gap: 12px; font-size: 13px; color: #475569; }
.actions, .sim-controls { display: flex; gap: 8px; margin-top: 10px; }
.btn { padding: 8px 12px; border: 0; border-radius: 6px; color: white; cursor: pointer; }
.btn-success { background: #10b981; } .btn-preview { background: #0ea5e9; } .btn-apply { background: #8b5cf6; } .btn-primary { background: #3b82f6; }
.error-message { color: #dc2626; margin-top: 8px; }
.sim-caption, .sim-status { font-size: 13px; color: #64748b; }
.sim-canvas { width: 100%; background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; }
.batch-sequences { margin-top: 8px; border-top: 1px dashed #e2e8f0; padding-top: 6px; }
.seq-row { font-size: 12px; color: #334155; margin-bottom: 4px; word-break: break-all; }
.state-log { margin-top: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px; max-height: 120px; overflow-y: auto; }
.log-row { font-size: 12px; color: #475569; margin-bottom: 4px; }
@media (max-width: 1100px) { .result-split { grid-template-columns: 1fr; } }
</style>
