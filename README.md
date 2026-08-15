# VerifyScreen — Web Demo

**Live demo: https://jayyp1234.github.io/VerifyScreen/**

A single-page, no-backend demo of **VerifyScreen**, the vendor-integrity screen from the
Bode Osunkoya 2026 essay *"Enforcement That Bites."* It shows two states of the tool
behind one toggle:

- **Mode A — Rules-Only** ("Day One"): transparent red-flag scoring, zero training data.
- **Mode B — Hybrid** ("After Audits"): a logistic-regression layer trained on audit
  outcomes, blended with the rules. The blend weight grows as audits accumulate.

Two panels: **left** = twelve vendors ranked by risk; **right** = the selected vendor's
verdict — the score, the tier, and every signal that produced it.

The point of the toggle is the vendors that move. *Harcourt Fabrication* scores **0.23
(LOW)** on rules alone and **0.67 (HIGH)** once 240 audits are in the model: it clears
every published threshold but resembles the vendors that failed audit.
[See it](https://jayyp1234.github.io/VerifyScreen/?v=V005&mode=B).

## What's in the demo

| | |
|---|---|
| **Worklist** | 12 vendors, ranked live by the active mode. Search, tier filter, four sorts, keyboard navigation. |
| **Verdict** | Score, risk meter, tier badge, and all eight signals with their individual contributions. |
| **Mode A** | Contribution column adds up to the displayed rule score — nothing is hidden in a black box. |
| **Mode B** | Rule / ML / Hybrid cards, the blend arithmetic printed with real numbers, and a callout on every vendor whose tier the rules alone got wrong. |
| **What-if** | Edit any of the eight filed values and watch the rule score re-compute with the same engine. The ML score stays fixed — the model is not run in the browser. |
| **Deep links** | The URL tracks vendor and mode (`?v=V005&mode=B`), so any single view can be cited directly. |

## Honesty notes

- Vendor names are **fictitious**; feature profiles are **simulated**.
- Mode A scores are a transparent severity-weighted sum of named red flags:
  `rule = Σ(severity × breach) ÷ Σ(severity)`.
- Mode B: `hybrid = (1 − b)·rule + b·ml`, with `b = min(0.75, 0.75·(1 − e^(−N/150)))`,
  so `b = 0.5986` at N = 240 audited vendors. The rules are never switched off.
- No data leaves the browser. There is no backend, no login, and no analytics.

## The scores are checkable

Every number on the page comes from `public/data.json` — produced by the Python
VerifyScreen engine — or is re-derived in the browser by `scoring.js`, an exact port of
that engine. `npm run verify` proves the two agree:

```bash
npm run verify
```

It re-derives all 12 rule scores from the raw feature values, checks that each vendor's
per-signal contributions sum to its rule score, recomputes the blend weight from the audit
count, recomputes every hybrid score, and re-derives every tier label — 181 assertions.
It exits non-zero if anything disagrees.

## Project layout

```
index.html            markup only
assets/styles.css     styles
assets/app.js         UI logic (plain JS, no framework, no dependencies)
assets/generated.js   GENERATED — data.json + scoring.js bundled for the browser
public/data.json      source of truth: 12 vendors scored by the Python engine
scoring.js            source of truth: exact browser port of the scoring math
tools/build.mjs       regenerates assets/generated.js  (npm run sync)
tools/verify.mjs      proves the port reproduces the data (npm run verify)
SPEC.md               the PRD this was built from
```

`assets/generated.js` is committed on purpose: it is what lets the page open with no build
step and no server. After editing `public/data.json` or `scoring.js`, run:

```bash
npm run check
```

which regenerates the bundle and then verifies it.

Nothing is fetched at runtime and no ES modules are used, so `index.html` also opens
directly from the filesystem — the two things browsers block over `file://`.

## Deploy

The repo is a plain static site: no build step, no dependencies, no framework.

- **GitHub Pages** (what the live link uses): Settings → Pages → Deploy from branch →
  `main` / `root`.
- **Vercel:** `npx vercel --prod` in this folder, accept the defaults.
- **Anything else:** copy the folder to any static host.

## Licence

MIT — same as the VerifyScreen package. See [LICENSE](LICENSE).
