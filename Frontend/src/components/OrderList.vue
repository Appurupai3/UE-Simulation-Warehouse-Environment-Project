<template>
  <div class="ds-card rounded-3xl p-6 lg:p-8">
    <div class="mb-5 flex items-center justify-between gap-3">
      <div>
        <div class="section-label mb-3">
          <span class="section-label__dot" />
          <span class="section-label__text">Live Queue</span>
        </div>
        <h2 class="text-2xl font-semibold tracking-tight text-slate-900">訂單列表</h2>
      </div>
      <button @click="$emit('clear-orders')" class="ds-btn ds-btn--danger">清空</button>
    </div>

    <div class="max-h-[600px] space-y-3 overflow-y-auto pr-1">
      <div v-if="orders.length === 0" class="rounded-2xl border border-dashed border-slate-300 py-12 text-center text-slate-400">
        <p class="text-lg">暫無訂單</p>
        <p class="mt-2 text-sm">請在右側建立新訂單</p>
      </div>

      <div
        v-for="order in orders"
        :key="order.id"
        class="group rounded-2xl border border-blue-100 bg-gradient-to-r from-white to-blue-50 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg"
      >
        <div class="mb-2 flex items-start justify-between gap-3">
          <span class="text-lg font-semibold text-slate-800">訂單 {{ order.id }}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-500">{{ order.time }}</span>
            <button
              @click="$emit('delete-order', order.id)"
              class="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
              title="刪除訂單"
              aria-label="刪除訂單"
            >
              🗑️
            </button>
          </div>
        </div>
        <div class="font-mono text-lg text-blue-700">
          {{ order.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  orders: {
    type: Array,
    default: () => []
  }
})

defineEmits(['clear-orders', 'delete-order'])
</script>
