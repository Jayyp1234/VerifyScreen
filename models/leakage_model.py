"""What weak enforcement costs, and what credible enforcement recovers.

    python models/leakage_model.py

An illustrative accounting model, not a forecast. Local-content value leaking abroad each
year is the addressable oil-and-gas content base times the share of that value won by
fronts times the fraction they deliver abroad::

    L = B x phi x lambda
    R = L x eta

Every input is swept over a range rather than asserted as a point, and the headline
carries a Monte-Carlo band. The ranges are the author's stated assumptions; they are not
official projections. The result scales linearly in phi, which is the least anchored of
the three, so treat the band as a statement about the assumptions, not about the world.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

SEED = 7
DRAWS = 50_000
OUT = Path(__file__).resolve().parent / "leakage_model.json"

BASE_RANGE = (8.0, 16.0)      # US$bn/yr addressable oil-and-gas content base
FRONT_SHARE_RANGE = (0.12, 0.25)   # share of that value won by front companies
EXPORT_FRACTION_RANGE = (0.55, 0.80)  # fraction a front delivers abroad

# Recovery effectiveness by enforcement scenario. "Enforcement that bites" is set below
# the classifier's demonstrated recall: even a strong screen with finite audit capacity
# and an appeal process does not recover everything it flags.
SCENARIOS = {
    "status_quo": 0.00,
    "audits_without_triage": 0.35,
    "enforcement_that_bites": 0.70,
}


def main() -> int:
    rng = np.random.default_rng(SEED)
    base = rng.uniform(*BASE_RANGE, DRAWS)
    front_share = rng.uniform(*FRONT_SHARE_RANGE, DRAWS)
    export_fraction = rng.uniform(*EXPORT_FRACTION_RANGE, DRAWS)

    leakage = base * front_share * export_fraction
    p10, p50, p90 = (float(np.percentile(leakage, q)) for q in (10, 50, 90))

    print(f"leakage model - {DRAWS:,} draws, seed {SEED}")
    print(f"  B      US${BASE_RANGE[0]:.0f}-{BASE_RANGE[1]:.0f}bn/yr addressable content base")
    print(f"  phi    {FRONT_SHARE_RANGE[0]:.0%}-{FRONT_SHARE_RANGE[1]:.0%} won by fronts")
    print(f"  lambda {EXPORT_FRACTION_RANGE[0]:.0%}-{EXPORT_FRACTION_RANGE[1]:.0%} delivered abroad")
    print()
    print(f"  median leakage   US${p50:.2f}bn/yr")
    print(f"  P10-P90          US${p10:.2f}-{p90:.2f}bn/yr")
    print()

    scenarios = {}
    for name, eta in SCENARIOS.items():
        recovered = leakage * eta
        scenarios[name] = {
            "effectiveness": eta,
            "median_recovered_bn": float(np.median(recovered)),
            "p10_bn": float(np.percentile(recovered, 10)),
            "p90_bn": float(np.percentile(recovered, 90)),
        }
        print(f"  {name:<24} eta {eta:.2f}   recovers US${np.median(recovered):.2f}bn/yr")

    # One-way sensitivity: hold two inputs at their midpoint, sweep the third.
    mid = {k: sum(r) / 2 for k, r in {
        "base": BASE_RANGE,
        "front_share": FRONT_SHARE_RANGE,
        "export_fraction": EXPORT_FRACTION_RANGE,
    }.items()}
    sensitivity = {}
    for name, rng_ in (("base", BASE_RANGE), ("front_share", FRONT_SHARE_RANGE),
                       ("export_fraction", EXPORT_FRACTION_RANGE)):
        others = [v for k, v in mid.items() if k != name]
        low = rng_[0] * others[0] * others[1]
        high = rng_[1] * others[0] * others[1]
        sensitivity[name] = {"low_bn": float(low), "high_bn": float(high),
                             "swing_bn": float(high - low)}
    ranked = sorted(sensitivity.items(), key=lambda kv: -kv[1]["swing_bn"])
    print("\n  one-way sensitivity (swing in median leakage)")
    for name, row in ranked:
        print(f"    {name:<18} US${row['low_bn']:.2f}-{row['high_bn']:.2f}bn "
              f"(swing {row['swing_bn']:.2f})")

    payload = {
        "seed": SEED,
        "draws": DRAWS,
        "inputs": {
            "addressable_base_bn": list(BASE_RANGE),
            "front_value_share": list(FRONT_SHARE_RANGE),
            "export_fraction": list(EXPORT_FRACTION_RANGE),
        },
        "leakage": {"median_bn": p50, "p10_bn": p10, "p90_bn": p90},
        "scenarios": scenarios,
        "sensitivity": sensitivity,
        "note": (
            "Illustrative accounting model on stated assumptions. Not an official "
            "projection. Scales linearly in the front value share, the least anchored input."
        ),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
