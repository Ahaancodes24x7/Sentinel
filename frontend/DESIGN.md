# Sentinel design system — hi-vis industrial control room

The palette is taken from the domain, not from a dashboard template. Hi-vis
lime, safety orange and warning red are the colours already painted on the
equipment, the PPE and the signage at an OIL facility. On a near-black ground
they read the way they do on site: as **signal**, not decoration.

The second rule is that the interface must look like it is **running**. A
precursor-detection console that sits perfectly still looks like a printed
report, and the whole point is that it is watching. Counters count, feeds push,
status dots breathe, control charts advance, severity bars fill.

Everything lives in `src/index.css`. There is **no `tailwind.config.js`** and
there never will be — Tailwind v4 is CSS-first. Tokens are declared in one
`@theme static { … }` block, which generates the utilities *and* emits every
token as a real CSS custom property on `:root`, so `var(--color-hivis)` works in
Recharts props and inline styles too.

---

## 1. How to use it

```tsx
// Correct
<div className="panel p-4 text-ink-2">
<span className="text-critical">…</span>

// Wrong — banned
<div className="bg-slate-900 border-slate-800 text-slate-400">
<div className="bg-[#0b0d10]">
<div style={{ color: '#ef4444' }}>
```

The token name **is** the utility name. `--color-surface-2` → `bg-surface-2`,
`text-surface-2`, `border-surface-2`. `--radius-panel` → `rounded-panel`.

---

## 2. Ground and surfaces

`#000` is banned: it flattens the sense of a lit control room and makes the
hi-vis accents glare rather than glow. The ground is warm-shifted near-black.

| Token | Hex | Use |
|---|---|---|
| `--color-void` | `#08090B` | Behind the app shell only |
| `--color-bg` | `#0B0D10` | The app ground |
| `--color-surface` | `#111419` | Default panel fill — the workhorse |
| `--color-surface-2` | `#171B21` | Raised: table headers, inputs, insets |
| `--color-surface-3` | `#1E242C` | Row hover, selected row, popovers |
| `--color-line` | `#232A33` | The default 1px hairline on every panel |
| `--color-line-faint` | `#171C23` | Dividers *inside* a panel, row rules |

Text runs `--color-ink` → `--color-ink-4`, lightest to dimmest. Body copy is
`ink-2`; `ink-4` is for mono labels and is deliberately quiet.

---

## 3. Colour has one job

**Hi-vis lime (`--color-hivis`, `#D4FF3F`)** means *live / active / primary
action*. It is the colour of a safety vest and it is never used decoratively.

**The severity ladder** is four steps, far apart in hue so they survive the
common colour-vision deficiencies:

| Token | Meaning in this product |
|---|---|
| `--color-critical` `#FF2D3D` | Precursor confirmed, barrier absent, SPC signal |
| `--color-high` `#FF7A18` | Needs review, barrier unverified |
| `--color-medium` `#FFC53D` | Insufficient detail, uncalibrated metric warning |
| `--color-low` `#3DDC97` | Cleared, barrier confirmed, process in control |

`--color-info` (blue) and `--color-violet` are **information, never severity** —
used for the reasoning chain, cluster views and ontology reference.

Every tone ships as three tokens: solid (`--color-high`), a 12% background wash
(`--color-high-wash`), and a 38% border (`--color-high-edge`). Chips and callouts
are always wash + edge + solid text, never solid fills.

---

## 4. Type

| Family | Token | Use |
|---|---|---|
| Archivo 800 | `--font-display` | Headlines and big numbers. Tight (`-0.03em`), heavy, condensed. |
| Inter | `--font-sans` | All body and UI copy. |
| JetBrains Mono | `--font-mono` | Every label, ID, timestamp, metric and chip. |

Two conventions carry most of the character:

- `.tracked` — uppercase, `0.14em` letter-spacing. Every panel title, chip and
  field label. This is what makes it read as instrumentation.
- `.tabular` — tabular numerals. **Mandatory** on any number that updates live,
  otherwise digits jitter as they change.

---

## 5. Motion

Motion is emphasis, never the only carrier of meaning. Every animated element
also encodes its state statically (colour, text, width), so the
`prefers-reduced-motion` block in `index.css` can disable all of it without
making anything ambiguous.

| Primitive | Where | Why |
|---|---|---|
| `<Counter>` | Every KPI | Counts up, and **flashes on change**. A silently-updated figure is indistinguishable from a stale one. |
| `<PulseDot live>` | Status, priority rows | The "system is watching" tell. `live={false}` for legend dots. |
| `<Bar>` | Severity, shares | Animates to width, so a change is visible not just present. |
| `<LiveFeed>` | Precursor stream, queue | New rows enter from the top with a hi-vis flash and push the rest down. |
| `.scan-sweep` | Panel headers | A sweeping hairline. Reads as monitoring. |
| `.marquee-track` | Alert ticker | Real CUSUM signals, scrolling. Pauses on hover. |
| `.drift` | Background glows | Slow ambient movement so the ground is never flat. |

**Durations:** 0.2–0.5s for state changes, 0.8–1.2s for entrances and bars.
Easing is `[0.22, 1, 0.36, 1]` almost everywhere.

---

## 6. Honesty is a design constraint

These are not decorative choices — they are the reason a domain expert can trust
the screen:

- **The synthetic-data banner is permanent and non-dismissible.** It sits above
  everything in `Topbar`, in `--color-medium`.
- **Loading is never rendered as a value.** `MetricTile` shows `—` and
  `LOADING…` rather than `0`, because a fabricated zero is indistinguishable
  from a real one, and on this console zero means *no precursors*.
- **Offline is never rendered as empty.** `QueryError` distinguishes "the API is
  unreachable" from "the API said no", and prints the command to start the
  backend. There is no silent mock fallback anywhere in the app.
- **Uncalibrated numbers carry an `UNCALIBRATED` chip** and their component
  breakdown, so a composite score is never shown as if it were validated.
- **The SPC method note renders next to the chart**, not in a tooltip someone
  has to hover to find.

---

## 7. Components

`src/components/kinetic/` holds the primitives: `Counter`, `PulseDot`, `Chip`,
`Bar`, `Sparkline`, `ScanPanel`, `PanelHead`, `LiveFeed`, `LoadingRail`,
`Shimmer`, `Stagger`, `LiveClock`.

`src/components/common/QueryState.tsx` holds `PanelLoading`, `QueryError`,
`EmptyPanel`, `NoDataYet` — the three states every panel must handle.

A panel is almost always:

```tsx
<ScanPanel>
  <PanelHead title="SOMETHING" sub="why it matters" right={<Chip>…</Chip>} />
  {isLoading ? <PanelLoading /> : error ? <QueryError error={error} /> : …}
</ScanPanel>
```
