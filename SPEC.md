# VerifyScreen Demo — PRD

## Goal
One static page. Two states of VerifyScreen via a Mode A ⟷ Mode B toggle. No backend.

## Data (public/data.json)
- `meta`: {tool, version, n_audits (240), blend_weight (0.60), note, tiers{HIGH:0.66, ELEVATED:0.40}}
- `signals[8]`: {key, label, reason, direction (below/above), threshold, bound, severity}
- `vendors[12]`: {id, name, rule_score, ml_score, hybrid_score, rule_tier, hybrid_tier,
  features{8 keys}, top_flags[{rule, reason, contribution}]}

## Layout
Header: logo "VERIFYSCREEN / Vendor Integrity Screening", a one-line mode subtitle,
mode toggle top-right. Body = two cards:
- LEFT "Vendor Worklist (Ranked by Risk Score)": search + tier filter + sort; table
  Rank | Vendor | Risk Score | Tier. Row click selects.
- RIGHT "Verdict": score + meter (0/0.40/0.66/1.00) + tier badge + red-flag table.

## Modes
- A (Rules-Only): rule_score/rule_tier. Flag table columns: Signal | Value | Contribution |
  Why it matters. Info line: "Score is the weighted sum of rule contributions; all 8 signals
  map to JQS/NIPEX data."
- B (Hybrid): hybrid_score/hybrid_tier, re-sort worklist by hybrid. Verdict shows 3 cards
  (Rule / ML / Hybrid) + chip "Trained on 240 audited vendors · ML weight 0.60" + footer
  "Hybrid = (1 − b)·Rule + b·ML".

## Scoring (only needed if you add editable what-if inputs) — see scoring.js
below(t,floor): v>=t ? 0 : min(1,(t-v)/(t-floor))
above(t,ceil):  v<=t ? 0 : min(1,(v-t)/(ceil-t))
breach_i = test(value_i); rule_score = Σ(sev·breach)/Σ(sev);
contribution_i = sev_i·breach_i / Σ(sev)   # sums to rule_score
blend b = min(0.75, 0.75·(1 − e^(−N/150)));  hybrid = (1−b)·rule + b·ml

## Colours
INK #1a2634 · TEAL #0f6e6e (LOW) · AMBER #d98a00 (ELEVATED) · RUST #b5482f (HIGH) · bg #f4f1ea

## Non-goals
No backend, login, nav rail, KPI cards, Trend column, pagination (<25 rows).
