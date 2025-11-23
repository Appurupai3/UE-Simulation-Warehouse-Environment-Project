## Three.js 3D 模擬環境

#  發送訂單 -> WebSocket 存入資料 -> Three.js 顯示 

## 🏗️ 專案架構

```
Simulation-Warehouse-Environment-Project/
├── Backend/                 # FastAPI WebSocket 後端
│   ├── app/
│   │   ├── main.py         # 主要的 FastAPI 應用程式
│   │   ├── models/         # 資料模型定義
│   │   └── services/       # WebSocket 服務層
│   ├── tests/              # 測試腳本
│   ├── requirements.txt    # Python 依賴項
│   └── .env               # 環境設定
├── Frontend/               # Vue.js 前端應用
│   ├── src/
│   │   ├── App.vue        # 主要的 Vue 組件
│   │   └── main.js        # 應用程式入口
│   ├── index.html         # HTML 模板
│   ├── package.json       # Node.js 依賴項
│   ├── vite.config.js     # Vite 設定
│   └── .gitignore         # Git 忽略規則
├── start_demo.sh          # 啟動腳本 (適用 bash/WSL)
└── start_demo.ps1         # 啟動腳本 (適用 PowerShell)
```

## 🚀 快速開始

### 1. 安裝依賴項

確保安裝了以下工具：
- **Linux bun**: `curl -fsSL https://bun.sh/install | bash`
- **Windows bun**: `powershell -c "irm bun.sh/install.ps1|iex"`
- **Python 3.8+**
- **Node.js 18+** (bun 會自動處理)

### 2. 一鍵啟動腳本

- **macOS / Linux / WSL**：在 bash 執行 `./start_demo.sh`
- **Windows PowerShell**：在 PowerShell 執行 `./start_demo.ps1`

> 如果在 PowerShell 直接執行 `start_demo.sh`，會因為指令語法不同而出現錯誤，請改用對應環境的腳本。

### 3. 訪問應用程式

- **前端介面**: http://localhost:5173
- **WebSocket 端點**: ws://localhost:8000/ws/{client_type}/{client_id}

## 🎯 前端功能特色

### 訂單管理系統

Vue.js 前端提供一個訂單管理介面：

#### 左側面板 - 訂單歷史
- 顯示所有提交的訂單記錄
- 格式：`訂單 1. 10-20-5-3`
- 包含時間戳記
- 支援清空歷史記錄

#### 右側面板 - 訂單發送

**數字輸入區**:
- 可動態新增/刪除數字輸入框
- 支援數值範圍設定（0-999）
- 即時預覽訂單格式

**操作功能**:
- **🎲 隨機生成**: 自動產生 3-7 個隨機數字
- **📤 送出訂單**: 將數字組合提交為訂單
- **清空數字**: 一鍵清除所有輸入
- **快速新增**: 可選擇新增 3 或 5 個數字框

## 🔧 開發指南

### 後端開發 (FastAPI)

```python
# 啟動開發服務器
cd Backend
python -m app.main
```

### 前端開發 (Vue.js)

```bash
# 啟動開發服務器
cd Frontend
bun run dev
```

### 建置生產版本

```bash
# 前端建置
cd Frontend
bun run build

# 後端部署
cd Backend
# 使用 uvicorn 或 gunicorn 部署
```

### 測試 WebSocket 連接

```python
# 運行測試腳本
cd Backend
python tests/test_websocket.py
```
## 3D Model
[Comfy UI](https://github.com/comfyanonymous/ComfyUI)
[hunyuan3D](https://huggingface.co/Comfy-Org/hunyuan3D_2.1_repackaged/tree/main)
## 📄 授權

此專案僅供教育和演示用途。

---
