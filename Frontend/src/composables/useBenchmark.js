import { ref, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from './useWebSocket'

export function useBenchmark() {
  const results = ref([])
  const history = ref([])
  const loading = ref(false)
  const error = ref(null)

  const API_BASE = 'http://localhost:8000/api'
  
  // WebSocket 連線
  const { isConnected, sendMessage } = useWebSocket()

  /**
   * 執行 Benchmark 測試
   * @param {Object} order - 訂單物件 { items: [75, 12, 43] }
   * @param {Array<string>} algorithms - 演算法名稱列表
   */
  const runBenchmark = async (order, algorithms) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/benchmark/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          order,
          algorithms
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      results.value = [result, ...results.value]
      return result
    } catch (err) {
      error.value = `執行 Benchmark 失敗: ${err.message}`
      console.error('執行 Benchmark 失敗:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 獲取歷史結果
   * @param {number} limit - 返回結果數量限制
   * @param {string} algorithm - 演算法名稱過濾器（可選）
   */
  const getHistory = async (limit = 50, algorithm = null) => {
    loading.value = true
    error.value = null
    
    try {
      let url = `${API_BASE}/benchmark/history?limit=${limit}`
      if (algorithm) {
        url += `&algorithm=${algorithm}`
      }
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      history.value = await response.json()
      return history.value
    } catch (err) {
      error.value = `獲取歷史結果失敗: ${err.message}`
      console.error('獲取歷史結果失敗:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * 批次優化所有訂單
   * @param {Array<string>} algorithms - 演算法名稱列表
   * @param {number} maxItemsPerBatch - 每批次最大項目數
   */
  const optimizeAllOrders = async (algorithms = ['original', 'greedy', 'sequential', 'reverse'], maxItemsPerBatch = 20) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/benchmark/optimize-orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          algorithms,
          max_items_per_batch: maxItemsPerBatch
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      return result
    } catch (err) {
      error.value = `批次優化失敗: ${err.message}`
      console.error('批次優化失敗:', err)
      return null
    } finally {
      loading.value = false
    }
  }


  /**
   * 使用 random 產生多局、多任務 Benchmark
   * @param {Object} config - { algorithms, rounds, tasksPerRound, itemsPerTask, seed }
   */
  const runRandomBenchmark = async ({
    algorithms = ['original', 'greedy', 'astar', 'obstacle_aware'],
    rounds = 3,
    tasksPerRound = 4,
    itemsPerTask = 6,
    seed = null
  } = {}) => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/benchmark/random`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          algorithms,
          rounds,
          tasks_per_round: tasksPerRound,
          items_per_task: itemsPerTask,
          seed
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (err) {
      error.value = `隨機 Benchmark 失敗: ${err.message}`
      console.error('隨機 Benchmark 失敗:', err)
      return null
    } finally {
      loading.value = false
    }
  }


  return {
    results,
    history,
    loading,
    error,
    runBenchmark,
    getHistory,
    optimizeAllOrders,
    runRandomBenchmark
  }
}
