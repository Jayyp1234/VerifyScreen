# Paste this into Claude Code

Build a single-page, static web app (no backend) called the **VerifyScreen demo**, from
the spec in `SPEC.md` and the data in `public/data.json`. Use plain HTML/CSS/vanilla JS
(or React + Vite if you prefer — but keep it deployable as static files). Requirements:

1. Read `public/data.json`. Render a two-panel screen:
   - LEFT: a "Vendor Worklist" table ranked by risk score (Rank, Vendor, Risk Score, Tier
     badge). A search box, a tier filter, and a sort dropdown. Clicking a row selects it.
   - RIGHT: the selected vendor's "Verdict" — the overall score, a horizontal risk meter
     with ticks at 0 / 0.40 / 0.66 / 1.00, a coloured tier badge, and a red-flag table.
2. A top-right toggle **Mode A ⟷ Mode B**:
   - Mode A: use `rule_score` / `rule_tier`; verdict flag table = columns Signal, Value,
     Contribution, "Why it matters" (from each vendor's `top_flags` + `signals` metadata).
   - Mode B: use `hybrid_score` / `hybrid_tier`; show THREE score cards (Rule = rule_score,
     ML = ml_score, Hybrid = hybrid_score), a chip "Trained on {meta.n_audits} audited
     vendors · ML weight {meta.blend_weight}", and a footer line
     "Hybrid = (1 − b)·Rule + b·ML". The worklist re-sorts by hybrid_score in Mode B.
3. Tiers & colours: HIGH ≥ 0.66 (rust #b5482f), ELEVATED ≥ 0.40 (amber #d98a00),
   else LOW (teal #0f6e6e). INK #1a2634 for text, background #f4f1ea.
4. Do NOT invent numbers. Every score is already in data.json — render it. If you add a
   "what-if" mode where the user edits a vendor's 8 feature values, recompute the rule
   score using `scoring.js` (exact engine port) — never guess.
5. Keep a footer with meta.note (fictitious names / simulated profiles).
6. No login, no nav rail, no KPI cards, no "Trend" column, no pagination for <25 rows.

Definition of done: toggling A↔B changes scores/ranking/verdict; clicking a vendor updates
the right panel; in Mode A the contribution column sums to the displayed score; in Mode B
(1−b)·Rule + b·ML equals the displayed Hybrid; opens over file:// with no server.
