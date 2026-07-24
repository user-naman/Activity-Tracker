# Daily Radar

A one-screen activity tracker for a procurement consultant, built on the **Astra by
Valorant** design system. Daily Radar shows one working day, reads the day's signals
from connected sources, ranks every item **P1 / P2 / P3**, and lays them out on a
**Kanban board** (To Do · In Progress · Done) so mid-flight work is always visible.

## What it does

- **Ranked list of today's items** — every card carries a P1/P2/P3 priority badge, and
  columns are ordered by priority (P1 → P2 → P3), then by time.
- **A source tag on every item** — each card shows the source it came from (Gmail,
  Outlook, Teams, Fireflies) as a colored avatar.
- **A one-line reason on every P1** — the highest-priority items explain themselves in a
  single calm line, so the "why" is never a click away.
- **Kanban flow** — drag a card between columns, or tap it to advance To Do → In
  Progress → Done. Items pushed back to To Do are tagged *Carried*.
- **Morning / Evening triage** — the segmented control reframes the day: a morning
  count of items to file, an evening count of items waiting for review.
- **Connections panel** — a slide-over showing connector status (Connected / Checking /
  Not connected) with per-source toggles and a Recheck All action.

## Design system

The UI is a faithful build of the handoff design (`Daily Radar.dc.html`) using the Astra
design tokens exactly as delivered — its Inter type scale, navy/teal palette, ring-based
depth, and radius system. No new colors or typefaces were introduced.

Tokens live in `src/styles/tokens/` and are imported through `src/styles/index.css`.

## Stack

- React 18 + TypeScript
- Vite

## Getting started

```bash
npm install
npm run dev      # start the dev server
npm run build    # typecheck + production build
npm run preview  # preview the production build
```

## Project structure

```
src/
  main.tsx                 App entry
  App.tsx                  The Daily Radar screen + state/logic
  lib/data.ts              Types, seed signals, source/priority/status metadata
  components/
    ds/                    Astra design-system components (Button, Badge, KPICard, …)
    KanbanBoard.tsx        Three ranked columns + drag targets
    RadarCard.tsx          A single item card (source tag, priority, P1 reason)
    ConnectionsPanel.tsx   Connector status slide-over
  styles/
    index.css              Global entry (imports tokens)
    tokens/                Astra tokens (colors, type, shape, motion, recipes, fonts)
```
