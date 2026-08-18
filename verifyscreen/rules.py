"""Transparent red-flag rules for vendor-integrity screening.

The rule layer has no dependencies and needs no training data. Each of the eight signals
is a field a vendor already files at JQS/NIPEX qualification, carries a published
threshold, and produces a plain-language reason an auditor can act on and a vendor can
contest.

A signal scores a *breach* in [0, 1]: zero at or better than the threshold, rising
linearly to one at the saturation bound. A vendor's risk score is the severity-weighted
mean of its eight breaches, so the score is bounded in [0, 1] and every point of it is
attributable to exactly one named signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

__all__ = [
    "Signal",
    "Flag",
    "RuleResult",
    "SIGNALS",
    "HIGH",
    "ELEVATED",
    "MissingSignalError",
    "tier_of",
    "score_vendor",
]

HIGH = 0.66
ELEVATED = 0.40

BELOW = "below"
ABOVE = "above"


class MissingSignalError(KeyError):
    """Raised when a vendor record is missing one of the eight required signals."""

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = tuple(missing)
        super().__init__(
            "vendor record is missing required signal(s): " + ", ".join(self.missing)
        )


@dataclass(frozen=True)
class Signal:
    """One qualification signal, its published threshold, and what breaching it means."""

    key: str
    label: str
    rule: str
    reason: str
    direction: str
    threshold: float
    bound: float
    severity: float

    def breach(self, value: float) -> float:
        """Return this signal's breach for ``value``, in [0, 1]."""
        if self.direction == BELOW:
            if value >= self.threshold:
                return 0.0
            span = self.threshold - self.bound
            if span <= 0:
                return 1.0
            return min(1.0, (self.threshold - value) / span)

        if value <= self.threshold:
            return 0.0
        span = max(self.bound - self.threshold, 1e-6)
        return min(1.0, (value - self.threshold) / span)

    def describe(self) -> str:
        edge = "below" if self.direction == BELOW else "above"
        return f"flags {edge} {_trim(self.threshold)}"


# The eight signals. Thresholds are set at the point a profile stops being explicable by
# ordinary small-firm variation; bounds are the point past which further deterioration
# tells us nothing new. Severity weights the classic briefcase signature -- winning more
# work than you can build, and passing it on -- above the supporting evidence.
SIGNALS: tuple[Signal, ...] = (
    Signal(
        key="capacity_contract_ratio",
        label="Capacity-to-Contract Ratio",
        rule="Under-capacity for contract value",
        reason=(
            "Verified fabrication capacity is far below the contract value won - the "
            "classic sign of winning work that must be built elsewhere."
        ),
        direction=BELOW,
        threshold=0.55,
        bound=0.05,
        severity=1.00,
    ),
    Signal(
        key="subcontract_share",
        label="Subcontracting Share",
        rule="Excessive subcontracting",
        reason=(
            "Most of the scope is passed to third parties (often abroad), so little "
            "real value is delivered in-country."
        ),
        direction=ABOVE,
        threshold=0.55,
        bound=0.95,
        severity=1.00,
    ),
    Signal(
        key="yard_footprint_log",
        label="Fabrication Yard Footprint",
        rule="No real fabrication yard",
        reason="Registered fabrication footprint is negligible - an office, not a yard.",
        direction=BELOW,
        threshold=3.20,
        bound=1.80,
        severity=0.80,
    ),
    Signal(
        key="tech_staff_per_m",
        label="Technical Staff per US$m",
        rule="Too few technical staff",
        reason=(
            "Welders, subsea and QA/QC headcount per US$m of contract is far too low "
            "to self-deliver."
        ),
        direction=BELOW,
        threshold=1.50,
        bound=0.20,
        severity=0.70,
    ),
    Signal(
        key="jqs_depth",
        label="JQS Depth",
        rule="Shallow qualification history",
        reason=(
            "Little registered depth in the JQS/NIPEX databank - a new or thin vendor."
        ),
        direction=BELOW,
        threshold=4.00,
        bound=0.50,
        severity=0.55,
    ),
    Signal(
        key="expat_ratio",
        label="Expatriate-Quota Ratio",
        rule="Heavy expatriate dependence",
        reason=(
            "Expatriate quota use is high for the scope, so the skills transfer the "
            "Act exists to force is not happening."
        ),
        direction=ABOVE,
        threshold=0.35,
        bound=0.90,
        severity=0.60,
    ),
    Signal(
        key="ncdf_compliance",
        label="NCDF Compliance",
        rule="Weak NCDF compliance",
        reason=(
            "Nigerian Content Development Fund remittances are partial or lapsed - the "
            "levy that funds capability building is not being paid."
        ),
        direction=BELOW,
        threshold=0.60,
        bound=0.10,
        severity=0.50,
    ),
    Signal(
        key="prior_delivery",
        label="Prior-Delivery Record",
        rule="No delivery track record",
        reason="Few or no completed comparable oil-and-gas scopes.",
        direction=BELOW,
        threshold=2.00,
        bound=0.00,
        severity=0.65,
    ),
)

SIGNAL_KEYS: tuple[str, ...] = tuple(s.key for s in SIGNALS)


@dataclass(frozen=True)
class Flag:
    """One signal's verdict on one vendor."""

    key: str
    label: str
    rule: str
    reason: str
    value: float
    breach: float
    severity: float
    contribution: float
    share: float

    @property
    def flagged(self) -> bool:
        return self.breach > 0.0


@dataclass(frozen=True)
class RuleResult:
    """A vendor's rule score with the full per-signal decomposition behind it."""

    score: float
    tier: str
    denominator: float
    flags: tuple[Flag, ...]

    @property
    def red_flags(self) -> tuple[Flag, ...]:
        """Only the signals the vendor actually breached, worst first."""
        return tuple(f for f in self.flags if f.flagged)


def tier_of(score: float) -> str:
    """Map a risk score to its audit tier."""
    if score >= HIGH:
        return "HIGH"
    if score >= ELEVATED:
        return "ELEVATED"
    return "LOW"


def score_vendor(
    features: Mapping[str, float],
    signals: Iterable[Signal] = SIGNALS,
) -> RuleResult:
    """Score one vendor from its eight filed values.

    The returned ``share`` values sum to ``score``, which is what makes the screen
    contestable: a vendor can be shown exactly which signal cost it how much.
    """
    signals = tuple(signals)
    missing = [s.key for s in signals if s.key not in features]
    if missing:
        raise MissingSignalError(missing)

    denominator = sum(s.severity for s in signals)
    if denominator <= 0:
        raise ValueError("signal severities must sum to a positive number")

    flags = []
    for signal in signals:
        value = float(features[signal.key])
        breach = signal.breach(value)
        contribution = signal.severity * breach
        flags.append(
            Flag(
                key=signal.key,
                label=signal.label,
                rule=signal.rule,
                reason=signal.reason,
                value=value,
                breach=breach,
                severity=signal.severity,
                contribution=contribution,
                share=contribution / denominator,
            )
        )

    score = sum(f.contribution for f in flags) / denominator
    flags.sort(key=lambda f: (-f.share, f.key))
    return RuleResult(
        score=score,
        tier=tier_of(score),
        denominator=denominator,
        flags=tuple(flags),
    )


def _trim(value: float) -> str:
    """Format a threshold without trailing zeros."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")
