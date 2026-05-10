<template>
  <div class="rounded-lg bg-gray-100 p-6">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-[-0.02em] text-gray-900">訂單列表</h2>
      <button
        @click="$emit('clear-orders')"
        class="flat-focus h-11 rounded-md bg-red-500 px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-red-600"
      >清空</button>
    </div>

    <div class="max-h-[600px] space-y-3 overflow-y-auto pr-1">
      <div v-if="orders.length === 0" class="rounded-lg bg-white p-8 text-center text-gray-500">
        <p class="text-lg font-semibold">暫無訂單</p>
        <p class="mt-2 text-sm">請在右側建立新訂單</p>
      </div>

      <div
        v-for="order in orders"
        :key="order.id"
        class="group cursor-pointer rounded-lg bg-white p-4 transition-all duration-200 hover:scale-[1.02] hover:bg-blue-50"
      >
        <div class="mb-2 flex items-start justify-between">
          <span class="font-bold text-gray-900">訂單 {{ order.id }}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500">{{ order.time }}</span>
            <button
              @click="$emit('delete-order', order.id)"
              class="flat-focus rounded-md p-1 text-red-500 transition-all duration-200 hover:bg-red-100 hover:text-red-700"
              title="刪除訂單"
            >🗑️</button>
          </div>
        </div>
        <div class="font-mono text-lg font-bold text-blue-600">{{ order.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  orders: { type: Array, default: () => [] }
})
defineEmits(['clear-orders', 'delete-order'])
</script>
