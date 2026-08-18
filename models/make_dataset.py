"""Regenerate the bundled reference portfolio and the two worked examples.

    python models/make_dataset.py

Deterministic: same seed, same 1,000 vendors, every time.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifyscreen.data import DATA_DIR, EXAMPLES_CSV, REFERENCE_CSV, simulate_vendors, write_vendors
from verifyscreen.rules import SIGNAL_KEYS
from verifyscreen.screener import Screener

SEED = 42
N = 1000
FRONT_RATE = 0.28

# Two worked profiles used throughout the documentation: a manufacturer that clears every
# threshold, and a front that breaches all eight.
EXAMPLES = [
    {
        "vendor_id": "EX-GENUINE",
        "vendor_name": "Genuine Fabrication Co. Ltd.",
        "capacity_contract_ratio": 1.20,
        "subcontract_share": 0.25,
        "yard_footprint_log": 4.10,
        "tech_staff_per_m": 3.20,
        "jqs_depth": 9.00,
        "expat_ratio": 0.14,
        "ncdf_compliance": 0.95,
        "prior_delivery": 7,
    },
    {
        "vendor_id": "EX-BRIEFCASE",
        "vendor_name": "Briefcase Ventures Ltd.",
        "capacity_contract_ratio": 0.10,
        "subcontract_share": 0.90,
        "yard_footprint_log": 2.00,
        "tech_staff_per_m": 0.35,
        "jqs_depth": 1.50,
        "expat_ratio": 0.58,
        "ncdf_compliance": 0.50,
        "prior_delivery": 0,
    },
]


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    vendors = simulate_vendors(n=N, front_rate=FRONT_RATE, seed=SEED)
    write_vendors(REFERENCE_CSV, vendors)
    fronts = sum(v["is_front"] for v in vendors)
    print(f"{REFERENCE_CSV.name}: {len(vendors):,} vendors, {fronts} fronts "
          f"({fronts / len(vendors):.1%} prevalence), seed {SEED}")

    write_vendors(EXAMPLES_CSV, EXAMPLES)
    screener = Screener()
    for verdict in screener.worklist(EXAMPLES):
        print(f"{EXAMPLES_CSV.name}: {verdict.name:<32} {verdict.score:.4f}  {verdict.tier}")

    counts = {"HIGH": 0, "ELEVATED": 0, "LOW": 0}
    for verdict in screener.worklist(vendors):
        counts[verdict.tier] += 1
    print(f"rules-only tiers: {counts['HIGH']} HIGH / {counts['ELEVATED']} ELEVATED / {counts['LOW']} LOW")
    print(f"                  {counts['HIGH']} flagged for audit, {N - counts['HIGH']} routine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
