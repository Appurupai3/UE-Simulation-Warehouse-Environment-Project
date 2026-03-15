<template>
  <div class="bg-white/10 backdrop-blur rounded-2xl border border-white/10 p-4 shadow-xl space-y-4">
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
        {{ isExecuting ? '執行中...' : '開始執行' }}
      </button>
    </div>

    <div
      v-if="executionStatus"
      class="rounded-lg bg-white/10 px-3 py-2 text-sm text-white/80"
    >
      {{ executionStatus }}
    </div>

    <div v-if="executionFlows.length > 0" class="space-y-3 rounded-xl border border-white/10 bg-white/5 p-3">
      <h3 class="text-sm font-semibold text-white/90">車輛執行流程圖（執行訂單時產生）</h3>
      <div
        v-for="flow in executionFlows"
        :key="flow.id"
        class="rounded-lg border border-white/10 bg-slate-900/50 p-3"
      >
        <div class="mb-2 text-xs text-white/70">
          {{ flow.carId }} · 訂單 {{ flow.orderId }} · 目標 {{ flow.shippingLabel }}
        </div>
        <div class="flow-track">
          <template v-for="(step, index) in flow.steps" :key="`${flow.id}-${step.key}`">
            <div class="flow-step">
              <span class="flow-index">{{ index + 1 }}</span>
              <span class="flow-label">{{ step.label }}</span>
            </div>
            <span v-if="index < flow.steps.length - 1" class="flow-arrow">→</span>
          </template>
        </div>
      </div>
    </div>

    <div class="space-y-3 max-h-[420px] overflow-y-auto pr-2">
      <div v-if="orders.length === 0" class="text-center text-white/60 py-8">
        暫無訂單
      </div>

      <div
        v-for="order in orders"
        :key="order.id"
        class="rounded-xl border border-white/10 bg-white/5 px-4 py-3"
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
  }
})

defineEmits(['start-execution'])

const buttonClass = computed(() => {
  if (props.orders.length === 0) {
    return 'bg-white/10 text-white/40 cursor-not-allowed'
  }
  if (props.isExecuting) {
    return 'bg-indigo-500/60 text-white cursor-wait'
  }
  return 'bg-indigo-500 hover:bg-indigo-400 text-white'
})
</script>

<style scoped>
.flow-track {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
  gap: 6px;
  align-items: center;
}

.flow-step {
  min-height: 52px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 10px;
  background: rgba(30, 41, 59, 0.7);
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.flow-index {
  width: 20px;
  height: 20px;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #22d3ee, #6366f1);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
}

.flow-label {
  font-size: 0.75rem;
  color: #f8fafc;
  line-height: 1.35;
}

.flow-arrow {
  color: #94a3b8;
  font-size: 1.1rem;
  font-weight: 700;
}

@media (max-width: 1280px) {
  .flow-track {
    grid-template-columns: 1fr;
  }

  .flow-arrow {
    justify-self: center;
    transform: rotate(90deg);
  }
}
</style>
