"""The behaviour the screen has to keep.

These are the guarantees an operator relies on: that a score is bounded and attributable,
that the decomposition adds up to the number a vendor is shown, that the rule floor is
never lost as the model takes over, and that the command-line tool produces a worklist an
audit team can work from.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from verifyscreen import (
    ELEVATED,
    HIGH,
    SIGNALS,
    Screener,
    blend,
    blend_weight,
    load_vendors,
    score_vendor,
    tier_of,
)
from verifyscreen.cli import main as cli_main
from verifyscreen.data import EXAMPLES_CSV, REFERENCE_CSV
from verifyscreen.rules import MissingSignalError

GENUINE = {
    "capacity_contract_ratio": 1.20,
    "subcontract_share": 0.25,
    "yard_footprint_log": 4.10,
    "tech_staff_per_m": 3.20,
    "jqs_depth": 9.00,
    "expat_ratio": 0.14,
    "ncdf_compliance": 0.95,
    "prior_delivery": 7,
}
BRIEFCASE = {
    "capacity_contract_ratio": 0.10,
    "subcontract_share": 0.90,
    "yard_footprint_log": 2.00,
    "tech_staff_per_m": 0.35,
    "jqs_depth": 1.50,
    "expat_ratio": 0.58,
    "ncdf_compliance": 0.50,
    "prior_delivery": 0,
}


def test_breach_is_bounded_and_respects_direction():
    """A breach runs from 0 at the threshold to 1 at the bound, and never outside."""
    for signal in SIGNALS:
        assert signal.breach(signal.threshold) == 0.0
        assert signal.breach(signal.bound) == pytest.approx(1.0)
        beyond = signal.bound - 1e3 if signal.direction == "below" else signal.bound + 1e3
        assert signal.breach(beyond) == 1.0
        clear = signal.threshold + 1e3 if signal.direction == "below" else signal.threshold - 1e3
        assert signal.breach(clear) == 0.0


def test_a_compliant_vendor_scores_zero_and_a_front_scores_high():
    """The screen must not manufacture risk where no threshold is breached."""
    clean = score_vendor(GENUINE)
    assert clean.score == 0.0
    assert clean.tier == "LOW"
    assert clean.red_flags == ()

    front = score_vendor(BRIEFCASE)
    assert front.tier == "HIGH"
    assert len(front.red_flags) == len(SIGNALS)
    assert 0.0 <= front.score <= 1.0


def test_contributions_sum_to_the_score():
    """The decomposition a vendor is shown must add up to the number it is judged on."""
    for features in (GENUINE, BRIEFCASE):
        result = score_vendor(features)
        assert sum(f.share for f in result.flags) == pytest.approx(result.score, abs=1e-12)
        assert [f.share for f in result.flags] == sorted(
            (f.share for f in result.flags), reverse=True
        )


def test_worked_examples_are_reproducible():
    """The two documented profiles must score what the documentation says they score."""
    vendors = {v["vendor_name"]: v for v in load_vendors(EXAMPLES_CSV)}
    verdicts = {v.name: v for v in Screener().worklist(vendors.values())}

    genuine = verdicts["Genuine Fabrication Co. Ltd."]
    briefcase = verdicts["Briefcase Ventures Ltd."]

    assert round(genuine.score, 2) == 0.00
    assert genuine.tier == "LOW"
    assert round(briefcase.score, 2) == 0.77
    assert briefcase.tier == "HIGH"
    assert briefcase.red_flags[0].rule == "Under-capacity for contract value"
    assert {f.rule for f in briefcase.red_flags} >= {"Excessive subcontracting"}


def test_tiers_follow_the_published_thresholds():
    assert tier_of(HIGH) == "HIGH"
    assert tier_of(HIGH - 1e-9) == "ELEVATED"
    assert tier_of(ELEVATED) == "ELEVATED"
    assert tier_of(ELEVATED - 1e-9) == "LOW"
    assert tier_of(0.0) == "LOW"
    assert tier_of(1.0) == "HIGH"


def test_blend_weight_grows_with_evidence_and_is_capped():
    """The model earns its weight from audits, and never takes the whole score."""
    assert blend_weight(0) == 0.0
    assert blend_weight(-5) == 0.0
    assert blend_weight(240) == pytest.approx(0.5986, abs=5e-4)
    assert blend_weight(10_000) == pytest.approx(0.75)
    weights = [blend_weight(n) for n in (0, 50, 150, 300, 600, 5000)]
    assert weights == sorted(weights)
    assert max(weights) <= 0.75


def test_the_rule_floor_survives_the_model():
    """With no labels the hybrid is the rule score; at the cap a quarter still is."""
    assert blend(0.40, 0.90, blend_weight(0)) == pytest.approx(0.40)
    assert blend(0.40, 0.90, 0.75) == pytest.approx(0.25 * 0.40 + 0.75 * 0.90)

    class AlwaysCertain:
        def probability(self, features):
            return 1.0

    hybrid = Screener(model=AlwaysCertain(), n_labels=10_000).screen(
        {"vendor_id": "V1", "vendor_name": "Test", **GENUINE}
    )
    assert hybrid.rule.score == 0.0
    assert hybrid.score == pytest.approx(0.75)
    assert hybrid.score < 1.0, "a perfectly confident model must not erase the rule floor"

    with pytest.raises(MissingSignalError):
        score_vendor({"capacity_contract_ratio": 0.1})


def test_cli_produces_a_ranked_worklist(tmp_path, capsys):
    """End to end: a CSV of vendors in, a ranked audit worklist out."""
    out = tmp_path / "worklist.csv"
    assert cli_main([str(REFERENCE_CSV), "--out", str(out), "--summary"]) == 0

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 1000
    scores = [float(r["risk_score"]) for r in rows]
    assert scores == sorted(scores, reverse=True), "worklist must be ranked by risk"
    assert rows[0]["tier"] == "HIGH"
    assert all(r["top_flag"] for r in rows if r["tier"] == "HIGH")

    printed = capsys.readouterr().out
    assert "Flagged for audit" in printed
    assert "Mode A (rules-only)" in printed

    assert cli_main([str(REFERENCE_CSV), "--explain", rows[0]["vendor_id"]]) == 0
    assert "Red flags driving the score" in capsys.readouterr().out
