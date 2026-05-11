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

    <div class="random-benchmark-section">
      <div class="random-header">
        <div>
          <h3>隨機多局驗證</h3>
          <p>一次產生多個 task / 多局，並用「出貨口 → 連續取貨順序 → 回出貨口」計步，比較四個演算法每次任務與平均步數。</p>
        </div>
        <button @click="handleRandomBenchmark" :disabled="loading || selectedAlgorithms.length === 0" class="btn btn-primary">{{ loading ? '隨機測試中...' : '開始隨機 Benchmark' }}</button>
      </div>

      <div class="random-controls">
        <label>局數
          <input v-model.number="randomConfig.rounds" type="number" min="1" max="100" />
        </label>
        <label>每局 Task 數
          <input v-model.number="randomConfig.tasksPerRound" type="number" min="1" max="50" />
        </label>
        <label>每個 Task 貨物數
          <input v-model.number="randomConfig.itemsPerTask" type="number" min="1" max="230" />
        </label>
        <label>Seed（可空白）
          <input v-model="randomConfig.seed" type="number" placeholder="固定 seed 可重現" />
        </label>
      </div>

      <div v-if="randomBenchmarkResult" class="random-results">
        <div class="best-result random-best">
          <p><strong>隨機測試最佳平均:</strong> {{ getAlgorithmLabel(randomBenchmarkResult.best_algorithm) }}</p>
          <p><strong>設定:</strong> {{ randomBenchmarkResult.rounds }} 局 × {{ randomBenchmarkResult.tasks_per_round }} tasks / 每 task {{ randomBenchmarkResult.items_per_task }} 件</p>
          <p><strong>Seed:</strong> {{ randomBenchmarkResult.seed ?? '未指定' }}</p>
        </div>

        <div class="random-chart-card">
          <div class="chart-title">平均步數比較圖</div>
          <div v-for="row in randomChartRows" :key="`chart-${row.algorithm_name}`" class="chart-row">
            <div class="chart-label">{{ getAlgorithmLabel(row.algorithm_name) }}</div>
            <div class="chart-track">
              <div class="chart-bar" :style="{ width: `${row.width}%` }"></div>
            </div>
            <div class="chart-value">{{ row.average_steps.toFixed(2) }}</div>
            <div class="chart-delta" :class="{ best: row.delta === 0 }">{{ row.delta === 0 ? '最佳' : `+${row.delta.toFixed(2)}` }}</div>
          </div>
          <p class="chart-note">用 seed、每個 task 訂單、每個演算法 path / step 與 2D 模擬交叉檢查，避免結果看起來像亂數硬湊。</p>
        </div>

        <div class="summary-table-wrap">
          <table class="benchmark-table">
            <thead>
              <tr>
                <th>演算法</th>
                <th>平均步數</th>
                <th>總步數</th>
                <th>最低</th>
                <th>最高</th>
                <th>勝出次數</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="summary in sortedRandomSummaries" :key="summary.algorithm_name">
                <td>{{ getAlgorithmLabel(summary.algorithm_name) }}</td>
                <td>{{ summary.average_steps.toFixed(2) }}</td>
                <td>{{ summary.total_steps }}</td>
                <td>{{ summary.min_steps }}</td>
                <td>{{ summary.max_steps }}</td>
                <td>{{ summary.wins }} / {{ summary.total_runs }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="summary-table-wrap task-table-wrap">
          <table class="benchmark-table">
            <thead>
              <tr>
                <th>局 / Task</th>
                <th>Random 訂單</th>
                <th v-for="algo in randomBenchmarkResult.algorithms" :key="`head-${algo}`">{{ getAlgorithmLabel(algo) }}</th>
                <th>最佳</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in randomBenchmarkResult.tasks" :key="`${task.round_number}-${task.task_number}`">
                <td>第 {{ task.round_number }} 局 / T{{ task.task_number }}</td>
                <td class="order-cell">{{ task.order.items.join('-') }}</td>
                <td v-for="algo in randomBenchmarkResult.algorithms" :key="`${task.round_number}-${task.task_number}-${algo}`">
                  <div class="task-step-cell">
                    <span class="step-count">{{ getTaskStep(task, algo) }}</span>
                    <button
                      class="btn-mini"
                      :class="{ active: isRandomPreviewSelected(task, algo) }"
                      @click="selectRandomTaskPreview(task, algo)"
                    >
                      看 2D
                    </button>
                  </div>
                  <div class="path-cell">{{ getTaskPath(task, algo).join(' → ') }}</div>
                </td>
                <td>{{ getAlgorithmLabel(task.best_algorithm) }}（{{ task.best_step_count }}）</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="batchOptimizationResult || selectedPreview" class="result-split">
      <div v-if="batchOptimizationResult" class="left-list">
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
        <p v-if="selectedPreview?.preview_title" class="sim-selection">目前預覽：{{ selectedPreview.preview_title }}</p>
        <p class="sim-caption">藍色：取貨、綠色：回出貨口、紫色：搬離堆疊物；車體固定面向單一方向、以 2 格足跡規劃與避碰。</p>
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
      { col: 0, row: 0, label: 'X1Y1' },
      { col: 3, row: 0, label: 'X4Y1' }
    ]
    const CAR_LENGTH_CELLS = 2
    const DEFAULT_CAR_DIRECTION = { dc: 0, dr: 1 }
    const CAR_CONFIGS = [
      { id: 'car-1', label: '1號車', color: '#f59e0b', dockIndex: 0, startCell: { x: 1, y: 2 }, startDirection: DEFAULT_CAR_DIRECTION },
      { id: 'car-2', label: '2號車', color: '#fb7185', dockIndex: 1, startCell: { x: 4, y: 2 }, startDirection: DEFAULT_CAR_DIRECTION }
    ]
    const clampGridCell = (col, row) => ({
      col: Math.max(0, Math.min(GRID_COLS - 1, Math.round(col))),
      row: Math.max(0, Math.min(GRID_ROWS - 1, Math.round(row)))
    })
    const oneBasedToGridCell = (cell) => {
      const x = Number(cell?.x)
      const y = Number(cell?.y)
      const safeCol = Number.isFinite(x) ? x - 1 : 0
      const safeRow = Number.isFinite(y) ? y - 1 : 0
      return clampGridCell(safeCol, safeRow)
    }
    const normalizeStartCell = (cell) => {
      if (!cell) return null
      if (Number.isFinite(Number(cell.x)) || Number.isFinite(Number(cell.y))) {
        return oneBasedToGridCell(cell)
      }
      const col = Number(cell.col)
      const row = Number(cell.row)
      if (Number.isFinite(col) && Number.isFinite(row)) {
        return clampGridCell(col, row)
      }
      return null
    }
    const getCarHomeCell = (config) => {
      const normalizedStart = normalizeStartCell(config?.startCell)
      if (normalizedStart) return normalizedStart
      const dock = DOCK_CELLS[config?.dockIndex] || DOCK_CELLS[0]
      return { col: dock.col, row: Math.min(GRID_ROWS - 1, dock.row + 1) }
    }

    const selectedAlgorithms = ref(['original', 'greedy', 'astar', 'obstacle_aware'])
    const batchOptimizationResult = ref(null)
    const randomBenchmarkResult = ref(null)
    const randomConfig = ref({ rounds: 3, tasksPerRound: 4, itemsPerTask: 6, seed: '' })
    const applyingBatches = ref(false)
    const selectedPreview = ref(null)
    const selectedRandomPreviewKey = ref('')
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
    const { loading, error, optimizeAllOrders, runRandomBenchmark } = useBenchmark()

    const getAlgorithmLabel = (name) => availableAlgorithms.find(a => a.value === name)?.label || name

    const sortedRandomSummaries = computed(() => {
      const summaries = randomBenchmarkResult.value?.summaries || []
      return [...summaries].sort((a, b) => a.average_steps - b.average_steps)
    })

    const randomChartRows = computed(() => {
      const summaries = sortedRandomSummaries.value
      if (!summaries.length) return []
      const bestAverage = summaries[0].average_steps
      const maxAverage = Math.max(...summaries.map(item => item.average_steps), bestAverage)
      return summaries.map((summary) => ({
        ...summary,
        width: maxAverage > 0 ? Math.max(6, (summary.average_steps / maxAverage) * 100) : 0,
        delta: summary.average_steps - bestAverage
      }))
    })

    const getTaskAlgorithmResult = (task, algorithmName) => task?.results?.find(item => item.algorithm_name === algorithmName) || null

    const getTaskStep = (task, algorithmName) => {
      const result = getTaskAlgorithmResult(task, algorithmName)
      return result?.step_count ?? '-'
    }

    const getTaskPath = (task, algorithmName) => {
      const result = getTaskAlgorithmResult(task, algorithmName)
      return result?.path || task?.order?.items || []
    }

    const getRandomPreviewKey = (task, algorithmName) => `${task?.round_number || 0}-${task?.task_number || 0}-${algorithmName}`

    const buildRandomTaskPreview = (task, algorithmName) => {
      const result = getTaskAlgorithmResult(task, algorithmName)
      if (!task || !result) return null
      const path = result.path || task.order?.items || []
      return {
        algorithm_name: algorithmName,
        total_steps: result.step_count,
        total_batches: 1,
        preview_title: `隨機第 ${task.round_number} 局 / Task ${task.task_number} / ${getAlgorithmLabel(algorithmName)} / ${result.step_count} 步`,
        batches: [
          {
            batch_number: 1,
            items: path,
            path,
            step_count: result.step_count,
            positions: result.positions || []
          }
        ]
      }
    }

    const isRandomPreviewSelected = (task, algorithmName) => selectedRandomPreviewKey.value === getRandomPreviewKey(task, algorithmName)

    const selectRandomTaskPreview = (task, algorithmName) => {
      const preview = buildRandomTaskPreview(task, algorithmName)
      if (!preview) return
      selectedPreview.value = preview
      selectedRandomPreviewKey.value = getRandomPreviewKey(task, algorithmName)
    }

    const currentLegLabel = computed(() => {
      const frame = animationLegs.value[animationIndex.value]
      if (!frame?.moves?.length) return '待機'
      return frame.moves
        .map((move) => {
          if (move.type === 'wait') return `${move.carLabel}・等待（避碰）`
          if (move.type === 'replan') return `${move.carLabel}・CBS 重規劃移動`
          if (move.type === 'clear') return `${move.carLabel}・批次 ${move.batchNumber} 搬離堆疊物（貨物 ${move.cargoLabel || '?'}）`
          if (move.type === 'park') return `${move.carLabel}・回到出貨口下方待命`
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

    const normalizeDirection = (direction) => {
      const dc = Number(direction?.dc)
      const dr = Number(direction?.dr)
      if (Number.isFinite(dc) && Number.isFinite(dr) && (dc !== 0 || dr !== 0)) {
        return { dc: Math.sign(dc), dr: Math.sign(dr) }
      }
      return { ...DEFAULT_CAR_DIRECTION }
    }

    const getCarHomeState = (config) => ({
      cell: getCarHomeCell(config),
      direction: normalizeDirection(config?.startDirection)
    })

    const getCarFootprint = (cell, direction) => {
      const normalizedDirection = normalizeDirection(direction)
      const cells = []
      for (let i = 0; i < CAR_LENGTH_CELLS; i++) {
        cells.push({
          col: cell.col - normalizedDirection.dc * i,
          row: cell.row - normalizedDirection.dr * i
        })
      }
      return cells
    }

    const isInsideGrid = (cell) => cell.col >= 0 && cell.col < GRID_COLS && cell.row >= 0 && cell.row < GRID_ROWS
    const stateKey = (state) => `${state.cell.col}-${state.cell.row}|${state.direction.dc},${state.direction.dr}`
    const cloneState = (state) => ({ cell: { ...state.cell }, direction: { ...state.direction } })

    const buildParallelFrames = (carLegQueues) => {
      const footprintKeys = (state) => getCarFootprint(state.cell, state.direction).map(keyOf)
      const isFootprintInside = (state) => getCarFootprint(state.cell, state.direction).every(isInsideGrid)
      const isFootprintFree = (reservations, time, state) => (
        isFootprintInside(state) && footprintKeys(state).every((cellKey) => !reservations.vertex.has(`${time}:${cellKey}`))
      )
      const isEdgeFree = (reservations, time, fromState, toState) => {
        const fromKeys = footprintKeys(fromState)
        const toKeys = footprintKeys(toState)
        return fromKeys.every((fromKey) => toKeys.every((toKey) => !reservations.edge.has(`${time}:${toKey}->${fromKey}`)))
      }
      const addReservation = (reservations, time, fromState, toState) => {
        footprintKeys(toState).forEach((cellKey) => reservations.vertex.add(`${time}:${cellKey}`))
        const fromKeys = footprintKeys(fromState)
        const toKeys = footprintKeys(toState)
        fromKeys.forEach((fromKey) => {
          toKeys.forEach((toKey) => reservations.edge.add(`${time}:${fromKey}->${toKey}`))
        })
      }
      const reserveInitialState = (reservations, state) => {
        footprintKeys(state).forEach((cellKey) => reservations.vertex.add(`0:${cellKey}`))
      }
      const getNextStates = (state) => {
        const movementOptions = [
          { dc: 1, dr: 0 },
          { dc: -1, dr: 0 },
          { dc: 0, dr: 1 },
          { dc: 0, dr: -1 }
        ].map((step) => ({
          cell: { col: state.cell.col + step.dc, row: state.cell.row + step.dr },
          direction: { ...state.direction }
        }))
        return [{ cell: { ...state.cell }, direction: { ...state.direction } }, ...movementOptions]
          .filter(isFootprintInside)
      }
      const getReachableTargetKeys = (targetCell, direction) => {
        const targetKeys = []
        const normalizedDirection = normalizeDirection(direction)
        for (let i = 0; i < CAR_LENGTH_CELLS; i++) {
          const candidateState = {
            cell: {
              col: targetCell.col + normalizedDirection.dc * i,
              row: targetCell.row + normalizedDirection.dr * i
            },
            direction: normalizedDirection
          }
          if (isFootprintInside(candidateState)) targetKeys.push(keyOf(candidateState.cell))
        }
        return targetKeys.length ? new Set(targetKeys) : new Set([keyOf(targetCell)])
      }

      const findPathWithReservations = (startState, targetCell, startTime, reservations, maxDepth = 80) => {
        const startKey = `${startTime}:${stateKey(startState)}`
        const targetKeys = getReachableTargetKeys(targetCell, startState.direction)
        const queue = [{ state: cloneState(startState), time: startTime }]
        const visited = new Set([startKey])
        const parents = new Map([[startKey, null]])

        while (queue.length) {
          const current = queue.shift()
          if (!current) break
          if (targetKeys.has(keyOf(current.state.cell))) {
            const path = []
            let cursorKey = `${current.time}:${stateKey(current.state)}`
            while (cursorKey) {
              const [timeText, stateText] = cursorKey.split(':')
              const [coordText, directionText] = stateText.split('|')
              const [col, row] = coordText.split('-').map(Number)
              const [dc, dr] = directionText.split(',').map(Number)
              path.push({ cell: { col, row }, direction: { dc, dr }, time: Number(timeText) })
              cursorKey = parents.get(cursorKey) || null
            }
            return path.reverse()
          }

          if (current.time - startTime >= maxDepth) continue
          getNextStates(current.state).forEach((nextState) => {
            const nextTime = current.time + 1
            if (!isFootprintFree(reservations, nextTime, nextState)) return
            if (!isEdgeFree(reservations, nextTime, current.state, nextState)) return
            const nextKey = `${nextTime}:${stateKey(nextState)}`
            if (visited.has(nextKey)) return
            visited.add(nextKey)
            parents.set(nextKey, `${current.time}:${stateKey(current.state)}`)
            queue.push({ state: cloneState(nextState), time: nextTime })
          })
        }

        return null
      }

      const buildPrioritizedPlan = (config, queue, reservations) => {
        const plan = []
        let currentState = getCarHomeState(config)
        let pointer = 0
        let time = 0
        let guard = 0
        reserveInitialState(reservations, currentState)

        while (pointer < queue.length && guard < 12000) {
          guard += 1
          const leg = queue[pointer]
          const segmentPath = findPathWithReservations(currentState, leg.to, time, reservations)

          if (segmentPath?.length === 1) {
            pointer += 1
            continue
          }

          if (!segmentPath) {
            const waitMove = {
              ...leg,
              type: 'wait',
              from: { ...currentState.cell },
              to: { ...currentState.cell },
              fromState: cloneState(currentState),
              toState: cloneState(currentState),
              cargoLabel: ''
            }
            plan.push(waitMove)
            addReservation(reservations, time + 1, currentState, currentState)
            time += 1
            pointer += 1
            continue
          }

          for (let i = 1; i < segmentPath.length; i++) {
            const prev = segmentPath[i - 1]
            const next = segmentPath[i]
            const prevState = { cell: { ...prev.cell }, direction: { ...prev.direction } }
            const nextState = { cell: { ...next.cell }, direction: { ...next.direction } }
            const isFinalStep = i === segmentPath.length - 1
            const moveType = isFinalStep ? leg.type : (keyOf(prev.cell) === keyOf(next.cell) ? 'wait' : 'replan')
            const move = {
              ...leg,
              type: moveType,
              from: { ...prev.cell },
              to: { ...next.cell },
              fromState: cloneState(prevState),
              toState: cloneState(nextState),
              cargoLabel: moveType === 'wait' ? '' : leg.cargoLabel
            }
            plan.push(move)
            addReservation(reservations, next.time, prevState, nextState)
          }

          const lastState = segmentPath[segmentPath.length - 1]
          currentState = { cell: { ...lastState.cell }, direction: { ...lastState.direction } }
          time = lastState.time
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
      const carStates = Object.fromEntries(CAR_CONFIGS.map((config) => [config.id, getCarHomeState(config)]))
      const carPositions = Object.fromEntries(CAR_CONFIGS.map((config) => [config.id, { ...carStates[config.id].cell }]))
      const frames = [{
        moves: [],
        carPositions: JSON.parse(JSON.stringify(carPositions)),
        carStates: JSON.parse(JSON.stringify(carStates))
      }]

      for (let t = 0; t < maxLen; t++) {
        const moves = []
        CAR_CONFIGS.forEach((config) => {
          const move = plans[config.id]?.[t]
          if (!move) return
          carStates[config.id] = cloneState(move.toState || { cell: move.to, direction: carStates[config.id].direction })
          carPositions[config.id] = { ...carStates[config.id].cell }
          if (move.type !== 'wait') moves.push(move)
        })
        frames.push({
          moves,
          carPositions: JSON.parse(JSON.stringify(carPositions)),
          carStates: JSON.parse(JSON.stringify(carStates))
        })
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
      logs.unshift(`2D 模擬：車體固定面向單一方向，長度 ${CAR_LENGTH_CELLS} 格，使用足跡感知的時空預約路徑規劃`)
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
          const home = getCarHomeCell(carConfig)
          const targetKey = keyOf(target)
          pendingPickupCellCounts.set(targetKey, Math.max(0, (pendingPickupCellCounts.get(targetKey) || 0) - 1))

          // 1) 先去取貨（不載貨）
          pushPathLegs(queue, buildSmartGridPath(home, target, simulationState, activeAlgorithm), batch.batch_number, 'pickup', cargoLabel, null, carConfig)

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

          // 3) 先把貨物送到對應出貨口，再讓車回到出貨口下方一格待命
          pushPathLegs(queue, buildSmartGridPath(target, dock, simulationState, activeAlgorithm), batch.batch_number, 'return', cargoLabel, cargoLabel, carConfig)
          simulationState.cargoCells.set(cargoLabel, { col: dock.col, row: dock.row })
          pushPathLegs(queue, buildSmartGridPath(dock, home, simulationState, activeAlgorithm), batch.batch_number, 'park', '', null, carConfig)
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
          ctx.strokeStyle = move.type === 'clear' ? '#c084fc' : (move.type === 'pickup' ? '#60a5fa' : (move.type === 'park' ? '#94a3b8' : '#34d399'))
          ctx.lineWidth = 3
          ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(to.x, to.y); ctx.stroke()
        })
      }

      const positions = currentFrame?.carPositions || Object.fromEntries(
        CAR_CONFIGS.map((config) => [config.id, getCarHomeCell(config)])
      )
      const carryingByCar = Object.fromEntries(CAR_CONFIGS.map((config) => [config.id, null]))
      for (let i = 0; i <= animationIndex.value && i < animationLegs.value.length; i++) {
        const frame = animationLegs.value[i]
        frame?.moves?.forEach((move) => {
          if (!move?.carId) return
          if (move.carryId !== null && move.carryId !== undefined && String(move.carryId) !== '') {
            carryingByCar[move.carId] = String(move.carryId)
            return
          }
          carryingByCar[move.carId] = null
        })
      }

      CAR_CONFIGS.forEach((config, index) => {
        const carState = currentFrame?.carStates?.[config.id] || getCarHomeState(config)
        const carCell = positions[config.id] || carState.cell
        if (!carCell) return
        const footprint = getCarFootprint(carState.cell, carState.direction)
        const footprintCenters = footprint.map(center)
        const head = footprintCenters[0]
        const tail = footprintCenters[footprintCenters.length - 1]
        const mid = {
          x: (head.x + tail.x) / 2,
          y: (head.y + tail.y) / 2
        }
        const width = Math.abs(head.x - tail.x) + cellW * 0.58
        const height = Math.abs(head.y - tail.y) + cellH * 0.58
        const rectX = mid.x - width / 2
        const rectY = mid.y - height / 2

        ctx.fillStyle = config.color
        ctx.strokeStyle = '#fef08a'
        ctx.lineWidth = 2
        if (ctx.roundRect) {
          ctx.beginPath(); ctx.roundRect(rectX, rectY, width, height, 8); ctx.fill(); ctx.stroke()
        } else {
          ctx.fillRect(rectX, rectY, width, height); ctx.strokeRect(rectX, rectY, width, height)
        }
        ctx.fillStyle = '#111827'
        ctx.beginPath(); ctx.arc(head.x, head.y, 4, 0, Math.PI * 2); ctx.fill()

        const carryingCargoId = carryingByCar[config.id]
        if (carryingCargoId) {
          const labelText = `貨 ${carryingCargoId}`
          ctx.font = 'bold 11px sans-serif'
          const textWidth = ctx.measureText(labelText).width
          const badgeWidth = textWidth + 10
          const badgeHeight = 16
          const badgeX = mid.x - badgeWidth / 2
          const badgeY = mid.y - badgeHeight / 2
          ctx.fillStyle = 'rgba(15,23,42,0.9)'
          ctx.fillRect(badgeX, badgeY, badgeWidth, badgeHeight)
          ctx.strokeStyle = '#f8fafc'
          ctx.lineWidth = 1
          ctx.strokeRect(badgeX, badgeY, badgeWidth, badgeHeight)
          ctx.fillStyle = '#fef08a'
          ctx.fillText(labelText, badgeX + 5, badgeY + 11)
        }

        ctx.fillStyle = '#fef08a'
        ctx.font = '12px sans-serif'
        ctx.fillText(`${config.label}（固定朝向・2格）`, head.x + 8, head.y - 10 + index * 12)
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

    const normalizePositiveInt = (value, fallback, min, max) => {
      const number = Number(value)
      if (!Number.isFinite(number)) return fallback
      return Math.max(min, Math.min(max, Math.trunc(number)))
    }

    const handleOptimizeAllOrders = async () => {
      const result = await optimizeAllOrders(selectedAlgorithms.value, 20)
      if (result) { batchOptimizationResult.value = result; selectedPreview.value = result.results?.[0] || null }
    }
    const handleRandomBenchmark = async () => {
      const seedValue = randomConfig.value.seed
      const result = await runRandomBenchmark({
        algorithms: selectedAlgorithms.value,
        rounds: normalizePositiveInt(randomConfig.value.rounds, 3, 1, 100),
        tasksPerRound: normalizePositiveInt(randomConfig.value.tasksPerRound, 4, 1, 50),
        itemsPerTask: normalizePositiveInt(randomConfig.value.itemsPerTask, 6, 1, 230),
        seed: seedValue === '' || seedValue === null ? null : Number(seedValue)
      })
      if (result) {
        randomBenchmarkResult.value = result
        const firstTask = result.tasks?.[0]
        if (firstTask) selectRandomTaskPreview(firstTask, firstTask.best_algorithm || result.algorithms?.[0])
      }
    }
    const selectPreview = (result) => { selectedPreview.value = result; selectedRandomPreviewKey.value = '' }

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
      selectedAlgorithms, availableAlgorithms, batchOptimizationResult, randomBenchmarkResult, randomConfig, sortedRandomSummaries, randomChartRows, applyingBatches, loading, error,
      animationLegs, animationIndex, isAnimating, simulationEvents, previewCargoCells, currentLegLabel, simCanvasRef,
      handleOptimizeAllOrders, handleRandomBenchmark, selectPreview, selectRandomTaskPreview, isRandomPreviewSelected, getAlgorithmLabel, getTaskStep, getTaskPath, startAnimation, pauseAnimation, resetAnimation, stepForward, stepBackward,
      applyBatchesToWarehouse, startSimulationFromBenchmark
    }
  }
}
</script>

<style scoped>
.benchmark-panel { padding: 20px; background: #f3f4f6; border-radius: 8px; height: 100%; overflow-y: auto; }
.panel-header h2 { margin: 0 0 12px; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; }
.input-section, .best-result, .algorithm-batch-result, .right-sim2d { background: #fff; border-radius: 8px; padding: 12px; }
.form-group { margin-bottom: 12px; }
.algorithm-checkboxes { display: flex; gap: 10px; flex-wrap: wrap; }
.checkbox-label { background: #f3f4f6; padding: 8px 10px; border-radius: 6px; font-weight: 500; }
.result-split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 12px; }
.left-list { display: flex; flex-direction: column; gap: 10px; }
.algorithm-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.batch-summary { margin-top: 6px; display: flex; gap: 12px; font-size: 13px; color: #374151; }
.actions, .sim-controls { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.btn { padding: 10px 12px; border: 0; border-radius: 6px; color: white; cursor: pointer; font-weight: 600; transition: transform .2s, background-color .2s; }
.btn:hover { transform: scale(1.03); }
.btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }
.btn-success { background: #10b981; } .btn-preview { background: #f59e0b; } .btn-apply { background: #111827; } .btn-primary { background: #3b82f6; }
.error-message { color: #dc2626; margin-top: 8px; font-weight: 600; }
.sim-caption, .sim-status { font-size: 13px; color: #4b5563; }
.sim-canvas { width: 100%; background: #0f172a; border-radius: 8px; }
.batch-sequences { margin-top: 8px; border-top: 2px solid #e5e7eb; padding-top: 6px; }
.seq-row { font-size: 12px; color: #334155; margin-bottom: 4px; word-break: break-all; }
.state-log { margin-top: 8px; background: #f8fafc; border-radius: 6px; padding: 6px; max-height: 120px; overflow-y: auto; }
.log-row { font-size: 12px; color: #475569; margin-bottom: 4px; }
.random-benchmark-section { background: #fff; border-radius: 8px; padding: 14px; margin-top: 12px; border: 1px solid #dbeafe; }
.random-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.random-header h3 { margin: 0; font-size: 1.1rem; font-weight: 800; color: #1e3a8a; }
.random-header p { margin: 4px 0 0; color: #475569; font-size: 13px; }
.random-controls { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 10px; margin-top: 12px; }
.random-controls label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 700; color: #334155; }
.random-controls input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 14px; }
.random-results { margin-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.random-best { border-left: 4px solid #3b82f6; }
.random-chart-card { background: #f8fafc; border: 1px solid #dbeafe; border-radius: 8px; padding: 12px; }
.chart-title { font-weight: 800; color: #1e3a8a; margin-bottom: 8px; }
.chart-row { display: grid; grid-template-columns: 150px 1fr 72px 64px; align-items: center; gap: 8px; margin-bottom: 8px; }
.chart-label { font-size: 12px; font-weight: 700; color: #334155; }
.chart-track { height: 18px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }
.chart-bar { height: 100%; background: linear-gradient(90deg, #60a5fa, #2563eb); border-radius: 999px; }
.chart-value, .chart-delta { font-size: 12px; font-weight: 700; color: #334155; text-align: right; }
.chart-delta.best { color: #059669; }
.chart-note { margin: 8px 0 0; color: #475569; font-size: 12px; }
.task-step-cell { display: flex; align-items: center; gap: 6px; justify-content: space-between; }
.step-count { font-weight: 800; color: #111827; }
.btn-mini { border: 0; border-radius: 999px; padding: 4px 8px; background: #dbeafe; color: #1d4ed8; cursor: pointer; font-size: 11px; font-weight: 800; white-space: nowrap; }
.btn-mini.active { background: #2563eb; color: #fff; }
.path-cell { margin-top: 4px; max-width: 180px; color: #64748b; font-size: 11px; line-height: 1.35; word-break: break-all; }
.sim-selection { margin: 0 0 6px; color: #1d4ed8; font-size: 13px; font-weight: 800; }
.summary-table-wrap { overflow-x: auto; border: 1px solid #e5e7eb; border-radius: 8px; }
.task-table-wrap { max-height: 360px; overflow: auto; }
.benchmark-table { width: 100%; border-collapse: collapse; font-size: 12px; background: #fff; }
.benchmark-table th, .benchmark-table td { border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }
.benchmark-table th { background: #eff6ff; color: #1e3a8a; position: sticky; top: 0; z-index: 1; }
.order-cell { max-width: 220px; word-break: break-all; color: #475569; }
@media (max-width: 900px) { .random-header { flex-direction: column; } .random-controls { grid-template-columns: 1fr 1fr; } .chart-row { grid-template-columns: 110px 1fr 58px 52px; } }
@media (max-width: 640px) { .random-controls { grid-template-columns: 1fr; } }
@media (max-width: 1100px) { .result-split { grid-template-columns: 1fr; } }
</style>
