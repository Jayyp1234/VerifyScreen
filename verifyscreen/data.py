"""Vendor records: reading them, writing worklists, and the reference simulation.

No public register of confirmed front companies exists - if one did, the problem would
already be solved. The reference dataset here is therefore simulated from an openly
documented process, so that anyone can regenerate it, inspect the assumptions, and
disagree with them. It demonstrates that the signal is learnable from data operators
already collect at qualification. It is not a claim about any real vendor.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from .rules import SIGNAL_KEYS

__all__ = [
    "DATA_DIR",
    "REFERENCE_CSV",
    "FeatureSpec",
    "GENUINE_PROFILE",
    "FRONT_PROFILE",
    "load_vendors",
    "reference_vendors",
    "simulate_vendors",
    "write_vendors",
    "write_worklist",
]

DATA_DIR = Path(__file__).resolve().parent / "data"
REFERENCE_CSV = DATA_DIR / "vendors_reference.csv"
EXAMPLES_CSV = DATA_DIR / "vendors_examples.csv"


# --------------------------------------------------------------------------- reading


def load_vendors(path: str | Path) -> list[dict[str, object]]:
    """Read vendor records from a CSV.

    Required columns are the eight signal keys. ``vendor_id`` and ``vendor_name`` are
    used for display when present; ``is_front`` is read as a label when present.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"{path} contains no vendor rows")

    missing = [key for key in SIGNAL_KEYS if key not in rows[0]]
    if missing:
        raise ValueError(
            f"{path} is missing required column(s): {', '.join(missing)}\n"
            f"expected: {', '.join(SIGNAL_KEYS)}"
        )

    vendors: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        record: dict[str, object] = {
            "vendor_id": row.get("vendor_id") or f"V{index:04d}",
            "vendor_name": row.get("vendor_name") or f"Vendor {index}",
        }
        for key in SIGNAL_KEYS:
            raw = row[key]
            if raw is None or raw == "":
                raise ValueError(f"{path} row {index}: empty value for '{key}'")
            record[key] = float(raw)
        if row.get("is_front") not in (None, ""):
            record["is_front"] = int(float(row["is_front"]))
        vendors.append(record)
    return vendors


def reference_vendors() -> list[dict[str, object]]:
    """The bundled 1,000-vendor reference portfolio."""
    return load_vendors(REFERENCE_CSV)


# --------------------------------------------------------------------------- writing


def write_vendors(path: str | Path, vendors: Sequence[Mapping[str, object]]) -> None:
    """Write vendor records to CSV."""
    labelled = any("is_front" in v for v in vendors)
    columns = ["vendor_id", "vendor_name", *SIGNAL_KEYS] + (["is_front"] if labelled else [])
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for vendor in vendors:
            writer.writerow({c: vendor.get(c, "") for c in columns})


def write_worklist(path: str | Path, verdicts: Iterable) -> int:
    """Write a ranked audit worklist to CSV. Returns the number of rows written."""
    columns = [
        "rank",
        "vendor_id",
        "vendor_name",
        "risk_score",
        "tier",
        "rule_score",
        "ml_score",
        "top_flag",
        "top_flag_contribution",
        "red_flag_count",
    ]
    count = 0
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for rank, verdict in enumerate(verdicts, start=1):
            red = verdict.red_flags
            writer.writerow(
                {
                    "rank": rank,
                    "vendor_id": verdict.vendor_id,
                    "vendor_name": verdict.name,
                    "risk_score": f"{verdict.score:.4f}",
                    "tier": verdict.tier,
                    "rule_score": f"{verdict.rule.score:.4f}",
                    "ml_score": "" if verdict.ml_score is None else f"{verdict.ml_score:.4f}",
                    "top_flag": red[0].rule if red else "",
                    "top_flag_contribution": f"{red[0].share:.4f}" if red else "",
                    "red_flag_count": len(red),
                }
            )
            count += 1
    return count


# ------------------------------------------------------------------------ simulation


@dataclass(frozen=True)
class FeatureSpec:
    """Class-conditional normal for one signal, clipped to a physical range."""

    mean: float
    sd: float
    low: float
    high: float
    integer: bool = False

    def draw(self, rng: random.Random) -> float:
        value = min(self.high, max(self.low, rng.gauss(self.mean, self.sd)))
        return float(round(value)) if self.integer else round(value, 3)


# Class-conditional normals. The separations below are set from an explicit principle:
# no single filed field may be decisive. Each signal alone distinguishes a front from a
# genuine firm at roughly AUC 0.72-0.85 (Cohen's d of 0.8-1.4), so the screen has to earn
# its accuracy by combining eight weak-to-moderate signals - which is what a real
# qualification file offers. A simulation in which one field gives the answer away would
# flatter any classifier and teach nothing.
#
# A genuine firm holds fabrication capacity roughly proportional to the contracts it wins,
# keeps most of the scope in-house, and has a registered history to show for it.
GENUINE_PROFILE: dict[str, FeatureSpec] = {
    "capacity_contract_ratio": FeatureSpec(1.00, 0.45, 0.05, 2.50),
    "subcontract_share": FeatureSpec(0.42, 0.18, 0.00, 1.00),
    "yard_footprint_log": FeatureSpec(3.70, 0.75, 1.00, 5.60),
    "tech_staff_per_m": FeatureSpec(2.60, 1.20, 0.00, 8.00),
    "jqs_depth": FeatureSpec(7.50, 3.20, 0.00, 15.0),
    "expat_ratio": FeatureSpec(0.24, 0.12, 0.00, 1.00),
    "ncdf_compliance": FeatureSpec(0.76, 0.18, 0.00, 1.00),
    "prior_delivery": FeatureSpec(4.20, 2.60, 0.00, 12.0, integer=True),
}

# A front wins value it cannot deliver and subcontracts the work abroad. Note how much
# the distributions overlap: plenty of fronts file numbers a struggling genuine firm
# could also file. That overlap is the whole difficulty of the problem.
FRONT_PROFILE: dict[str, FeatureSpec] = {
    "capacity_contract_ratio": FeatureSpec(0.55, 0.35, 0.05, 2.50),
    "subcontract_share": FeatureSpec(0.68, 0.18, 0.00, 1.00),
    "yard_footprint_log": FeatureSpec(2.95, 0.75, 1.00, 5.60),
    "tech_staff_per_m": FeatureSpec(1.50, 1.00, 0.00, 8.00),
    "jqs_depth": FeatureSpec(4.60, 2.80, 0.00, 15.0),
    "expat_ratio": FeatureSpec(0.36, 0.14, 0.00, 1.00),
    "ncdf_compliance": FeatureSpec(0.60, 0.20, 0.00, 1.00),
    "prior_delivery": FeatureSpec(2.30, 2.00, 0.00, 12.0, integer=True),
}

# Fronts are not one population. The typology runs from a firm that is thinly
# capitalised but real, through the ordinary middleman, to the case in the literature: a
# registration, a compliance certificate, and no welding bench. Modelling them as a
# single cloud makes the easy cases and the hard cases equally likely, which is not what
# a regulator's inbox looks like.
BLATANT_FRONT_RATE = 0.20        # a desk and a certificate: breaches nearly every threshold
SOPHISTICATED_FRONT_RATE = 0.20  # rents a yard and pads the staff roll to pass inspection
UNDERSTATED_GENUINE_RATE = 0.15  # a real but small or newly registered firm that looks thin

_BLATANT_SHIFT = {
    "capacity_contract_ratio": -0.37,
    "subcontract_share": +0.20,
    "yard_footprint_log": -0.85,
    "tech_staff_per_m": -1.05,
    "jqs_depth": -2.80,
    "expat_ratio": +0.16,
    "ncdf_compliance": -0.18,
    "prior_delivery": -1.90,
}
_SOPHISTICATED_SHIFT = {
    "capacity_contract_ratio": +0.30,
    "yard_footprint_log": +0.80,
    "tech_staff_per_m": +1.20,
    "jqs_depth": +2.80,
    "ncdf_compliance": +0.18,
}
_UNDERSTATED_SHIFT = {
    "capacity_contract_ratio": -0.35,
    "yard_footprint_log": -0.70,
    "jqs_depth": -3.50,
    "prior_delivery": -2.50,
}

_FIRST = (
    "Delta", "Oceanic", "Westfield", "Primewell", "Harcourt", "Seabright", "Meridian",
    "Coastline", "Atlas", "Riverside", "Bonny", "Escravos", "Qua Iboe",
    "Forcados", "Brass", "Calabar", "Onne", "Warri", "Bayelsa", "Akwa", "Rivers",
    "Niger", "Gulf", "Trident", "Anchor", "Beacon", "Summit", "Vanguard", "Pinnacle",
    "Crestline", "Northgate", "Southfield", "Eastport", "Westgate", "Highland",
)
_MIDDLE = (
    "Offshore", "Marine", "Subsea", "Fabrication", "Energy", "Petroleum", "Oilfield",
    "Technical", "Engineering", "Integrated", "Industrial", "Drilling", "Pipeline",
    "Process", "Maritime",
)
_LAST = (
    "Ltd.", "Nig. Ltd.", "Services Ltd.", "Solutions Ltd.", "Company Ltd.",
    "Partners Ltd.", "Group Ltd.", "Systems Ltd.",
)


def _names(rng: random.Random, count: int) -> list[str]:
    """Distinct, obviously fictitious vendor names."""
    seen: set[str] = set()
    names: list[str] = []
    while len(names) < count:
        name = f"{rng.choice(_FIRST)} {rng.choice(_MIDDLE)} {rng.choice(_LAST)}"
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def simulate_vendors(
    n: int = 1000,
    front_rate: float = 0.28,
    seed: int = 42,
) -> list[dict[str, object]]:
    """Generate the reference portfolio from the documented process.

    Classes are drawn from overlapping class-conditional normals. Roughly 15% of genuine
    firms are understated as small or newly registered, and roughly 20% of fronts are
    sophisticated enough to mimic real capacity, so the classes overlap and the screen
    errs the way a real one does.

    Every value is simulated and labelled as such. It shows the signal is learnable; it
    is not a claim about the behaviour of any real vendor.
    """
    if not 0.0 < front_rate < 1.0:
        raise ValueError("front_rate must be between 0 and 1")

    rng = random.Random(seed)
    names = _names(random.Random(seed + 1), n)

    # Draw an exact count rather than a coin flip per vendor. A reference fixture should
    # realise its stated prevalence exactly, so that anyone regenerating it gets the same
    # portfolio composition and not a binomial neighbour of it.
    n_fronts = round(n * front_rate)
    labels = [1] * n_fronts + [0] * (n - n_fronts)
    rng.shuffle(labels)

    vendors: list[dict[str, object]] = []

    for index, label in enumerate(labels):
        is_front = bool(label)
        profile = FRONT_PROFILE if is_front else GENUINE_PROFILE

        shift: Mapping[str, float] = {}
        if is_front:
            roll = rng.random()
            if roll < BLATANT_FRONT_RATE:
                shift = _BLATANT_SHIFT
            elif roll < BLATANT_FRONT_RATE + SOPHISTICATED_FRONT_RATE:
                shift = _SOPHISTICATED_SHIFT
        elif rng.random() < UNDERSTATED_GENUINE_RATE:
            shift = _UNDERSTATED_SHIFT

        record: dict[str, object] = {
            "vendor_id": f"V{index + 1:04d}",
            "vendor_name": names[index],
        }
        for key, spec in profile.items():
            if key in shift:
                spec = FeatureSpec(
                    mean=spec.mean + shift[key],
                    sd=spec.sd,
                    low=spec.low,
                    high=spec.high,
                    integer=spec.integer,
                )
            record[key] = spec.draw(rng)
        record["is_front"] = int(is_front)
        vendors.append(record)

    return vendors
