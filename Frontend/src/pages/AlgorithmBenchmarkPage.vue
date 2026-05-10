<template>
  <div class="min-h-screen bg-gray-100 text-gray-900">
    <header class="bg-blue-500 px-6 py-8 text-white md:px-10">
      <div class="mx-auto max-w-7xl">
        <h1 class="text-4xl font-extrabold tracking-[-0.02em]">演算法 Benchmark 測試</h1>
        <p class="mt-2 text-sm font-medium text-blue-100">用圖像化方式比較演算法，並直接銜接到 3D 模擬</p>
      </div>
    </header>

    <div class="mx-auto max-w-7xl p-6 md:p-8">
      <BenchmarkPanel />
    </div>
  </div>
</template>

<script>
import BenchmarkPanel from '../components/AlgorithmBenchmark/BenchmarkPanel.vue'
export default { name: 'AlgorithmBenchmarkPage', components: { BenchmarkPanel } }
</script>
