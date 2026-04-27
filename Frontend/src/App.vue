<template>
  <div class="minimalist-shell">
    <div class="mx-auto max-w-6xl space-y-8">
      <section class="ds-card relative overflow-hidden px-6 py-10 lg:px-10 lg:py-14">
        <div class="absolute -right-20 -top-20 h-52 w-52 rounded-full bg-blue-400/20 blur-3xl" />
        <div class="grid items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div class="space-y-5">
            <div class="section-label">
              <span class="section-label__dot" />
              <span class="section-label__text">Warehouse Control</span>
            </div>
            <h1 class="font-[Calistoga] text-[2.75rem] leading-[1.05] text-slate-900 md:text-6xl lg:text-[5.25rem]">
              智慧倉儲訂單
              <span class="gradient-text">即時調度</span>
            </h1>
            <p class="max-w-2xl text-base leading-relaxed text-slate-500 md:text-lg">
              透過一致化設計語彙管理訂單、監控連線、快速切換 3D 場景與 benchmark。
              整體介面採用 Minimalist Modern 風格，將重點互動集中在高辨識度藍色漸層。
            </p>
          </div>

          <div class="relative hidden min-h-[320px] lg:block">
            <div class="hero-visual-ring absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-blue-300/70" />
            <div class="hero-floating absolute right-8 top-8 w-44 rounded-2xl border border-slate-200 bg-white p-4 shadow-xl">
              <p class="text-xs uppercase tracking-[0.15em] text-slate-500">Queue</p>
              <p class="mt-2 text-3xl font-semibold text-slate-900">{{ orders.length }}</p>
            </div>
            <div class="hero-floating hero-floating--alt absolute bottom-8 left-4 w-52 rounded-2xl bg-gradient-to-br from-[#0052FF] to-[#4D7CFF] p-5 text-white shadow-[var(--shadow-accent-lg)]">
              <p class="text-xs uppercase tracking-[0.15em] text-blue-100">Preview</p>
              <p class="mt-3 font-mono text-lg">{{ orderPreview }}</p>
            </div>
          </div>
        </div>
      </section>

      <HeaderControls
        :is-connected="isConnected"
        :error-message="errorMessage"
        @open-three="openThreeScene"
        @open-benchmark="openBenchmark"
        @toggle-connection="toggleConnection"
      />

      <section class="inverted-panel ds-card rounded-3xl px-6 py-6 lg:px-10">
        <div class="relative z-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p class="text-xs uppercase tracking-[0.16em] text-blue-200">Connection</p>
            <p class="mt-2 text-3xl font-semibold">{{ isConnected ? 'Online' : 'Offline' }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.16em] text-blue-200">Orders</p>
            <p class="mt-2 text-3xl font-semibold">{{ orders.length }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.16em] text-blue-200">Input Count</p>
            <p class="mt-2 text-3xl font-semibold">{{ numbers.length }}</p>
          </div>
          <div>
            <p class="text-xs uppercase tracking-[0.16em] text-blue-200">Ready State</p>
            <p class="mt-2 text-3xl font-semibold">{{ numbers.length > 0 ? 'Ready' : 'Idle' }}</p>
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 gap-6 xl:grid-cols-2">
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
      </section>
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

const openThreeScene = () => {
  window.open('/three.html', '_blank')
}

const openBenchmark = () => {
  window.open('/benchmark.html', '_blank')
}

const submitOrder = () => {
  if (numbers.value.length === 0) return

  const orderContent = numbers.value.join('-')

  if (isConnected.value) {
    sendOrder(orderContent)
    clearNumbers()
  } else {
    addLocalOrder(orderContent)
    clearNumbers()
  }
}

const handleClearOrders = () => {
  if (!isConnected.value) {
    errorMessage.value = '請先連線到後端再清空訂單，否則無法刪除後端資料，刷新後訂單會恢復。'
    return
  }

  if (confirm('確定要清空所有訂單嗎？')) {
    requestClearOrders()
  }
}

const handleDeleteOrder = (orderId) => {
  if (!isConnected.value) {
    errorMessage.value = '請先連線到後端再刪除訂單，否則無法刪除後端資料。'
    return
  }

  if (confirm(`確定要刪除訂單 ${orderId} 嗎？`)) {
    requestDeleteOrder(orderId)
  }
}

const handleUpdateNumber = (index, value) => {
  updateNumber(index, value)
}

const handleApplyCode = (value) => {
  applyCodeInput(value)
}

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
input[type='number']::-webkit-inner-spin-button,
input[type='number']::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type='number'] {
  -moz-appearance: textfield;
}

.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.18);
  border-radius: 10px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(51, 65, 85, 0.45);
  border-radius: 10px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(15, 23, 42, 0.75);
}
</style>
