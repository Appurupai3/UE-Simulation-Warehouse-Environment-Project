<template>
  <section class="flow-panel">
    <h3 class="flow-title">車子移動流程圖</h3>
    <p class="flow-subtitle">包含：移動到取貨位 → 拿起貨物 → 移動到目標位 → 放下貨物</p>

    <div class="flow-track" aria-label="車子移動流程">
      <div class="flow-step"><span class="flow-index">1</span><span class="flow-label">移動到取貨位置 (X,Z)</span></div>
      <span class="flow-arrow">→</span>
      <div class="flow-step"><span class="flow-index">2</span><span class="flow-label">拿起貨物 (Pick Up)</span></div>
      <span class="flow-arrow">→</span>
      <div class="flow-step"><span class="flow-index">3</span><span class="flow-label">移動到放貨位置 (X,Z)</span></div>
      <span class="flow-arrow">→</span>
      <div class="flow-step"><span class="flow-index">4</span><span class="flow-label">放下貨物 (Drop)</span></div>
    </div>
  </section>
</template>

<style scoped>
.flow-panel { border-radius: 8px; padding: 16px; background: #1f2937; }
.flow-title { margin: 0; font-size: 1rem; font-weight: 700; color: #f9fafb; }
.flow-subtitle { margin: 6px 0 14px; font-size: 0.875rem; color: #d1d5db; }
.flow-track { display: grid; grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr; gap: 8px; align-items: center; }
.flow-step { min-height: 72px; border-radius: 8px; background: #374151; padding: 10px; display: flex; flex-direction: column; justify-content: center; gap: 6px; }
.flow-index { width: 24px; height: 24px; border-radius: 9999px; display: inline-flex; align-items: center; justify-content: center; background: #3b82f6; color: #fff; font-size: 0.75rem; font-weight: 700; }
.flow-label { font-size: 0.875rem; color: #f8fafc; line-height: 1.4; }
.flow-arrow { color: #9ca3af; font-size: 1.2rem; font-weight: 700; }
@media (max-width: 1024px) { .flow-track { grid-template-columns: 1fr; gap: 10px; } .flow-arrow { justify-self: center; transform: rotate(90deg); } }
</style>
