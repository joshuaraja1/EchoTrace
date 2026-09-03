# Investigation Workspace Page Overrides

> **PROJECT:** EchoTrace
> **Generated:** 2026-09-03 04:19:23
> **Page Type:** Dashboard / Data View

> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/MASTER.md`).
> Only deviations from the Master are documented here. For all other rules, refer to the Master.

---

## Page-Specific Rules

### Layout Overrides

- **Max Width:** 1400px or full-width
- **Grid:** 12-column grid for data flexibility
- **Sections:** 1. Case identity and state, 2. Persistent view navigation, 3. Active reconstruction surface, 4. Responsive evidence register

### Spacing Overrides

- **Content Density:** High — optimize for information display

### Typography Overrides

- No overrides — use Master typography

### Color Overrides

- **Strategy:** Dark or neutral. Status colors (green/amber/red). Data-dense but scannable.

### Component Overrides

- Avoid: Leave UI frozen with no feedback
- Source ingestion must remain reachable at every breakpoint.
- Empty states must explain the next action and the three-stage workflow.
- Case processing actions use explicit disabled states until prerequisites are met.

---

## Page-Specific Components

- Responsive source register drawer
- Synchronized multi-camera stage and global transport
- Guided evidence-ingestion empty state
- Audited event correction dialog
- Evidence-grounded assistant with citations

---

## Recommendations

- Effects: Hover tooltips, chart zoom on click, row highlighting on hover, smooth filter animations, data loading spinners
- Animation: 200ms view crossfades, 240ms source-drawer transition, loading spinners; transform and opacity only
- CTA Placement: Processing controls in the workbar; upload CTA in both the empty state and source register

## Visual Philosophy: Forensic Control Room

The workspace behaves like a reconstruction desk, not a generic SaaS dashboard. Dark structural rails hold the case together while warm evidence surfaces provide enough calm for sustained review. Safety orange is reserved for action, synchronization, and the currently active investigative state.

Information density is deliberate but never cryptic. Technical labels, timestamps, hashes, and confidence values use a monospace voice; conclusions and investigator-facing language use Archivo for fast reading. Every screen keeps case identity, source state, and the next valid action within sight.

Motion communicates change of state. Views crossfade with a small directional shift, the source register moves from the edge where it lives, and progress indicators rotate only while work is happening. Reduced-motion preferences collapse these transitions to immediate state changes.

The composition uses a strict operational grid and visible provenance. Empty space is instructional rather than decorative, showing how independent source channels converge into a shared clock. The interface should feel precise, calm, and accountable under pressure.
