<template>
  <div class="ds-card rounded-3xl p-6 lg:p-8">
    <div class="section-label mb-4">
      <span class="section-label__dot" />
      <span class="section-label__text">Compose Order</span>
    </div>
    <h2 class="mb-6 text-2xl font-semibold tracking-tight text-slate-900">訂單發送</h2>

    <div class="mb-6">
      <label class="mb-2 block text-sm font-medium text-slate-700">輸入數字</label>
      <div class="min-h-[120px] rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
        <div class="flex flex-wrap gap-2">
          <div
            v-for="(num, index) in numbers"
            :key="`${num}-${index}`"
            class="group flex items-center gap-2 rounded-xl border border-blue-200 bg-white px-3 py-2 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
          >
            <input
              :value="num"
              type="number"
              class="w-20 border-none bg-transparent text-center text-lg font-semibold text-blue-700 focus:outline-none"
              min="1"
              max="999"
              @input="$emit('update-number', index, $event.target.value ? Number($event.target.value) : 0)"
              @blur="$emit('validate-number', index)"
            />
            <button
              @click="$emit('remove-number', index)"
              class="rounded-md px-2 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
              aria-label="刪除數字"
            >
              ✕
            </button>
          </div>

          <button @click="$emit('add-number')" class="ds-btn ds-btn--primary">
            + 新增
          </button>
        </div>
      </div>
    </div>

    <div class="mb-6">
      <label class="mb-2 block text-sm font-medium text-slate-700">代碼輸入</label>
      <div class="flex flex-col gap-3 sm:flex-row">
        <input
          v-model="codeInput"
          type="text"
          class="ds-input min-w-[220px] flex-1"
          placeholder="例如 60-70-80-90"
        />
        <button @click="applyCode(codeInput)" class="ds-btn ds-btn--secondary">
          套用代碼
        </button>
      </div>
    </div>

    <div class="mb-6">
      <label class="mb-2 block text-sm font-medium text-slate-700">訂單預覽</label>
      <div class="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-100 p-4 text-center">
        <div class="font-mono text-2xl font-semibold text-blue-700">
          {{ orderPreview }}
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <button @click="$emit('generate-random')" class="ds-btn ds-btn--secondary h-14">
        🎲 隨機數字
      </button>

      <button
        @click="$emit('submit-order')"
        :disabled="numbers.length === 0"
        class="ds-btn ds-btn--primary h-14"
      >
        📤 送出訂單
      </button>
    </div>

    <div class="mt-6 border-t border-slate-200 pt-6">
      <label class="mb-3 block text-sm font-medium text-slate-700">快速操作</label>
      <div class="flex flex-wrap gap-2">
        <button @click="$emit('clear-numbers')" class="ds-btn ds-btn--secondary">清空數字</button>
        <button @click="$emit('add-multiple', 3)" class="ds-btn ds-btn--secondary">新增 3 個</button>
        <button @click="$emit('add-multiple', 5)" class="ds-btn ds-btn--secondary">新增 5 個</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  numbers: {
    type: Array,
    default: () => []
  },
  orderPreview: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'add-number',
  'update-number',
  'remove-number',
  'clear-numbers',
  'add-multiple',
  'validate-number',
  'generate-random',
  'apply-code',
  'submit-order'
])

const codeInput = ref('')

const applyCode = (value) => {
  if (!value) return
  emit('apply-code', value)
  codeInput.value = ''
}
</script>
