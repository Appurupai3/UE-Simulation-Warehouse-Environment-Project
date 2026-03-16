<template>
  <div class="bg-white rounded-2xl shadow-xl p-6 mt-6 space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold text-gray-800">客製化倉儲編輯器（15 x 15）</h2>
        <p class="text-sm text-gray-500">車子與貨物可同格；出貨口每次會成對佔 2 格；障礙物會阻擋貨物。</p>
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

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 bg-gray-50 rounded-xl p-3 border border-gray-200">
      <label class="text-sm text-gray-700">全域貨物層數
        <input v-model.number="globalCargoCount" type="number" min="0" max="20" class="mt-1 w-full border rounded px-2 py-1" />
      </label>
      <label class="text-sm text-gray-700">行號 (1-15)
        <input v-model.number="selectedRow" type="number" min="1" max="15" class="mt-1 w-full border rounded px-2 py-1" />
      </label>
      <label class="text-sm text-gray-700">該行貨物層數
        <input v-model.number="rowCargoCount" type="number" min="0" max="20" class="mt-1 w-full border rounded px-2 py-1" />
      </label>
      <label class="text-sm text-gray-700">架子高度 (3~10)
        <input v-model.number="shelfHeight" type="number" min="3" max="10" class="mt-1 w-full border rounded px-2 py-1" />
      </label>
      <div class="lg:col-span-3 flex flex-wrap gap-2">
        <button class="px-3 py-2 rounded bg-indigo-500 text-white text-sm" @click="applyGlobalCargo">套用全域貨量</button>
        <button class="px-3 py-2 rounded bg-indigo-400 text-white text-sm" @click="applyRowCargo">套用該行貨量</button>
      </div>
    </div>

    <div class="overflow-auto border rounded-lg p-2 bg-gray-50">
      <div class="grid-container" :style="gridStyle">
        <button
          v-for="(cell, index) in flatCells"
          :key="index"
          class="cell"
          :class="cellClass(cell)"
          @click="paintCell(index)"
          :title="cellTitle(cell)"
        >
          <span v-if="cell.unload">🚪</span>
          <span v-if="cell.car">🚗</span>
          <span v-if="cell.cargo">📦{{ cell.cargoCount }}</span>
          <span v-if="cell.obstacle">🟫</span>
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
import { createDefaultWarehouseLayout, LAYOUT_SIZE, TOOL_OPTIONS } from '../utils/warehouseLayout';
import { fetchWarehouseLayout, saveWarehouseLayout } from '../utils/warehouseLayoutApi';

const layout = ref(createDefaultWarehouseLayout());
const selectedTool = ref('cargo');
const message = ref('');
const globalCargoCount = ref(5);
const selectedRow = ref(1);
const rowCargoCount = ref(5);
const shelfHeight = ref(5);

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${LAYOUT_SIZE}, minmax(34px, 1fr))`
}));

const flatCells = computed(() => layout.value.cells.flat());
const activeToolLabel = computed(() => TOOL_OPTIONS.find(t => t.key === selectedTool.value)?.label || '');

const indexToCoord = (index) => ({
  y: Math.floor(index / LAYOUT_SIZE),
  x: index % LAYOUT_SIZE
});

const normalizeCargoCount = (v) => Math.max(0, Math.floor(Number(v) || 0));

const applyCargoCount = (cell, count) => {
  const next = normalizeCargoCount(count);
  if (cell.obstacle) return;
  cell.cargoCount = next;
  cell.cargo = next > 0;
};

const setUnloadPair = (x, y, value) => {
  if (x >= LAYOUT_SIZE - 1) return;
  layout.value.cells[y][x].unload = value;
  layout.value.cells[y][x + 1].unload = value;
};

const paintCell = (index) => {
  const { x, y } = indexToCoord(index);
  const cell = layout.value.cells[y][x];

  if (selectedTool.value === 'cargo') {
    if (cell.unload) return;
    cell.obstacle = false;
    applyCargoCount(cell, globalCargoCount.value);
    return;
  }

  if (selectedTool.value === 'car') {
    cell.car = !cell.car;
    return;
  }

  if (selectedTool.value === 'unload') {
    const next = !(cell.unload && x < LAYOUT_SIZE - 1 && layout.value.cells[y][x + 1].unload);
    setUnloadPair(x, y, next);
    if (next) {
      const rightCell = layout.value.cells[y][Math.min(x + 1, LAYOUT_SIZE - 1)];
      cell.cargo = false;
      cell.cargoCount = 0;
      rightCell.cargo = false;
      rightCell.cargoCount = 0;
      cell.obstacle = false;
      rightCell.obstacle = false;
    }
    return;
  }

  if (selectedTool.value === 'obstacle') {
    cell.obstacle = !cell.obstacle;
    if (cell.obstacle) {
      cell.cargo = false;
      cell.cargoCount = 0;
      cell.unload = false;
    }
    return;
  }

  // erase
  layout.value.cells[y][x] = {
    cargo: false,
    cargoCount: 0,
    unload: false,
    car: false,
    obstacle: false
  };
};

const applyGlobalCargo = () => {
  layout.value.cells.forEach((row) => {
    row.forEach((cell) => {
      if (!cell.obstacle && !cell.unload && cell.cargo) applyCargoCount(cell, globalCargoCount.value);
    });
  });
};

const applyRowCargo = () => {
  const rowIndex = Math.max(1, Math.min(LAYOUT_SIZE, Number(selectedRow.value || 1))) - 1;
  layout.value.cells[rowIndex].forEach((cell) => {
    if (!cell.obstacle && !cell.unload && cell.cargo) applyCargoCount(cell, rowCargoCount.value);
  });
};

const cellClass = (cell) => ({
  cargo: cell.cargo,
  unload: cell.unload,
  car: cell.car,
  obstacle: cell.obstacle,
  empty: !cell.cargo && !cell.unload && !cell.car && !cell.obstacle
});

const cellTitle = (cell) => `貨:${cell.cargo ? cell.cargoCount : 0} 出:${cell.unload ? '是' : '否'} 車:${cell.car ? '是' : '否'} 障:${cell.obstacle ? '是' : '否'}`;

const load = async () => {
  layout.value = await fetchWarehouseLayout();
  globalCargoCount.value = layout.value.maxStack || 5;
  rowCargoCount.value = globalCargoCount.value;
  shelfHeight.value = Math.max(3, Math.min(10, Number(layout.value.shelfHeight || 5)));
  message.value = `已載入 (${new Date().toLocaleTimeString()})`;
};

const save = async () => {
  layout.value.maxStack = normalizeCargoCount(globalCargoCount.value) || 1;
  layout.value.shelfHeight = Math.max(3, Math.min(10, Math.floor(Number(shelfHeight.value || 5))));
  layout.value.updatedAt = new Date().toISOString();
  await saveWarehouseLayout(layout.value);
  message.value = `已儲存 (${new Date().toLocaleTimeString()})`;
};

const resetDefault = () => {
  layout.value = createDefaultWarehouseLayout();
  globalCargoCount.value = layout.value.maxStack;
  rowCargoCount.value = layout.value.maxStack;
  shelfHeight.value = layout.value.shelfHeight || 5;
  message.value = '已回復預設配置，記得按「儲存到後端」';
};

load();
</script>

<style scoped>
.grid-container { display: grid; gap: 4px; min-width: 620px; }
.cell {
  aspect-ratio: 1/1;
  border-radius: 6px;
  font-size: 10px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  line-height: 1.05;
}
.cell.empty { background: #fff; }
.cell.cargo { background: #dbeafe; }
.cell.unload { box-shadow: inset 0 0 0 2px #22c55e; }
.cell.car { outline: 2px solid #ef4444; }
.cell.obstacle { background: #d6b38a; }
</style>
