"""Prove the browser console and the Python engine agree.

    python models/check_browser_parity.py

The web console at docs/ ships a JavaScript port of verifyscreen.rules so that the page
works with nothing installed. A port is a liability unless it is checked: this script
re-scores every vendor in the console's dataset with the Python engine and asserts the
stored scores match. docs/tools/verify.mjs makes the same assertion from the JavaScript
side, so the two implementations are pinned to each other through the shared dataset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifyscreen.rules import SIGNAL_KEYS, score_vendor
from verifyscreen.screener import blend, blend_weight

DATA = Path(__file__).resolve().parent.parent / "docs" / "public" / "data.json"
TOLERANCE = 5e-4


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    meta, vendors = payload["meta"], payload["vendors"]
    weight = blend_weight(meta["n_audits"])

    failures = 0
    checks = 0

    if abs(weight - meta["blend_weight"]) > TOLERANCE:
        print(f"FAIL blend weight: python {weight:.4f} vs data {meta['blend_weight']}")
        failures += 1
    checks += 1

    print(f"{'vendor':<32}{'stored':>9}{'python':>9}{'hybrid':>9}{'python':>9}")
    print("-" * 68)
    for vendor in vendors:
        features = {k: vendor["features"][k] for k in SIGNAL_KEYS}
        result = score_vendor(features)
        hybrid = blend(vendor["rule_score"], vendor["ml_score"], weight)

        for label, got, want in (
            ("rule_score", result.score, vendor["rule_score"]),
            ("hybrid_score", hybrid, vendor["hybrid_score"]),
        ):
            checks += 1
            if abs(got - want) > TOLERANCE:
                print(f"FAIL {vendor['id']} {label}: python {got:.4f} vs data {want}")
                failures += 1

        for label, tier in (("rule_tier", vendor["rule_tier"]), ("hybrid_tier", vendor["hybrid_tier"])):
            checks += 1
            expected = result.tier if label == "rule_tier" else __import__(
                "verifyscreen.rules", fromlist=["tier_of"]
            ).tier_of(hybrid)
            if expected != tier:
                print(f"FAIL {vendor['id']} {label}: python {expected} vs data {tier}")
                failures += 1

        print(f"{vendor['name']:<32}{vendor['rule_score']:>9.4f}{result.score:>9.4f}"
              f"{vendor['hybrid_score']:>9.4f}{hybrid:>9.4f}")

    print("-" * 68)
    print(f"\n{checks} checks, {failures} failure(s).")
    if failures:
        print("PARITY BROKEN - the browser port and the Python engine disagree.")
        return 1
    print("PARITY VERIFIED - the browser console and the Python engine agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
