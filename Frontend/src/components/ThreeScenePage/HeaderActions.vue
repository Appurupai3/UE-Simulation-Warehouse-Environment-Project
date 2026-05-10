<template>
  <div class="flex flex-wrap gap-3">
    <button
      @click="$emit('open-guide')"
      class="flat-focus h-12 rounded-md bg-blue-500 px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-blue-600"
    >
      操作說明
    </button>
    <button
      @click="$emit('go-home')"
      class="flat-focus h-12 rounded-md bg-emerald-500 px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-emerald-600"
    >
      返回訂單系統
    </button>
  </div>
</template>

<script setup>
defineEmits(['open-guide', 'go-home'])
</script>
