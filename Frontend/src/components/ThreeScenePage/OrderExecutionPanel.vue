<template>
  <div class="rounded-lg bg-gray-800 p-4 space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold">訂單清單</h2>
        <p class="text-xs text-white/60">出貨區：X1Y1、X4Y1</p>
      </div>
      <button
        class="px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200"
        :class="buttonClass"
        :disabled="isExecuting || orders.length === 0"
        @click="$emit('start-execution')"
      >
        {{ buttonLabel }}
      </button>
    </div>

    <div
      v-if="benchmarkBridge"
      class="rounded-md bg-blue-500 px-3 py-2 text-sm text-white"
    >
      <p class="font-semibold">Benchmark 銜接模式</p>
      <p>演算法：{{ benchmarkBridge.algorithm }} / 預估總步數：{{ benchmarkBridge.totalSteps }}</p>
      <p>批次：{{ benchmarkBridge.totalBatches }}（系統會每次取 2 筆並連續執行）</p>
    </div>

    <div
      v-if="executionStatus"
      class="rounded-md bg-gray-700 px-3 py-2 text-sm text-gray-100"
    >
      {{ executionStatus }}
    </div>

    <div v-if="executionFlows.length > 0" class="space-y-2">
      <div
        v-for="flow in executionFlows"
        :key="flow.id"
        class="rounded-md bg-gray-700 px-3 py-2 text-sm text-gray-100"
      >
        {{ flow.carId }}：{{ flow.status }}
      </div>
    </div>

    <div class="space-y-3 max-h-[420px] overflow-y-auto pr-2">
      <div v-if="orders.length === 0" class="text-center text-white/60 py-8">
        暫無訂單
      </div>

      <div
        v-for="order in orders"
        :key="order.id"
        class="rounded-lg bg-gray-700 px-4 py-3 transition-all duration-200 hover:scale-[1.02] hover:bg-gray-600"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold">訂單 {{ order.id }}</span>
          <span class="text-xs text-white/50">{{ order.time }}</span>
        </div>
        <div class="mt-2 text-lg font-mono text-indigo-100">
          {{ order.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  orders: {
    type: Array,
    default: () => []
  },
  isExecuting: {
    type: Boolean,
    default: false
  },
  executionStatus: {
    type: String,
    default: ''
  },
  executionFlows: {
    type: Array,
    default: () => []
  },
  benchmarkBridge: {
    type: Object,
    default: null
  }
})

defineEmits(['start-execution'])

const buttonClass = computed(() => {
  if (props.orders.length === 0) {
    return 'bg-gray-600 text-gray-300 cursor-not-allowed'
  }
  if (props.isExecuting) {
    return 'bg-blue-400 text-white cursor-wait'
  }
  return 'bg-blue-500 hover:bg-blue-600 text-white'
})

const buttonLabel = computed(() => {
  if (props.isExecuting) return '執行中...'
  return props.benchmarkBridge ? '開始執行 Benchmark 批次' : '開始執行'
})
</script>
