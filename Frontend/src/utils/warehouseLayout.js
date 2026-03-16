export const LAYOUT_SIZE = 15;

export const CELL_TYPES = {
  EMPTY: 'empty',
  CARGO: 'cargo',
  UNLOAD: 'unload',
  CAR: 'car',
  OBSTACLE: 'obstacle'
};

export const TOOL_OPTIONS = [
  { key: CELL_TYPES.CARGO, label: '貨物', emoji: '📦' },
  { key: CELL_TYPES.UNLOAD, label: '出貨口', emoji: '🚪' },
  { key: CELL_TYPES.CAR, label: '車子', emoji: '🚗' },
  { key: CELL_TYPES.OBSTACLE, label: '障礙物', emoji: '⛔' },
  { key: CELL_TYPES.EMPTY, label: '清除', emoji: '🧹' }
];

export function createDefaultWarehouseLayout() {
  const cells = Array.from({ length: LAYOUT_SIZE }, () =>
    Array.from({ length: LAYOUT_SIZE }, () => CELL_TYPES.EMPTY)
  );

  // 先把目前既有倉儲(5x10)內容映射進 15x15
  for (let y = 0; y < 10; y++) {
    for (let x = 0; x < 5; x++) {
      cells[y][x] = CELL_TYPES.CARGO;
    }
  }

  // 原有出貨口
  cells[0][0] = CELL_TYPES.UNLOAD;
  cells[0][1] = CELL_TYPES.UNLOAD;
  cells[0][3] = CELL_TYPES.UNLOAD;
  cells[0][4] = CELL_TYPES.UNLOAD;

  // 先放兩台車(沿用原本起始概念)
  cells[1][0] = CELL_TYPES.CAR;
  cells[1][4] = CELL_TYPES.CAR;

  return {
    version: 1,
    width: LAYOUT_SIZE,
    height: LAYOUT_SIZE,
    cells,
    updatedAt: new Date().toISOString()
  };
}

export function normalizeWarehouseLayout(input) {
  if (!input || !Array.isArray(input.cells)) {
    return createDefaultWarehouseLayout();
  }

  const layout = createDefaultWarehouseLayout();
  const height = Math.min(LAYOUT_SIZE, input.cells.length);

  for (let y = 0; y < height; y++) {
    const row = input.cells[y];
    if (!Array.isArray(row)) continue;
    const width = Math.min(LAYOUT_SIZE, row.length);
    for (let x = 0; x < width; x++) {
      const type = row[x];
      if (Object.values(CELL_TYPES).includes(type)) {
        layout.cells[y][x] = type;
      }
    }
  }

  layout.updatedAt = input.updatedAt || layout.updatedAt;
  return layout;
}
