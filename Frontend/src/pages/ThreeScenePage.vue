<template>
  <div class="min-h-screen bg-gray-900 p-6 text-white">
    <div class="mx-auto max-w-7xl space-y-6">
      <PageHeader @open-guide="openGuide" @go-home="goHome" />
      <SceneContainer :orders="orders" @order-complete="handleOrderComplete" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import PageHeader from '../components/ThreeScenePage/PageHeader.vue'
import SceneContainer from '../components/ThreeScenePage/SceneContainer.vue'
import { useWebSocket } from '../composables/useWebSocket'

const { isConnected, orders, connectWebSocket, disconnectWebSocket, requestDeleteOrder, removeLocalOrder } = useWebSocket()

const goHome = () => window.open('/', '_self')
const openGuide = () => alert('🖱️ 左鍵拖曳旋轉\n🖱️ 滾輪縮放\n建議於桌機上使用以獲得最佳體驗。')
const handleOrderComplete = (orderId) => isConnected.value ? requestDeleteOrder(orderId) : removeLocalOrder(orderId)

onMounted(connectWebSocket)
onUnmounted(disconnectWebSocket)
</script>
