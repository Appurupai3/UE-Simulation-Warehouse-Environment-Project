<template>
  <div class="relative mb-6 overflow-hidden rounded-lg bg-blue-500 p-6 text-white">
    <div class="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10"></div>
    <div class="absolute -bottom-16 right-24 h-28 w-28 rotate-12 bg-white/10"></div>

    <div class="relative flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
      <div>
        <h1 class="text-3xl font-extrabold tracking-[-0.02em]">倉儲訂單系統</h1>
        <p class="mt-1 text-sm font-medium tracking-wide text-blue-100">ORDER MANAGEMENT SYSTEM</p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-2 rounded-md bg-white/15 px-3 py-2">
          <div class="h-3 w-3 rounded-full" :class="isConnected ? 'bg-emerald-400' : 'bg-amber-400'"></div>
          <span class="text-sm font-semibold">{{ isConnected ? '已連線' : '未連線' }}</span>
        </div>

        <button
          @click="$emit('open-three')"
          class="flat-focus h-12 rounded-md bg-white px-4 text-sm font-semibold text-blue-600 transition-all duration-200 hover:scale-105 hover:bg-blue-50"
        >🎮 3D 場景</button>

        <button
          @click="$emit('open-benchmark')"
          class="flat-focus h-12 rounded-md bg-amber-500 px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-amber-600"
        >📊 Benchmark</button>

        <button
          @click="$emit('toggle-connection')"
          :class="isConnected ? 'bg-gray-900 hover:bg-gray-800' : 'bg-emerald-500 hover:bg-emerald-600'"
          class="flat-focus h-12 rounded-md px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105"
        >{{ isConnected ? '斷開連線' : '連線後端' }}</button>
      </div>
    </div>

    <p v-if="errorMessage" class="relative mt-4 rounded-md bg-white px-4 py-3 text-sm font-medium text-red-600">
      {{ errorMessage }}
    </p>
  </div>
</template>

<script setup>
const { isConnected, errorMessage } = defineProps({
  isConnected: { type: Boolean, required: true },
  errorMessage: { type: String, default: '' }
})
defineEmits(['open-three', 'toggle-connection', 'open-benchmark'])
</script>
