<template>
  <div class="bg-white rounded-2xl shadow-xl p-6 mb-6">
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold text-center bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          倉儲訂單系統
        </h1>
        <p class="text-center text-gray-600 mt-2">Order Management System</p>
      </div>

      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2">
          <div class="w-3 h-3 rounded-full" :class="isConnected ? 'bg-green-500' : 'bg-red-500'"></div>
          <span class="text-sm font-medium" :class="isConnected ? 'text-green-600' : 'text-red-600'">
            {{ isConnected ? '已連線' : '未連線' }}
          </span>
        </div>
        <button
          @click="$emit('open-three')"
          class="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-all duration-300 font-medium flex items-center gap-2"
        >
          <span>🎮</span>
          開啟 3D 場景頁面
        </button>
        <button
          @click="$emit('open-benchmark')"
          class="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-all duration-300 font-medium flex items-center gap-2"
        >
          <span>📊</span>
          演算法 Benchmark
        </button>
        <button
          @click="$emit('toggle-connection')"
          :class="isConnected ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'"
          class="px-4 py-2 text-white rounded-lg transition-all duration-300 font-medium"
        >
          {{ isConnected ? '斷開連線' : '連線後端' }}
        </button>
      </div>
    </div>

    <div
      v-if="errorMessage"
      class="mt-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded-lg"
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
