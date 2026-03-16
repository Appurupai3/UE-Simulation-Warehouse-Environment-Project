<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-100 via-white to-indigo-100 p-6">
    <div class="max-w-7xl mx-auto space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-slate-800">客製化倉儲編輯器</h1>
          <p class="text-slate-500">獨立視窗：編輯 15x15 版面並儲存到後端。</p>
        </div>
        <button class="px-4 py-2 rounded-lg bg-slate-700 text-white" @click="goHome">返回訂單系統</button>
      </div>
      <WarehouseLayoutEditor />
    </div>
  </div>
</template>

<script setup>
import WarehouseLayoutEditor from '../components/WarehouseLayoutEditor.vue';

const goHome = () => {
  window.open('/', '_self');
};
</script>
