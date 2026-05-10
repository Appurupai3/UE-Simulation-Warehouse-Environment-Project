<template>
  <div class="rounded-lg bg-white p-6">
    <h2 class="mb-4 text-2xl font-bold tracking-[-0.02em] text-gray-900">訂單發送</h2>

    <div class="mb-6">
      <label class="mb-2 block text-sm font-semibold uppercase tracking-wider text-gray-700">輸入數字</label>
      <div class="flex min-h-[120px] flex-wrap gap-2 rounded-lg bg-gray-100 p-4">
        <div
          v-for="(num, index) in numbers"
          :key="`${num}-${index}`"
          class="flex items-center gap-2 rounded-md bg-white px-4 py-2"
        >
          <input
            :value="num"
            type="number"
            class="flat-focus w-20 rounded-md bg-gray-100 px-2 py-1 text-center text-lg font-bold text-blue-600"
            min="1"
            max="999"
            @input="$emit('update-number', index, $event.target.value ? Number($event.target.value) : 0)"
            @blur="$emit('validate-number', index)"
          />
          <button @click="$emit('remove-number', index)" class="flat-focus font-bold text-red-500 hover:text-red-700">✕</button>
        </div>

        <button
          @click="$emit('add-number')"
          class="flat-focus h-11 rounded-md bg-emerald-500 px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-emerald-600"
        >+ 新增</button>
      </div>
    </div>

    <div class="mb-6">
      <label class="mb-2 block text-sm font-semibold uppercase tracking-wider text-gray-700">代碼輸入</label>
      <div class="flex flex-wrap gap-2">
        <input v-model="codeInput" type="text" class="flat-focus h-12 min-w-[220px] flex-1 rounded-md border-2 border-gray-200 bg-gray-100 px-3"
          placeholder="例如 60-70-80-90" />
        <button @click="applyCode(codeInput)" class="flat-focus h-12 rounded-md bg-blue-500 px-4 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-blue-600">套用代碼</button>
      </div>
    </div>

    <div class="mb-6 rounded-lg bg-amber-100 p-4 text-center">
      <p class="mb-2 text-sm font-semibold uppercase tracking-wider text-amber-700">訂單預覽</p>
      <div class="text-2xl font-bold text-gray-900">{{ orderPreview }}</div>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <button @click="$emit('generate-random')" class="flat-focus h-14 rounded-md bg-amber-500 text-lg font-bold text-white transition-all duration-200 hover:scale-105 hover:bg-amber-600">🎲 隨機數字</button>
      <button @click="$emit('submit-order')" :disabled="numbers.length === 0" class="flat-focus h-14 rounded-md bg-blue-500 text-lg font-bold text-white transition-all duration-200 hover:scale-105 hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-gray-400">📤 送出訂單</button>
    </div>

    <div class="mt-6 border-t-2 border-gray-200 pt-6">
      <label class="mb-3 block text-sm font-semibold uppercase tracking-wider text-gray-700">快速操作</label>
      <div class="flex flex-wrap gap-2">
        <button @click="$emit('clear-numbers')" class="flat-focus h-11 rounded-md bg-gray-200 px-4 text-sm font-semibold text-gray-800 transition-all duration-200 hover:scale-105 hover:bg-gray-300">清空數字</button>
        <button @click="$emit('add-multiple', 3)" class="flat-focus h-11 rounded-md bg-blue-100 px-4 text-sm font-semibold text-blue-700 transition-all duration-200 hover:scale-105 hover:bg-blue-200">新增3個</button>
        <button @click="$emit('add-multiple', 5)" class="flat-focus h-11 rounded-md bg-emerald-100 px-4 text-sm font-semibold text-emerald-700 transition-all duration-200 hover:scale-105 hover:bg-emerald-200">新增5個</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
defineProps({ numbers: { type: Array, default: () => [] }, orderPreview: { type: String, default: '' } })
const emit = defineEmits(['add-number', 'update-number', 'remove-number', 'clear-numbers', 'add-multiple', 'validate-number', 'generate-random', 'apply-code', 'submit-order'])
const codeInput = ref('')
const applyCode = (value) => { if (!value) return; emit('apply-code', value); codeInput.value = '' }
</script>
