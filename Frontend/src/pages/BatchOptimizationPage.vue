<template>
  <div class="batch-optimization-page">
    <div class="page-header">
      <h1>🚗 批次優化實時比較</h1>
      <button @click="goBack" class="btn-back">← 返回 Benchmark</button>
    </div>
    
    <div class="control-panel">
      <div class="info-section">
        <p><strong>來源訂單數:</strong> {{ sourceOrders.length }}</p>
        <p><strong>總項目數:</strong> {{ totalItems }}</p>
        <p><strong>演算法數:</strong> {{ algorithms.length }}</p>
      </div>
      
      <button 
        @click="startSimulation" 
        :disabled="isSimulating"
        class="btn-start"
      >
        {{ isSimulating ? '模擬中...' : '🚀 開始實時模擬' }}
      </button>
    </div>
    
    <div class="scenes-grid" :class="'grid-' + algorithms.length">
      <div 
        v-for="algo in algorithms" 
        :key="algo.name"
        class="scene-container"
      >
        <div class="scene-header">
          <h3>{{ algo.label }}</h3>
          <div class="scene-stats">
            <span class="stat">批次: {{ algo.batches?.length || 0 }}</span>
            <span class="stat" :class="{ 'highlight': algo.actualSteps }">
              步數: {{ algo.actualSteps || algo.theoreticalSteps || '計算中...' }}
              <span v-if="algo.actualSteps" class="badge">實測</span>
              <span v-else-if="algo.theoreticalSteps" class="badge theory">理論</span>
            </span>
            <span class="stat">狀態: {{ algo.status || '待命' }}</span>
          </div>
        </div>
        <div class="scene-wrapper">
          <iframe 
            :ref="el => setSceneRef(algo.name, el)"
            :src="'/three.html?algorithm=' + algo.name + '&autoStart=false'"
            class="scene-iframe"
          ></iframe>
        </div>
      </div>
    </div>
    
    <div v-if="winner" class="winner-banner">
      🏆 最佳演算法: {{ winner.label }} - {{ winner.actualSteps }} 步
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const sourceOrders = ref([])
const totalItems = ref(0)
const algorithms = ref([
  { name: 'original', label: '原始順序（不整理）', batches: [], theoreticalSteps: 0, actualSteps: 0, status: '待命' },
  { name: 'greedy', label: '貪婪演算法', batches: [], theoreticalSteps: 0, actualSteps: 0, status: '待命' },
  { name: 'sequential', label: '順序演算法', batches: [], theoreticalSteps: 0, actualSteps: 0, status: '待命' },
  { name: 'reverse', label: '反向順序演算法', batches: [], theoreticalSteps: 0, actualSteps: 0, status: '待命' }
])

const isSimulating = ref(false)
const sceneRefs = ref({})

const winner = computed(() => {
  const completed = algorithms.value.filter(a => a.actualSteps > 0)
  if (completed.length === 0) return null
  
  return completed.reduce((best, current) => {
    return current.actualSteps < best.actualSteps ? current : best
  })
})

const setSceneRef = (algoName, el) => {
  if (el) {
    sceneRefs.value[algoName] = el
  }
}

const goBack = () => {
  router.push('/benchmark.html')
}

const startSimulation = async () => {
  isSimulating.value = true
  
  try {
    // 1. 獲取批次優化結果
    const response = await fetch('http://localhost:8000/api/benchmark/optimize-orders', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        algorithms: algorithms.value.map(a => a.name),
        max_items_per_batch: 20
      })
    })
    
    const result = await response.json()
    
    // 2. 更新理論步數和批次資訊
    result.results.forEach(algoResult => {
      const algo = algorithms.value.find(a => a.name === algoResult.algorithm_name)
      if (algo) {
        algo.batches = algoResult.batches
        algo.theoreticalSteps = algoResult.total_steps
        algo.status = '準備中'
      }
    })
    
    // 3. 為每個演算法創建訂單並開始模擬
    const simulationPromises = algorithms.value.map(async (algo) => {
      try {
        algo.status = '清除舊訂單'
        
        // 清除訂單
        await fetch('http://localhost:8000/orders', { method: 'DELETE' })
        
        // 等待一下讓場景同步
        await new Promise(resolve => setTimeout(resolve, 500))
        
        algo.status = '創建批次訂單'
        
        // 創建批次訂單
        for (const batch of algo.batches) {
          await fetch('http://localhost:8000/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              content: batch.items.join('-'),
              items: batch.items
            })
          })
        }
        
        algo.status = '執行中'
        
        // 通知 iframe 開始執行
        const iframe = sceneRefs.value[algo.name]
        if (iframe && iframe.contentWindow) {
          iframe.contentWindow.postMessage({
            type: 'START_EXECUTION',
            algorithm: algo.name
          }, '*')
        }
        
        // 監聽執行完成
        return new Promise((resolve) => {
          const handleMessage = (event) => {
            if (event.data.type === 'EXECUTION_COMPLETE' && event.data.algorithm === algo.name) {
              algo.actualSteps = event.data.totalSteps
              algo.status = '完成'
              window.removeEventListener('message', handleMessage)
              resolve()
            }
          }
          window.addEventListener('message', handleMessage)
        })
        
      } catch (err) {
        console.error(`演算法 ${algo.name} 模擬失敗:`, err)
        algo.status = '失敗'
      }
    })
    
    // 等待所有模擬完成
    await Promise.all(simulationPromises)
    
  } catch (err) {
    console.error('批次優化模擬失敗:', err)
    alert(`模擬失敗: ${err.message}`)
  } finally {
    isSimulating.value = false
  }
}

onMounted(async () => {
  // 載入訂單資訊
  try {
    const response = await fetch('http://localhost:8000/orders?limit=100')
    const data = await response.json()
    sourceOrders.value = data.orders || []
    
    const allItems = new Set()
    sourceOrders.value.forEach(order => {
      order.items?.forEach(item => allItems.add(item))
    })
    totalItems.value = allItems.size
  } catch (err) {
    console.error('載入訂單失敗:', err)
  }
})
</script>

<style scoped>
.batch-optimization-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  color: white;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 32px;
}

.btn-back {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid white;
  border-radius: 8px;
  color: white;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateX(-5px);
}

.control-panel {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-section p {
  margin: 5px 0;
  font-size: 16px;
}

.btn-start {
  padding: 15px 40px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border: none;
  border-radius: 50px;
  color: white;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.btn-start:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.btn-start:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.scenes-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 20px;
}

.grid-2 {
  grid-template-columns: repeat(2, 1fr);
}

.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.grid-4 {
  grid-template-columns: repeat(2, 1fr);
}

.scene-container {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.scene-header {
  padding: 15px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid rgba(255, 255, 255, 0.1);
}

.scene-header h3 {
  margin: 0 0 10px 0;
  font-size: 20px;
}

.scene-stats {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.stat {
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.stat.highlight {
  background: rgba(76, 175, 80, 0.3);
  border: 1px solid #4caf50;
}

.badge {
  padding: 2px 8px;
  background: #4caf50;
  border-radius: 10px;
  font-size: 11px;
  font-weight: bold;
}

.badge.theory {
  background: #ff9800;
}

.scene-wrapper {
  width: 100%;
  height: 500px;
  position: relative;
}

.scene-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.winner-banner {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  padding: 20px 40px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-radius: 50px;
  font-size: 24px;
  font-weight: bold;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateX(-50%) translateY(0);
  }
  50% {
    transform: translateX(-50%) translateY(-10px);
  }
}
</style>
