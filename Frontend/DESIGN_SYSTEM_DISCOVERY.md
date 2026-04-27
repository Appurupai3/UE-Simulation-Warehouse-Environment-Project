# Design System Discovery: UE Warehouse Frontend

## 1) Current Tech Stack (Observed)

- **Framework:** Vue 3 (Composition API + `<script setup>`).
- **Build Tooling:** Vite 5 (`@vitejs/plugin-vue`).
- **Styling Approach:** Utility-first classes from **Tailwind via CDN** in `index.html` (not via local Tailwind config/package).
- **3D/Visualization:** Three.js (+ helpers like `three-mesh-bvh`, `dat.gui`, `stats.js`).
- **Editor/Benchmark UI:** Monaco editor dependency is present.

## 2) Existing Design Tokens & Styling Patterns (Observed)

### Color and surface language
- Heavy usage of Tailwind utility color presets (e.g. `blue-*`, `indigo-*`, `purple-*`, `gray-*`).
- Gradient usage exists (`bg-gradient-to-r from-blue-600 to-purple-600`) but is not centralized as a reusable token.
- Cards follow a recurring visual style: `bg-white rounded-2xl shadow-xl` with moderate spacing.

### Typography
- Default system sans stack (no explicit custom font loading for display/body/mono pairing).
- Title hierarchy relies mostly on utility sizes and `font-bold`.

### Spacing/radius/shadow
- Spacing is mostly utility-driven (`p-6`, `mb-6`, `gap-6`) and generally consistent.
- Rounding commonly uses `rounded-lg`/`rounded-2xl`.
- Elevation uses preset shadows (`shadow-xl`) with no accent shadow token.

### Global styles / utilities
- `App.vue` includes scoped browser input spinner resets and custom scrollbar styles for `.overflow-y-auto`.
- No centralized CSS variable theme layer is currently present.

## 3) Component Architecture & Naming

- Feature-first Vue component organization:
  - `src/components/*` with nested feature folders (e.g. `ThreeScenePage`, `CargoTest`, `AlgorithmBenchmark`).
  - Shared pages under `src/pages/*`.
  - Reusable behavior in `src/composables/*`.
- Naming is descriptive and domain-aligned (`OrderForm`, `OrderList`, `HeaderControls`, `CarStatusPanel`).
- Current pattern appears pragmatic rather than strict atomic-design tiers.

## 4) Constraints / Risks for Design-System Integration

1. **Tailwind via CDN**
   - Fast to iterate, but no local `tailwind.config` means limited token centralization, plugin support, and scale control.

2. **Mixed UI concerns**
   - The app includes both business UI and real-time/3D workflows. A migration should avoid destabilizing scene tooling pages.

3. **No existing design primitives layer**
   - No local Button/Card/Input abstraction with variants yet, so one-off utility strings can drift over time.

4. **Potential language and density constraints**
   - UI labels are Chinese-first in places; typography and spacing choices should preserve readability across bilingual text.

## 5) Recommended Migration Direction (Concise)

1. Introduce a **theme token layer** using CSS variables (background, foreground, muted, accent, border, ring, etc.).
2. Add a small set of **UI primitives** (`BaseButton`, `BaseCard`, `BaseInput`, `SectionLabel`) with prop-driven variants.
3. Start by migrating a **single high-impact page** (likely `App.vue` + top-level components), then expand page-by-page.
4. Add **motion utilities** and reduced-motion fallbacks before introducing continuous hero/ambient animations.
5. Keep Three.js pages functional and style-shell them gradually instead of deep refactors in one pass.

## 6) Focused Questions to Confirm Scope Before Coding

1. Which scope do you want first?
   - A) Redesign **one specific page/component** in the Minimalist Modern style.
   - B) Refactor **existing shared components** into reusable design-system primitives.
   - C) Build **new page(s)/feature(s)** fully in the new style while leaving existing ones mostly intact.

2. Do you want me to keep Tailwind CDN for now, or migrate to a local Tailwind config so we can centralize tokens properly?

3. Should the first implementation target only the **order management UI** (`App.vue`, `HeaderControls`, `OrderForm`, `OrderList`) and avoid Three.js/benchmark pages in phase 1?

4. Are we allowed to add dependencies for motion/primitives (e.g. `framer-motion` equivalent for Vue such as `motion-v`) or should we stick to zero new runtime deps?

5. Should I prioritize a **light-only Minimalist Modern theme** first, or include dark/inverted section support in the first pass?

6. Is there a deadline preference: fast visual pass first, or slower architecture-first migration with strict reuse and tokenization?
