<template>
  <div class="ds-card rounded-3xl p-6 lg:p-8">
    <div class="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <div class="section-label mb-3">
          <span class="section-label__dot" />
          <span class="section-label__text">Control Center</span>
        </div>
        <h2 class="font-[Calistoga] text-3xl text-slate-900 md:text-4xl">
          倉儲作業 <span class="gradient-text">控制台</span>
        </h2>
        <p class="mt-2 text-sm text-slate-500 md:text-base">Order Management System</p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div
          class="inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium"
          :class="isConnected ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'"
        >
          <span class="h-2 w-2 rounded-full" :class="isConnected ? 'bg-emerald-500' : 'bg-rose-500'" />
          {{ isConnected ? '已連線' : '未連線' }}
        </div>

        <button @click="$emit('open-three')" class="ds-btn ds-btn--secondary">
          🎮 3D 場景
        </button>

        <button @click="$emit('open-benchmark')" class="ds-btn ds-btn--secondary">
          📊 Benchmark
        </button>

        <button
          @click="$emit('toggle-connection')"
          :class="isConnected ? 'ds-btn ds-btn--danger' : 'ds-btn ds-btn--primary'"
        >
          {{ isConnected ? '斷開連線' : '連線後端' }}
        </button>
      </div>
    </div>

    <div
      v-if="errorMessage"
      class="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
    >
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup>
const { isConnected, errorMessage } = defineProps({
  isConnected: {
    type: Boolean,
    required: true
  },
  errorMessage: {
    type: String,
    default: ''
  }
})

defineEmits(['open-three', 'toggle-connection', 'open-benchmark'])
</script>
