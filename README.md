# VerifyScreen — Web Demo (starter kit)

A single-page, no-backend demo of **VerifyScreen**, the vendor-integrity screen from the
Bode Osunkoya 2026 essay *"Enforcement That Bites."* It shows two states of the tool via
one toggle:

- **Mode A — Rules-Only** ("Day One"): transparent red-flag scoring, zero training data.
- **Mode B — Hybrid** ("After Audits"): a logistic-regression ML layer, trained on audit
  outcomes, blended with the rules. The blend weight grows as audits accumulate.

Two-panel layout: **left** = vendor worklist ranked by risk; **right** = the selected
vendor's verdict (score, tier, and the red flags that drove it).

## How to build it with Claude Code (fast path)

1. Open this folder in your terminal and run `claude`.
2. Paste the prompt in `BUILD_PROMPT.md`. It tells Claude Code to build the app against
   the exact spec and the ready-made data.
3. Everything Claude Code needs is already here:
   - `public/data.json` — 12 vendors, each **scored by the real engine** (rules + ML +
     hybrid). Do not recompute these; render them.
   - `scoring.js` — the exact scoring math, if you want live re-scoring when a value is
     edited (optional; the demo works from the precomputed scores alone).
   - `SPEC.md` — the full PRD (layout, modes, colours, definition of done).
4. `index.html` is a minimal working version so you can open it immediately (double-click)
   and see real data before Claude Code polishes the UI.

## Deploy (pick one, both free)
- **GitHub Pages:** push this folder to a repo → Settings → Pages → deploy from `/root` or
  `/public`. Your link: `https://<user>.github.io/<repo>/`.
- **Vercel:** `npx vercel` in this folder, accept defaults. Static; no build step needed.

## Honesty notes (keep these — they are what make it credible)
- Vendor names are **fictitious**; feature profiles are **simulated**.
- Mode A scores are a transparent weighted sum of named red flags.
- Mode B: `hybrid = (1 − b)·rule + b·ml`, with `b = 0.60` at 240 audited vendors
  (`b = min(0.75, 0.75·(1 − e^(−N/150)))`).
- No data leaves the browser; there is no backend.

MIT-licensed, same as the VerifyScreen package.
