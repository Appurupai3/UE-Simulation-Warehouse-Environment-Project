<template>
  <div class="bg-white/10 backdrop-blur rounded-2xl shadow-2xl p-4 border border-white/10 space-y-4">
    <ThreeScene ref="threeSceneRef" />
    <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-4">
      <OrderExecutionPanel
        :orders="orders"
        :is-executing="isExecuting"
        :execution-status="executionStatus"
        :execution-flows="executionFlows"
        :benchmark-bridge="benchmarkBridge"
        @start-execution="handleStartExecution"
      />
      <ExecutionToolsPanel
        :completed-orders="completedOrders"
        @reset-warehouse="handleResetWarehouse"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ThreeScene from '../ThreeScene/ThreeScene.vue'
import OrderExecutionPanel from './OrderExecutionPanel.vue'
import ExecutionToolsPanel from './ExecutionToolsPanel.vue'

const props = defineProps({
  orders: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['order-complete'])

const threeSceneRef = ref(null)
const completedOrders = ref([])
const benchmarkBridge = ref(null)

const unwrapExposedRef = (maybeRef, fallback) => {
  if (maybeRef && typeof maybeRef === 'object' && 'value' in maybeRef) {
    return maybeRef.value ?? fallback
  }
  return maybeRef ?? fallback
}

const isExecuting = computed(() => unwrapExposedRef(threeSceneRef.value?.isExecuting, false))
const executionStatus = computed(() => unwrapExposedRef(threeSceneRef.value?.executionStatus, ''))
const executionFlows = computed(() => unwrapExposedRef(threeSceneRef.value?.executionFlows, []))

const parseOrderItems = (content) => {
  if (!content) return []
  return content
    .split(/[^0-9]+/)
    .filter(Boolean)
    .map(item => Number(item))
    .filter(item => !Number.isNaN(item))
}

const pushCompletedOrders = (orderTasks, completedOrderIds = []) => {
  if (!completedOrderIds.length) return

  const completed = orderTasks
    .filter(task => completedOrderIds.includes(task.order.id))
    .map(task => ({
      id: task.order.id,
      content: task.order.content,
      time: task.order.time
    }))

  completed.forEach((order) => {
    if (!completedOrders.value.find(existing => existing.id === order.id)) {
      completedOrders.value.unshift(order)
    }
  })

  completedOrderIds.forEach((orderId) => {
    emit('order-complete', orderId)
  })
}

const executeInPairs = async (tasks) => {
  for (let cursor = 0; cursor < tasks.length; cursor += 2) {
    const chunk = tasks.slice(cursor, cursor + 2)
    const result = await threeSceneRef.value.startOrderExecution(chunk)
    pushCompletedOrders(chunk, result?.completedOrderIds || [])
  }
}

const handleStartExecution = async () => {
  if (!threeSceneRef.value || isExecuting.value || props.orders.length === 0) return

  const orderTasks = props.orders.map((order) => ({
    order,
    items: parseOrderItems(order.content)
  }))

  if (benchmarkBridge.value?.source === 'benchmark') {
    await executeInPairs(orderTasks)
    return
  }

  const firstTwo = orderTasks.slice(0, 2)
  const result = await threeSceneRef.value.startOrderExecution(firstTwo)
  pushCompletedOrders(firstTwo, result?.completedOrderIds || [])
}

const handleResetWarehouse = () => {
  threeSceneRef.value?.resetWarehouse?.()
}

onMounted(() => {
  try {
    const raw = localStorage.getItem('benchmark-execution-bridge')
    if (!raw) return
    benchmarkBridge.value = JSON.parse(raw)
  } catch (error) {
    console.error('讀取 benchmark bridge 失敗', error)
    benchmarkBridge.value = null
  }
})

</script>
