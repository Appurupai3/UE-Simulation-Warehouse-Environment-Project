<template>
  <div class="car-status-panel">
    <div class="panel-header" @click="togglePanel">
      <h3>🚗 車輛狀態監控</h3>
      <button class="toggle-btn">
        {{ isExpanded ? '▼' : '▶' }}
      </button>
    </div>
    
    <div v-show="isExpanded" class="panel-content">
      <div class="stats-summary">
        <div class="stat-item">
          <span class="stat-label">移動：</span>
          <span class="stat-value running">{{ runningCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">停滯中：</span>
          <span class="stat-value waiting">{{ waitingCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">停止中：</span>
          <span class="stat-value idle">{{ idleCount }}</span>
        </div>
      </div>

      <div class="car-list">
        <div 
          v-for="car in carStatuses" 
          :key="car.id" 
          class="car-card"
          :class="getCarStatusClass(car)"
        >
          <div class="car-header">
            <span class="car-name">{{ car.name }}</span>
            <span class="car-priority" :title="`優先級：${car.priority}`">
              ⭐ {{ car.priority }}
            </span>
          </div>

          <div class="car-details">
            <div class="detail-row">
              <span class="detail-label">位置：</span>
              <span class="detail-value">
                X{{ car.currentCoord?.x ?? '-' }} - Z{{ car.currentCoord?.z ?? '-' }}
              </span>
            </div>

            <div class="detail-row" v-if="car.targetCoord">
              <span class="detail-label">目標：</span>
              <span class="detail-value">
                X{{ car.targetCoord.x }} - Z{{ car.targetCoord.z }}
              </span>
            </div>

            <div class="detail-row" v-if="car.pathLength > 0">
              <span class="detail-label">路徑：</span>
              <span class="detail-value">
                {{ car.pathIndex }} / {{ car.pathLength }} 步
                <span class="progress-bar">
                  <span 
                    class="progress-fill" 
                    :style="{ width: getProgressPercent(car) + '%' }"
                  ></span>
                </span>
              </span>
            </div>

            <div class="detail-row" v-if="car.hasCargo">
              <span class="detail-label">貨物：</span>
              <span class="detail-value cargo-badge">📦 已載貨</span>
            </div>

            <div class="detail-row status-row" v-if="car.motionState === 'stagnant'">
              <span class="status-badge waiting">
                ⏸️ {{ car.waitReason || '停滯中（尚未完成目標）' }}
              </span>
            </div>

            <div class="detail-row status-row" v-else-if="car.motionState === 'moving'">
              <span class="status-badge moving">
                ▶️ 移動
              </span>
            </div>

            <div class="detail-row status-row" v-else>
              <span class="status-badge idle">
                ⏹️ 停止（目標完成）
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="legend">
        <div class="legend-item">
          <span class="legend-dot running"></span>
          <span>移動</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot waiting"></span>
          <span>停滯</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot idle"></span>
          <span>停止</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CarStatusPanel',
  props: {
    carStatuses: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      isExpanded: false
    };
  },
  computed: {
    runningCount() {
      return this.carStatuses.filter(car => car.motionState === 'moving').length;
    },
    waitingCount() {
      return this.carStatuses.filter(car => car.motionState === 'stagnant').length;
    },
    idleCount() {
      return this.carStatuses.filter(car => car.motionState === 'stopped').length;
    }
  },
  methods: {
    togglePanel() {
      this.isExpanded = !this.isExpanded;
    },
    getCarStatusClass(car) {
      if (car.motionState === 'stagnant') return 'status-waiting';
      if (car.motionState === 'moving') return 'status-running';
      return 'status-idle';
    },
    getProgressPercent(car) {
      if (car.pathLength === 0) return 0;
      return Math.round((car.pathIndex / car.pathLength) * 100);
    }
  }
};
</script>

<style scoped>
.car-status-panel {
  width: 100%;
  background: rgba(0, 0, 0, 0.85);
  border: 2px solid #3498db;
  border-radius: 12px;
  color: #ffffff;
  font-family: 'Arial', sans-serif;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #764ba2;
  border-radius: 10px 10px 0 0;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s ease;
}

.panel-header:hover {
  background: #8e44ad;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
}

.toggle-btn {
  background: transparent;
  border: none;
  color: white;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  transition: transform 0.3s ease;
}

.toggle-btn:hover {
  transform: scale(1.2);
}

.panel-content {
  padding: 12px;
}

.stats-summary {
  display: flex;
  justify-content: space-around;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: #aaa;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: bold;
}

.stat-value.running {
  color: #2ecc71;
}

.stat-value.waiting {
  color: #f39c12;
}

.stat-value.idle {
  color: #95a5a6;
}

.car-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.car-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
  border-left: 4px solid #95a5a6;
  transition: all 0.3s ease;
}

.car-card:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateX(-2px);
}

.car-card.status-running {
  border-left-color: #2ecc71;
}

.car-card.status-waiting {
  border-left-color: #f39c12;
  animation: pulse 2s infinite;
}

.car-card.status-idle {
  border-left-color: #95a5a6;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.car-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.car-name {
  font-weight: bold;
  font-size: 14px;
  color: #3498db;
}

.car-priority {
  font-size: 12px;
  background: rgba(255, 215, 0, 0.2);
  padding: 2px 8px;
  border-radius: 12px;
  color: #ffd700;
}

.car-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.detail-label {
  color: #aaa;
  font-weight: 500;
}

.detail-value {
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  display: inline-block;
  width: 60px;
  height: 6px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  background: #2ecc71;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.cargo-badge {
  background: rgba(46, 204, 113, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
  color: #2ecc71;
  font-weight: bold;
}

.status-row {
  margin-top: 4px;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
  display: inline-block;
}

.status-badge.moving {
  background: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

.status-badge.waiting {
  background: rgba(243, 156, 18, 0.2);
  color: #f39c12;
}

.status-badge.idle {
  background: rgba(149, 165, 166, 0.2);
  color: #95a5a6;
}

.legend {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-around;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #aaa;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.running {
  background: #2ecc71;
}

.legend-dot.waiting {
  background: #f39c12;
}

.legend-dot.idle {
  background: #95a5a6;
}

/* 滾動條樣式 */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>