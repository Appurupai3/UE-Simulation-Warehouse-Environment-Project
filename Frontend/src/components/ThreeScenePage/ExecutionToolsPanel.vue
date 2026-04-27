<template>
  <div class="rounded-lg bg-gray-800 p-4 space-y-4">
    <div>
      <h2 class="text-lg font-semibold">功能列表</h2>
      <p class="text-xs text-white/60">常用操作與完成紀錄</p>
    </div>

    <button
      class="w-full px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 bg-amber-500 hover:bg-amber-600 text-white"
      @click="$emit('reset-warehouse')"
    >
      🔄 重製倉庫
    </button>

    <div class="space-y-2">
      <div class="text-sm font-semibold text-white/80">已完成清單</div>
      <div v-if="completedOrders.length === 0" class="text-sm text-white/50">
        尚無完成訂單
      </div>
      <div
        v-for="order in completedOrders"
        :key="order.id"
        class="rounded-md bg-gray-700 px-3 py-2 text-sm"
      >
        <div class="flex items-center justify-between">
          <span>訂單 {{ order.id }}</span>
          <span class="text-xs text-white/50">{{ order.time }}</span>
        </div>
        <div class="text-xs text-white/70 mt-1">{{ order.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  completedOrders: {
    type: Array,
    default: () => []
  }
})

defineEmits(['reset-warehouse'])
</script>
