export const LAYOUT_SIZE = 15;
export const DEFAULT_MAX_STACK = 5;

export const TOOL_OPTIONS = [
  { key: 'cargo', label: '貨物', emoji: '📦' },
  { key: 'unload', label: '出貨口(2格)', emoji: '🚪' },
  { key: 'car', label: '車子', emoji: '🚗' },
  { key: 'obstacle', label: '障礙物', emoji: '🟫' },
  { key: 'erase', label: '清除', emoji: '🧹' }
];

export function createEmptyCell() {
  return {
    cargo: false,
    cargoCount: 0,
    unload: false,
    car: false,
    obstacle: false
  };
}

export function normalizeCell(raw) {
  const base = createEmptyCell();

  if (typeof raw === 'string') {
    if (raw === 'cargo') {
      base.cargo = true;
      base.cargoCount = 1;
    } else if (raw === 'unload') {
      base.unload = true;
    } else if (raw === 'car') {
      base.car = true;
    } else if (raw === 'obstacle') {
      base.obstacle = true;
    }
    return base;
  }

  if (!raw || typeof raw !== 'object') return base;

  base.cargo = Boolean(raw.cargo);
  base.unload = Boolean(raw.unload);
  base.car = Boolean(raw.car);
  base.obstacle = Boolean(raw.obstacle);
  base.cargoCount = Number.isFinite(Number(raw.cargoCount)) ? Math.max(0, Math.floor(Number(raw.cargoCount))) : (base.cargo ? 1 : 0);

  if (base.obstacle) {
    base.cargo = false;
    base.cargoCount = 0;
  }

  if (base.cargoCount > 0) {
    base.cargo = true;
  }

  return base;
}

export function createDefaultWarehouseLayout() {
  const cells = Array.from({ length: LAYOUT_SIZE }, () =>
    Array.from({ length: LAYOUT_SIZE }, () => createEmptyCell())
  );

  for (let y = 0; y < 10; y++) {
    for (let x = 0; x < 5; x++) {
      cells[y][x].cargo = true;
      cells[y][x].cargoCount = DEFAULT_MAX_STACK;
    }
  }

  // 原有出貨口(每個出貨口佔2格)
  cells[0][0].unload = true;
  cells[0][1].unload = true;
  cells[0][3].unload = true;
  cells[0][4].unload = true;

  // 原本起始車位
  cells[1][0].car = true;
  cells[1][4].car = true;

  return {
    version: 2,
    width: LAYOUT_SIZE,
    height: LAYOUT_SIZE,
    maxStack: DEFAULT_MAX_STACK,
    cells,
    updatedAt: new Date().toISOString()
  };
}

export function normalizeWarehouseLayout(input) {
  const layout = createDefaultWarehouseLayout();
  if (!input || !Array.isArray(input.cells)) return layout;

  const height = Math.min(LAYOUT_SIZE, input.cells.length);
  for (let y = 0; y < height; y++) {
    const row = input.cells[y];
    if (!Array.isArray(row)) continue;
    const width = Math.min(LAYOUT_SIZE, row.length);
    for (let x = 0; x < width; x++) {
      layout.cells[y][x] = normalizeCell(row[x]);
    }
  }

  if (Number.isFinite(Number(input.maxStack))) {
    layout.maxStack = Math.max(1, Math.floor(Number(input.maxStack)));
  }

  layout.updatedAt = input.updatedAt || layout.updatedAt;
  return layout;
}
