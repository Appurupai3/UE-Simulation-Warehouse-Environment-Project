[EN](#en) | [ZH_TW](#zh_tw)

---

<a name="en"></a>
# Three.js 3D Warehouse Simulation

> Order → WebSocket → Three.js Visualization

A browser-based 3D warehouse simulation for comparing pathfinding algorithms in real time, inspired by AutoStore's grid system.

## Stack

- **Frontend**: Vue.js + Three.js (3D rendering)
- **Backend**: FastAPI + WebSocket
- **Algorithms**: A*, BFS, Dynamic Avoidance, Deadlock Detection

## Quick Start

```bash
# Backend
cd Backend
pip install -r requirements.txt
python3 app/main.py

# Frontend
cd Frontend
bun install
bun run dev
```

- Frontend: http://localhost:5173
- WebSocket: ws://localhost:8000/ws/{client_type}/{client_id}

## License

For educational and demonstration purposes only.

---

<a name="zh_tw"></a>
# Three.js 3D 倉儲模擬環境

> 發送訂單 → WebSocket 存入資料 → Three.js 顯示

基於瀏覽器的 3D 倉儲自動化模擬系統，支援多種路徑規劃演算法的即時視覺化比較，設計靈感來自 AutoStore 網格式倉儲系統。

## 技術棧

- **前端**: Vue.js + Three.js（3D 渲染）
- **後端**: FastAPI + WebSocket
- **演算法**: A*、BFS、動態避障、死鎖檢測

## 快速開始

```bash
# 後端
cd Backend
pip install -r requirements.txt
python3 app/main.py

# 前端
cd Frontend
bun install
bun run dev
```

- 前端介面: http://localhost:5173
- WebSocket 端點: ws://localhost:8000/ws/{client_type}/{client_id}

## 授權

此專案僅供教育和演示用途。
