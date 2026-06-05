<template>
    <div
        class="box-tooltip"
        :style="{ left: `${position.x}px`, top: `${position.y}px` }"
    >
        <div class="tooltip-label">箱子編號</div>
        <div class="tooltip-id">#{{ boxInfo.boxId }}</div>

        <div class="tooltip-label">寶藏包</div>
        <div class="tooltip-name">{{ boxInfo.treasurePack || '海盜寶藏' }}</div>

        <div class="tooltip-label">單詞分類</div>
        <div class="tooltip-category">{{ boxInfo.productName }}</div>

        <div class="tooltip-label">分類提示</div>
        <div class="tooltip-story">{{ storySummary }}</div>

        <div v-if="boxInfo.wordCount" class="tooltip-count">{{ boxInfo.wordCategory }}｜{{ boxInfo.wordCount }} 字</div>
    </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    boxInfo: {
        type: Object,
        required: true
    },
    position: {
        type: Object,
        required: true
    }
});

const storySummary = computed(() => props.boxInfo.storyHint || '跟著海盜故事的線索，猜猜這箱寶藏屬於哪一種單詞分類。')
</script>

<style scoped>
.box-tooltip {
    position: absolute;
    padding: 10px 12px;
    background: rgba(0, 0, 0, 0.84);
    color: white;
    border-radius: 8px;
    font-size: 12px;
    pointer-events: none;
    transform: translate(12px, -12px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    z-index: 12;
    backdrop-filter: blur(6px);
    max-width: 280px;
    min-width: 220px;
}

.tooltip-label {
    font-size: 11px;
    color: #cbd5e1;
    letter-spacing: 0.5px;
}

.tooltip-id {
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 6px;
    color: #a5b4fc;
}

.tooltip-name {
    font-weight: 700;
    margin-bottom: 6px;
    color: #fbbf24;
}

.tooltip-category {
    font-weight: 600;
    margin-bottom: 6px;
    color: #f9fafb;
}

.tooltip-story {
    line-height: 1.45;
    margin-bottom: 8px;
    color: #e5e7eb;
}

.tooltip-count {
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    padding-top: 6px;
    color: #93c5fd;
    font-weight: 600;
}
</style>
