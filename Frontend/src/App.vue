<template>
  <div class="min-h-screen bg-white">
    <div class="mx-auto max-w-7xl px-4 py-8 md:px-8">
      <HeaderControls
        :is-connected="isConnected"
        :error-message="errorMessage"
        @open-three="openThreeScene"
        @open-benchmark="openBenchmark"
        @toggle-connection="toggleConnection"
      />

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <OrderList
          :orders="orders"
          @clear-orders="handleClearOrders"
          @delete-order="handleDeleteOrder"
        />

        <OrderForm
          :numbers="numbers"
          :order-preview="orderPreview"
          @add-number="addNumber"
          @update-number="handleUpdateNumber"
          @remove-number="removeNumber"
          @clear-numbers="clearNumbers"
          @add-multiple="addMultipleNumbers"
          @validate-number="validateNumber"
          @generate-random="generateRandom"
          @apply-code="handleApplyCode"
          @submit-order="submitOrder"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import HeaderControls from './components/HeaderControls.vue'
import OrderList from './components/OrderList.vue'
import OrderForm from './components/OrderForm.vue'
import { useOrderNumbers } from './composables/useOrderNumbers'
import { useWebSocket } from './composables/useWebSocket'

const {
  numbers,
  orderPreview,
  addNumber,
  updateNumber,
  removeNumber,
  clearNumbers,
  addMultipleNumbers,
  validateNumber,
  generateRandom,
  applyCodeInput
} = useOrderNumbers()

const {
  isConnected,
  errorMessage,
  orders,
  connectWebSocket,
  disconnectWebSocket,
  toggleConnection,
  sendOrder,
  requestClearOrders,
  requestDeleteOrder,
  addLocalOrder
} = useWebSocket()

const openThreeScene = () => window.open('/three.html', '_blank')
const openBenchmark = () => window.open('/benchmark.html', '_blank')

const submitOrder = () => {
  if (numbers.value.length === 0) return
  const orderContent = numbers.value.join('-')
  if (isConnected.value) sendOrder(orderContent)
  else addLocalOrder(orderContent)
  clearNumbers()
}

const handleClearOrders = () => {
  if (!isConnected.value) {
    errorMessage.value = '請先連線到後端再清空訂單，否則無法刪除後端資料，刷新後訂單會恢復。'
    return
  }
  if (confirm('確定要清空所有訂單嗎？')) requestClearOrders()
}

const handleDeleteOrder = (orderId) => {
  if (!isConnected.value) {
    errorMessage.value = '請先連線到後端再刪除訂單，否則無法刪除後端資料。'
    return
  }
  if (confirm(`確定要刪除訂單 ${orderId} 嗎？`)) requestDeleteOrder(orderId)
}

const handleUpdateNumber = (index, value) => updateNumber(index, value)
const handleApplyCode = (value) => applyCodeInput(value)

onMounted(connectWebSocket)
onUnmounted(disconnectWebSocket)
</script>
