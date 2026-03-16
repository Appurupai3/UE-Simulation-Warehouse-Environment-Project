import { createDefaultWarehouseLayout, normalizeWarehouseLayout } from './warehouseLayout';

const API_BASE_URL = 'http://localhost:8000';

export async function fetchWarehouseLayout(apiBaseUrl = API_BASE_URL) {
  try {
    const response = await fetch(`${apiBaseUrl}/vue/warehouse-layout`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return normalizeWarehouseLayout(data?.layout);
  } catch (error) {
    console.warn('載入客製化倉儲配置失敗，改用預設配置', error);
    return createDefaultWarehouseLayout();
  }
}

export async function saveWarehouseLayout(layout, apiBaseUrl = API_BASE_URL) {
  const normalized = normalizeWarehouseLayout(layout);
  const response = await fetch(`${apiBaseUrl}/vue/warehouse-layout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(normalized)
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}
