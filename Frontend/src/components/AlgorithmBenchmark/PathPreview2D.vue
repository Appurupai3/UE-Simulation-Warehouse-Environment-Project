<template>
  <div class="path-preview-2d">
    <div class="preview-header">
      <h4>2D 移動模擬預覽</h4>
      <div class="controls">
        <button class="btn-control" @click="togglePlayback">
          {{ isPlaying ? '暫停' : '播放' }}
        </button>
        <button class="btn-control" @click="resetPlayback">重播</button>
        <label class="speed-label">
          速度
          <input v-model.number="playbackMs" type="range" min="120" max="1200" step="60" />
        </label>
      </div>
    </div>

    <svg :viewBox="`0 0 ${viewSize} ${viewSize}`" class="preview-canvas" role="img" aria-label="2D 路徑預覽">
      <g>
        <line
          v-for="(line, index) in gridLines"
          :key="`grid-${index}`"
          :x1="line.x1"
          :y1="line.y1"
          :x2="line.x2"
          :y2="line.y2"
          class="grid-line"
        />
      </g>

      <polyline v-if="polylinePoints" :points="polylinePoints" class="path-line" />

      <g v-for="(point, index) in scaledPoints" :key="`point-${index}`">
        <circle :cx="point.x" :cy="point.y" :class="getPointClass(index)" r="6" />
        <text :x="point.x + 8" :y="point.y - 8" class="point-label">{{ index + 1 }}</text>
      </g>

      <circle
        v-if="currentMarker"
        :cx="currentMarker.x"
        :cy="currentMarker.y"
        class="moving-marker"
        r="8"
      />
    </svg>

    <div class="preview-footer">
      <span>步驟：{{ currentStep }} / {{ totalSteps }}</span>
      <span v-if="activeItemId !== null">當前箱號：{{ activeItemId }}</span>
      <span v-else>尚未開始</span>
    </div>
  </div>
</template>

<script>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

export default {
  name: 'PathPreview2D',
  props: {
    path: {
      type: Array,
      default: () => []
    },
    positions: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const viewSize = 360
    const padding = 30
    const playbackMs = ref(420)
    const animationIndex = ref(0)
    const timerId = ref(null)
    const isPlaying = ref(false)

    const normalizedPoints = computed(() => {
      if (!Array.isArray(props.positions) || props.positions.length === 0) return []

      const points = props.positions.map((position, idx) => ({
        x: Number(position?.x ?? 0),
        z: Number(position?.z ?? 0),
        itemId: props.path?.[idx] ?? null
      }))

      const xs = points.map((point) => point.x)
      const zs = points.map((point) => point.z)
      const minX = Math.min(...xs)
      const maxX = Math.max(...xs)
      const minZ = Math.min(...zs)
      const maxZ = Math.max(...zs)

      return points.map((point) => ({
        ...point,
        nx: maxX === minX ? 0.5 : (point.x - minX) / (maxX - minX),
        nz: maxZ === minZ ? 0.5 : (point.z - minZ) / (maxZ - minZ)
      }))
    })

    const scaledPoints = computed(() => {
      const drawable = viewSize - padding * 2
      return normalizedPoints.value.map((point) => ({
        ...point,
        x: padding + point.nx * drawable,
        y: padding + point.nz * drawable
      }))
    })

    const polylinePoints = computed(() => scaledPoints.value.map((point) => `${point.x},${point.y}`).join(' '))

    const gridLines = computed(() => {
      const lines = []
      const drawable = viewSize - padding * 2
      const segments = 6
      for (let i = 0; i <= segments; i += 1) {
        const offset = padding + (drawable / segments) * i
        lines.push({ x1: padding, y1: offset, x2: viewSize - padding, y2: offset })
        lines.push({ x1: offset, y1: padding, x2: offset, y2: viewSize - padding })
      }
      return lines
    })

    const totalSteps = computed(() => scaledPoints.value.length)
    const currentStep = computed(() => Math.min(animationIndex.value + 1, totalSteps.value || 0))
    const currentMarker = computed(() => scaledPoints.value[animationIndex.value] || null)
    const activeItemId = computed(() => currentMarker.value?.itemId ?? null)

    const stopPlayback = () => {
      if (timerId.value) {
        clearInterval(timerId.value)
        timerId.value = null
      }
      isPlaying.value = false
    }

    const startPlayback = () => {
      if (scaledPoints.value.length <= 1) return
      stopPlayback()
      isPlaying.value = true
      timerId.value = setInterval(() => {
        if (animationIndex.value >= scaledPoints.value.length - 1) {
          stopPlayback()
          return
        }
        animationIndex.value += 1
      }, playbackMs.value)
    }

    const togglePlayback = () => {
      if (isPlaying.value) {
        stopPlayback()
      } else {
        startPlayback()
      }
    }

    const resetPlayback = () => {
      stopPlayback()
      animationIndex.value = 0
    }

    const getPointClass = (index) => {
      if (index === 0) return 'path-point start'
      if (index === scaledPoints.value.length - 1) return 'path-point end'
      return 'path-point mid'
    }

    watch(() => props.positions, () => {
      resetPlayback()
      if (scaledPoints.value.length > 1) {
        startPlayback()
      }
    }, { deep: true, immediate: true })

    watch(playbackMs, () => {
      if (isPlaying.value) {
        startPlayback()
      }
    })

    onBeforeUnmount(() => {
      stopPlayback()
    })

    return {
      viewSize,
      playbackMs,
      isPlaying,
      scaledPoints,
      gridLines,
      polylinePoints,
      currentMarker,
      currentStep,
      totalSteps,
      activeItemId,
      togglePlayback,
      resetPlayback,
      getPointClass
    }
  }
}
</script>

<style scoped>
.path-preview-2d {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #d8e2ef;
  border-radius: 8px;
  background: #f5f9ff;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.preview-header h4 {
  margin: 0;
  color: #1f3a5a;
}

.controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-control {
  border: 1px solid #7ca5d6;
  color: #1f3a5a;
  background: #fff;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
}

.btn-control:hover {
  background: #eaf3ff;
}

.speed-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #1f3a5a;
  font-size: 12px;
}

.preview-canvas {
  width: 100%;
  max-width: 420px;
  height: auto;
  border: 1px solid #d4e1f1;
  border-radius: 6px;
  background: #ffffff;
}

.grid-line {
  stroke: #edf2fa;
  stroke-width: 1;
}

.path-line {
  fill: none;
  stroke: #4f7db8;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 4 4;
}

.path-point {
  stroke: #fff;
  stroke-width: 2;
}

.path-point.start {
  fill: #16a34a;
}

.path-point.end {
  fill: #dc2626;
}

.path-point.mid {
  fill: #3b82f6;
}

.moving-marker {
  fill: #f59e0b;
  stroke: #9a6d08;
  stroke-width: 2;
}

.point-label {
  font-size: 10px;
  fill: #35567f;
  font-weight: 600;
}

.preview-footer {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  color: #2f4562;
  font-size: 12px;
}
</style>
