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
        <h4>2D 倉庫模擬（10 x 5 網格）</h4>
        <p class="sim-caption">藍色：取貨、綠色：回出貨口、紫色：搬離堆疊物；方形框：目標貨物與上層堆疊物。</p>
        <canvas ref="simCanvasRef" class="sim-canvas" width="540" height="360"></canvas>
        <div class="sim-controls">
          <button class="btn btn-preview" @click="startAnimation" :disabled="!animationLegs.length || isAnimating">開始</button>
          <button class="btn btn-apply" @click="stepBackward" :disabled="!animationLegs.length || animationIndex === 0">後退</button>
          <button class="btn btn-apply" @click="pauseAnimation" :disabled="!isAnimating">暫停</button>
          <button class="btn btn-preview" @click="stepForward" :disabled="!animationLegs.length || animationIndex >= animationLegs.length - 1">前進</button>
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
    const GRID_ROWS = 10
    const GRID_COLS = 5
    const DOCK_CELLS = [
      { col: 0, row: 1, label: 'X1Y2' },
      { col: 3, row: 1, label: 'X4Y2' }
    ]
    const CAR_CONFIGS = [
      { id: 'car-1', label: '1號車', color: '#f59e0b', dockIndex: 0 },
      { id: 'car-2', label: '2號車', color: '#fb7185', dockIndex: 1 }
    ]

    const selectedAlgorithms = ref(['original', 'greedy', 'astar', 'obstacle_aware'])
    const batchOptimizationResult = ref(null)
    const applyingBatches = ref(false)
    const selectedPreview = ref(null)
    const cargoLayout = ref([])
    const simCanvasRef = ref(null)

    const animationLegs = ref([])
    const animationIndex = ref(0)
    const isAnimating = ref(false)
    const simulationEvents = ref([])
    const previewCargoCells = ref(new Map())
    let timer = null

    const availableAlgorithms = [
      { value: 'original', label: '原始順序（不整理）' },
      { value: 'greedy', label: '貪婪演算法' },
      { value: 'astar', label: 'A* 演算法' },
      { value: 'obstacle_aware', label: '避障優先演算法' }
    ]
    const { loading, error, optimizeAllOrders } = useBenchmark()

    const getAlgorithmLabel = (name) => availableAlgorithms.find(a => a.value === name)?.label || name

    const currentLegLabel = computed(() => {
      const frame = animationLegs.value[animationIndex.value]
      if (!frame?.moves?.length) return '待機'
      return frame.moves
        .map((move) => {
          if (move.type === 'wait') return `${move.carLabel}・等待（避碰）`
          if (move.type === 'replan') return `${move.carLabel}・CBS 重規劃移動`
          if (move.type === 'clear') return `${move.carLabel}・批次 ${move.batchNumber} 搬離堆疊物（貨物 ${move.cargoLabel || '?'}）`
          return `${move.carLabel}・批次 ${move.batchNumber} ${move.type === 'pickup' ? '去取貨' : '回出貨口'}（貨物 ${move.cargoLabel || '?'}）`
        })
        .join(' ｜ ')
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
      const zLevels = [...new Set(points.map(p => Number(p.z)).filter(Number.isFinite))].sort((a, b) => a - b)

      if (xLevels.length === 0 || zLevels.length === 0) {
        return () => ({ col: DOCK_CELLS[0].col, row: DOCK_CELLS[0].row })
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
          return { col: DOCK_CELLS[0].col, row: DOCK_CELLS[0].row }
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

    const buildSmartGridPath = (from, to, state, algorithmName) => {
      if (algorithmName !== 'obstacle_aware') return buildGridPath(from, to)

      const startKey = keyOf(from)
      const goalKey = keyOf(to)
      const frontier = [{ key: startKey, cost: 0, priority: 0 }]
      const cameFrom = new Map([[startKey, null]])
      const costSoFar = new Map([[startKey, 0]])

      const parseKey = (key) => {
        const [col, row] = key.split('-').map(Number)
        return { col, row }
      }

      const neighborsOf = (cell) => (
        [
          { col: cell.col + 1, row: cell.row },
          { col: cell.col - 1, row: cell.row },
          { col: cell.col, row: cell.row + 1 },
          { col: cell.col, row: cell.row - 1 }
        ]
      ).filter((next) => next.col >= 0 && next.col < GRID_COLS && next.row >= 0 && next.row < GRID_ROWS)

      const heuristic = (a, b) => Math.abs(a.col - b.col) + Math.abs(a.row - b.row)

      while (frontier.length > 0) {
        frontier.sort((a, b) => a.priority - b.priority)
        const current = frontier.shift()
        if (!current) break
        if (current.key === goalKey) break

        const currentCell = parseKey(current.key)
        const currentCost = costSoFar.get(current.key) ?? 0

        neighborsOf(currentCell).forEach((nextCell) => {
          const nextKey = keyOf(nextCell)
          const occupied = state?.occupancy?.get(nextKey) || 0
          const dockPenalty = DOCK_CELLS.some((dock) => dock.col === nextCell.col && dock.row === nextCell.row) && nextKey !== goalKey ? 1.5 : 0
          const occupiedPenalty = occupied * 0.25
          const newCost = currentCost + 1 + dockPenalty + occupiedPenalty

          if (!costSoFar.has(nextKey) || newCost < (costSoFar.get(nextKey) ?? Number.POSITIVE_INFINITY)) {
            costSoFar.set(nextKey, newCost)
            const priority = newCost + heuristic(nextCell, to)
            frontier.push({ key: nextKey, cost: newCost, priority })
            cameFrom.set(nextKey, current.key)
          }
        })
      }

      if (!cameFrom.has(goalKey)) return buildGridPath(from, to)

      const reversedPath = []
      let cursor = goalKey
      while (cursor) {
        reversedPath.push(parseKey(cursor))
        cursor = cameFrom.get(cursor) || null
      }
      return reversedPath.reverse()
    }

    const getBlockers = (targetPos) => {
      if (!targetPos || !Number.isFinite(Number(targetPos.x)) || !Number.isFinite(Number(targetPos.z)) || !Number.isFinite(Number(targetPos.y))) {
        return []
      }
      return cargoLayout.value
        .filter(item => item?.position)
        .map((item) => ({ id: parseCargoId(item.id), pos: item.position }))
        .filter(item => Number.isFinite(item.id))
        .filter(item => Number.isFinite(Number(item.pos.x)) && Number.isFinite(Number(item.pos.z)) && Number.isFinite(Number(item.pos.y)))
        .filter(item => Math.abs(item.pos.x - targetPos.x) < 0.0001 && Math.abs(item.pos.z - targetPos.z) < 0.0001 && item.pos.y > targetPos.y)
        .sort((a, b) => b.pos.y - a.pos.y)
    }

    const keyOf = (cell) => `${cell.col}-${cell.row}`

    const initSimulationState = (worldToGrid) => {
      const occupancy = new Map()
      const cargoCells = new Map()
      cargoLayout.value.forEach((c) => {
        const pos = c?.position
        if (!pos) return
        const cargoId = parseCargoId(c.id)
        const cell = worldToGrid(pos.x, pos.z)
        const key = keyOf(cell)
        occupancy.set(key, (occupancy.get(key) || 0) + 1)
        if (Number.isFinite(cargoId)) cargoCells.set(String(cargoId), { ...cell })
      })
      return { occupancy, cargoCells, maxPerCell: 6 }
    }

    const getManhattanRingCells = (centerCell, distance) => {
      const cells = []
      const seen = new Set()

      const addCell = (cell) => {
        if (cell.col < 0 || cell.col >= GRID_COLS || cell.row < 0 || cell.row >= GRID_ROWS) return
        const key = keyOf(cell)
        if (seen.has(key)) return
        seen.add(key)
        cells.push(cell)
      }

      if (distance === 1) {
        [
          { col: centerCell.col, row: centerCell.row - 1 },
          { col: centerCell.col + 1, row: centerCell.row },
          { col: centerCell.col, row: centerCell.row + 1 },
          { col: centerCell.col - 1, row: centerCell.row }
        ].forEach(addCell)
        return cells
      }

      for (let dr = -distance; dr <= distance; dr++) {
        const dcAbs = distance - Math.abs(dr)
        addCell({ col: centerCell.col - dcAbs, row: centerCell.row + dr })
        addCell({ col: centerCell.col + dcAbs, row: centerCell.row + dr })
      }

      return cells
    }

    const findAvailableStagingCell = (targetCell, state, protectedCellCounts = new Map()) => {
      const maxDistance = Math.max(GRID_COLS, GRID_ROWS)
      for (let distance = 1; distance <= maxDistance; distance++) {
        const ringCells = getManhattanRingCells(targetCell, distance)
        for (const cell of ringCells) {
          if (DOCK_CELLS.some(d => d.col === cell.col && d.row === cell.row)) continue
          if (cell.row === GRID_ROWS - 1) continue
          if ((protectedCellCounts.get(keyOf(cell)) || 0) > 0) continue
          const used = state.occupancy.get(keyOf(cell)) || 0
          if (used < state.maxPerCell) return cell
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


    const pushPathLegs = (legs, route, batchNumber, type, cargoLabel = '', carryId = null, carConfig) => {
      for (let i = 0; i < route.length - 1; i++) {
        legs.push({
          batchNumber, type, cargoLabel, carryId,
          carId: carConfig.id,
          carLabel: carConfig.label,
          carColor: carConfig.color,
          from: route[i], to: route[i + 1]
        })
      }
    }

    const buildPendingPickupCellCounter = (preview, worldToGrid) => {
      const pending = new Map()
      const batches = preview?.batches || []
      batches.forEach((batch) => {
        const positions = batch?.positions || []
        positions.forEach((pos) => {
          if (!Number.isFinite(Number(pos?.x)) || !Number.isFinite(Number(pos?.z))) return
          const cell = worldToGrid(pos.x, pos.z)
          const key = keyOf(cell)
          pending.set(key, (pending.get(key) || 0) + 1)
        })
      })
      return pending
    }

    const buildParallelFrames = (carLegQueues) => {
      const isCellFree = (reservations, time, cell) => !reservations.vertex.has(`${time}:${keyOf(cell)}`)
      const isEdgeFree = (reservations, time, from, to) => !reservations.edge.has(`${time}:${keyOf(to)}->${keyOf(from)}`)
      const addReservation = (reservations, time, from, to) => {
        reservations.vertex.add(`${time}:${keyOf(to)}`)
        reservations.edge.add(`${time}:${keyOf(from)}->${keyOf(to)}`)
      }
      const getNeighbors = (cell) => (
        [
          { col: cell.col + 1, row: cell.row },
          { col: cell.col - 1, row: cell.row },
          { col: cell.col, row: cell.row + 1 },
          { col: cell.col, row: cell.row - 1 }
        ]
      ).filter((next) => next.col >= 0 && next.col < GRID_COLS && next.row >= 0 && next.row < GRID_ROWS)

      const findPathWithReservations = (startCell, targetCell, startTime, reservations, maxDepth = 48) => {
        const startKey = `${startTime}:${keyOf(startCell)}`
        const queue = [{ cell: { ...startCell }, time: startTime }]
        const visited = new Set([startKey])
        const parents = new Map([[startKey, null]])

        while (queue.length) {
          const current = queue.shift()
          if (!current) break
          if (keyOf(current.cell) === keyOf(targetCell)) {
            const path = []
            let cursorKey = `${current.time}:${keyOf(current.cell)}`
            while (cursorKey) {
              const [timeText, coordText] = cursorKey.split(':')
              const [col, row] = coordText.split('-').map(Number)
              path.push({ col, row, time: Number(timeText) })
              cursorKey = parents.get(cursorKey) || null
            }
            return path.reverse()
          }

          if (current.time - startTime >= maxDepth) continue
          const options = [...getNeighbors(current.cell), { ...current.cell }]
          options.forEach((nextCell) => {
            const nextTime = current.time + 1
            if (!isCellFree(reservations, nextTime, nextCell)) return
            if (!isEdgeFree(reservations, nextTime, current.cell, nextCell)) return
            const nextKey = `${nextTime}:${keyOf(nextCell)}`
            if (visited.has(nextKey)) return
            visited.add(nextKey)
            parents.set(nextKey, `${current.time}:${keyOf(current.cell)}`)
            queue.push({ cell: nextCell, time: nextTime })
          })
        }

        return null
      }

      const buildPrioritizedPlan = (config, queue, reservations) => {
        const plan = []
        let current = { ...DOCK_CELLS[config.dockIndex] }
        let pointer = 0
        let time = 0
        let guard = 0

        while (pointer < queue.length && guard < 12000) {
          guard += 1
          const leg = queue[pointer]
          const segmentPath = findPathWithReservations(current, leg.to, time, reservations)

          if (!segmentPath || segmentPath.length < 2) {
            const waitMove = {
              ...leg,
              type: 'wait',
              from: { ...current },
              to: { ...current },
              cargoLabel: ''
            }
            plan.push(waitMove)
            addReservation(reservations, time + 1, current, current)
            time += 1
            continue
          }

          for (let i = 1; i < segmentPath.length; i++) {
            const prev = segmentPath[i - 1]
            const next = segmentPath[i]
            const isFinalStep = i === segmentPath.length - 1
            const moveType = isFinalStep ? leg.type : (keyOf(prev) === keyOf(next) ? 'wait' : 'replan')
            const move = {
              ...leg,
              type: moveType,
              from: { col: prev.col, row: prev.row },
              to: { col: next.col, row: next.row },
              cargoLabel: moveType === 'wait' ? '' : leg.cargoLabel
            }
            plan.push(move)
            addReservation(reservations, next.time, move.from, move.to)
          }

          current = { ...leg.to }
          time = segmentPath[segmentPath.length - 1].time
          pointer += 1
        }

        return plan
      }

      const priorityOrder = [...CAR_CONFIGS].sort((a, b) => carLegQueues[a.id].length - carLegQueues[b.id].length)
      const reservations = { vertex: new Set(), edge: new Set() }
      const plans = {}
      priorityOrder.forEach((config) => {
        plans[config.id] = buildPrioritizedPlan(config, carLegQueues[config.id], reservations)
      })

      const maxLen = Math.max(...CAR_CONFIGS.map((config) => plans[config.id]?.length || 0), 0)
      const carPositions = Object.fromEntries(CAR_CONFIGS.map((config) => [config.id, { ...DOCK_CELLS[config.dockIndex] }]))
      const frames = []

      for (let t = 0; t < maxLen; t++) {
        const moves = []
        CAR_CONFIGS.forEach((config) => {
          const move = plans[config.id]?.[t]
          if (!move) return
          carPositions[config.id] = { ...move.to }
          if (move.type !== 'wait') moves.push(move)
        })
        frames.push({ moves, carPositions: JSON.parse(JSON.stringify(carPositions)) })
      }

      return frames
    }

    const buildAnimationLegs = () => {
      if (!selectedPreview.value?.batches?.length) { animationLegs.value = []; return }

      const worldToGrid = getGridMapper()
      const simulationState = initSimulationState(worldToGrid)
      const initialCargoCells = new Map(simulationState.cargoCells)
      const carLegQueues = { 'car-1': [], 'car-2': [] }
      const pendingPickupCellCounts = buildPendingPickupCellCounter(selectedPreview.value, worldToGrid)
      const logs = []
      const activeAlgorithm = selectedPreview.value?.algorithm_name || 'original'
      if (activeAlgorithm === 'obstacle_aware') logs.unshift('2D 模擬：使用避障優先演算法路徑規劃')

      selectedPreview.value.batches.forEach((batch, batchIndex) => {
        const carConfig = CAR_CONFIGS[batchIndex % CAR_CONFIGS.length]
        const queue = carLegQueues[carConfig.id]
        const positions = batch.positions || []
        positions.forEach((pos, posIndex) => {
          if (!Number.isFinite(Number(pos?.x)) || !Number.isFinite(Number(pos?.z)) || !Number.isFinite(Number(pos?.y))) {
            return
          }
          const cargoLabel = String(batch.items?.[posIndex] ?? '?')
          const target = worldToGrid(pos.x, pos.z)
          const dock = DOCK_CELLS[carConfig.dockIndex]
          const targetKey = keyOf(target)
          pendingPickupCellCounts.set(targetKey, Math.max(0, (pendingPickupCellCounts.get(targetKey) || 0) - 1))

          // 1) 先去取貨（不載貨）
          pushPathLegs(queue, buildSmartGridPath(dock, target, simulationState, activeAlgorithm), batch.batch_number, 'pickup', cargoLabel, null, carConfig)

          // 2) 取貨後、回出貨口前，演示搬離堆疊物（與 3D 相同：距離 1 再距離 2）
          const blockers = getBlockers(pos).slice(0, 4)
          blockers.forEach((blocker, blockerIndex) => {
            const staging = findAvailableStagingCell(target, simulationState, pendingPickupCellCounts)
            if (!staging) {
              logs.unshift(`批次 ${batch.batch_number} 貨物 ${cargoLabel}: 無可用暫存空間`) 
              return
            }
            const blockerId = String(blocker.id)
            pushPathLegs(queue, buildSmartGridPath(target, staging, simulationState, activeAlgorithm), batch.batch_number, 'clear', cargoLabel, blockerId, carConfig)
            moveOccupancy(simulationState, target, staging)
            simulationState.cargoCells.set(blockerId, { ...staging })
            logs.unshift(`${carConfig.label} 批次 ${batch.batch_number} 貨物 ${cargoLabel}: 搬離阻擋物 #${blockerIndex + 1} 到 (${staging.col + 1},${staging.row + 1})`)
            pushPathLegs(queue, buildSmartGridPath(staging, target, simulationState, activeAlgorithm), batch.batch_number, 'clear', cargoLabel, null, carConfig)
          })

          // 3) 最後回到對應出貨口（此段載貨）
          pushPathLegs(queue, buildSmartGridPath(target, dock, simulationState, activeAlgorithm), batch.batch_number, 'return', cargoLabel, cargoLabel, carConfig)
          simulationState.cargoCells.set(cargoLabel, { col: dock.col, row: dock.row })
        })
      })

      animationLegs.value = buildParallelFrames(carLegQueues).slice(0, 4000)
      simulationEvents.value = logs
      previewCargoCells.value = initialCargoCells
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
      const currentFrame = animationLegs.value[animationIndex.value]

      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = '#0f172a'
      ctx.fillRect(0, 0, w, h)

      ctx.strokeStyle = 'rgba(148,163,184,0.35)'
      for (let c = 0; c <= GRID_COLS; c++) { const x = pad + c * cellW; ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, h - pad); ctx.stroke() }
      for (let r = 0; r <= GRID_ROWS; r++) { const y = pad + r * cellH; ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke() }

      DOCK_CELLS.forEach((dock) => {
        const dockCenter = center(dock)
        ctx.fillStyle = '#22d3ee'; ctx.beginPath(); ctx.arc(dockCenter.x, dockCenter.y, 7, 0, Math.PI * 2); ctx.fill()
        ctx.fillStyle = '#e2e8f0'; ctx.font = '12px sans-serif'; ctx.fillText(dock.label, dockCenter.x + 8, dockCenter.y - 8)
      })

      // 方形標出要取貨與堆疊物，並讓物品隨搬運動態更新位置
      const dynamicCells = new Map(previewCargoCells.value)
      for (let i = 0; i <= animationIndex.value && i < animationLegs.value.length; i++) {
        const frame = animationLegs.value[i]
        frame?.moves?.forEach((move) => {
          if (move?.carryId) dynamicCells.set(String(move.carryId), { ...move.to })
        })
      }

      const activeCargoMoves = (currentFrame?.moves || []).filter((move) => move.cargoLabel)
      const blockerTargets = []
      activeCargoMoves.forEach((move) => {
        const targetPos = getCargoPositionByLabel(move.cargoLabel)
        if (!targetPos) return
        blockerTargets.push(targetPos)
        const highlightedCell = dynamicCells.get(String(move.cargoLabel)) || worldToGrid(targetPos.x, targetPos.z)
        const targetX = pad + highlightedCell.col * cellW
        const targetY = pad + highlightedCell.row * cellH
        ctx.strokeStyle = move.carColor || '#fbbf24'
        ctx.lineWidth = 3
        ctx.strokeRect(targetX + 2, targetY + 2, cellW - 4, cellH - 4)
      })

      blockerTargets.forEach((targetPos) => {
        const blockerIds = getBlockers(targetPos).map(b => String(b.id)).slice(0, 4)
        blockerIds.forEach((id) => {
          const cell = dynamicCells.get(id)
          if (!cell) return
          const x = pad + cell.col * cellW
          const y = pad + cell.row * cellH
          ctx.strokeStyle = '#a78bfa'
          ctx.lineWidth = 2
          ctx.strokeRect(x + 6, y + 6, cellW - 12, cellH - 12)
        })
      })

      for (let i = 0; i < animationIndex.value && i < animationLegs.value.length; i++) {
        const frame = animationLegs.value[i]
        frame?.moves?.forEach((move) => {
          const from = center(move.from)
          const to = center(move.to)
          ctx.strokeStyle = move.type === 'clear' ? '#c084fc' : (move.type === 'pickup' ? '#60a5fa' : '#34d399')
          ctx.lineWidth = 3
          ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(to.x, to.y); ctx.stroke()
        })
      }

      const positions = currentFrame?.carPositions || Object.fromEntries(
        CAR_CONFIGS.map((config) => [config.id, { ...DOCK_CELLS[config.dockIndex] }])
      )
      CAR_CONFIGS.forEach((config, index) => {
        const carCell = positions[config.id]
        if (!carCell) return
        const to = center(carCell)
        ctx.fillStyle = config.color
        ctx.beginPath(); ctx.arc(to.x, to.y, 6, 0, Math.PI * 2); ctx.fill()
        ctx.fillStyle = '#fef08a'
        ctx.font = '12px sans-serif'
        ctx.fillText(config.label, to.x + 8, to.y - 10 + index * 12)
      })
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
    const stepForward = () => {
      if (!animationLegs.value.length) return
      pauseAnimation()
      animationIndex.value = Math.min(animationLegs.value.length - 1, animationIndex.value + 1)
    }
    const stepBackward = () => {
      if (!animationLegs.value.length) return
      pauseAnimation()
      animationIndex.value = Math.max(0, animationIndex.value - 1)
    }

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
      animationLegs, animationIndex, isAnimating, simulationEvents, previewCargoCells, currentLegLabel, simCanvasRef,
      handleOptimizeAllOrders, selectPreview, getAlgorithmLabel, startAnimation, pauseAnimation, resetAnimation, stepForward, stepBackward,
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
