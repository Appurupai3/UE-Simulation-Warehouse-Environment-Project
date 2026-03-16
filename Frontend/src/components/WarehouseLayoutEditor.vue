<template>
  <div class="bg-white rounded-2xl shadow-xl p-6 mt-6 space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold text-gray-800">客製化倉儲編輯器（15 x 15）</h2>
        <p class="text-sm text-gray-500">選工具後點擊格子放置元素，儲存後 3D「重製倉庫」會依此配置重建。</p>
      </div>
      <div class="text-sm text-gray-500">目前工具：<span class="font-semibold text-indigo-600">{{ activeToolLabel }}</span></div>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="tool in TOOL_OPTIONS"
        :key="tool.key"
        class="px-3 py-2 rounded-lg border text-sm font-medium"
        :class="selectedTool === tool.key ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'"
        @click="selectedTool = tool.key"
      >
        {{ tool.emoji }} {{ tool.label }}
      </button>
    </div>

    <div class="overflow-auto border rounded-lg p-2 bg-gray-50">
      <div class="grid-container" :style="gridStyle">
        <button
          v-for="(cell, index) in flatCells"
          :key="index"
          class="cell"
          :class="cellClass(cell)"
          @click="paintCell(index)"
          :title="cell"
        >
          {{ cellSymbol(cell) }}
        </button>
      </div>
    </div>

    <div class="flex flex-wrap gap-2">
      <button class="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg" @click="save">儲存到後端</button>
      <button class="px-4 py-2 bg-slate-500 hover:bg-slate-600 text-white rounded-lg" @click="load">重新載入</button>
      <button class="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg" @click="resetDefault">回復預設</button>
      <span class="text-sm text-gray-500 self-center">{{ message }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { CELL_TYPES, createDefaultWarehouseLayout, LAYOUT_SIZE, TOOL_OPTIONS } from '../utils/warehouseLayout';
import { fetchWarehouseLayout, saveWarehouseLayout } from '../utils/warehouseLayoutApi';

const layout = ref(createDefaultWarehouseLayout());
const selectedTool = ref(CELL_TYPES.CARGO);
const message = ref('');

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${LAYOUT_SIZE}, minmax(30px, 1fr))`
}));

const flatCells = computed(() => layout.value.cells.flat());
const activeToolLabel = computed(() => TOOL_OPTIONS.find(t => t.key === selectedTool.value)?.label || '');

const indexToCoord = (index) => ({
  y: Math.floor(index / LAYOUT_SIZE),
  x: index % LAYOUT_SIZE
});

const paintCell = (index) => {
  const { x, y } = indexToCoord(index);
  layout.value.cells[y][x] = selectedTool.value;
};

const cellSymbol = (cell) => {
  if (cell === CELL_TYPES.CARGO) return '📦';
  if (cell === CELL_TYPES.UNLOAD) return '🚪';
  if (cell === CELL_TYPES.CAR) return '🚗';
  if (cell === CELL_TYPES.OBSTACLE) return '⛔';
  return '';
};

const cellClass = (cell) => ({
  cargo: cell === CELL_TYPES.CARGO,
  unload: cell === CELL_TYPES.UNLOAD,
  car: cell === CELL_TYPES.CAR,
  obstacle: cell === CELL_TYPES.OBSTACLE,
  empty: cell === CELL_TYPES.EMPTY
});

const load = async () => {
  layout.value = await fetchWarehouseLayout();
  message.value = `已載入 (${new Date().toLocaleTimeString()})`;
};

const save = async () => {
  layout.value.updatedAt = new Date().toISOString();
  await saveWarehouseLayout(layout.value);
  message.value = `已儲存 (${new Date().toLocaleTimeString()})`;
};

const resetDefault = () => {
  layout.value = createDefaultWarehouseLayout();
  message.value = '已回復預設配置，記得按「儲存到後端」';
};

load();
</script>

<style scoped>
.grid-container { display: grid; gap: 4px; min-width: 550px; }
.cell { aspect-ratio: 1/1; border-radius: 6px; font-size: 12px; border: 1px solid #e5e7eb; }
.cell.empty { background: #fff; }
.cell.cargo { background: #dbeafe; }
.cell.unload { background: #dcfce7; }
.cell.car { background: #fee2e2; }
.cell.obstacle { background: #fef3c7; }
</style>
