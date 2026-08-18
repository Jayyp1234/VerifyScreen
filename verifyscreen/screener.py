"""The cold-start bridge: rules on day one, blended ML as audit labels accumulate.

No operator has a labelled register of confirmed front companies on day one, so a
supervised model cannot be trained yet. VerifyScreen therefore runs the transparent rule
layer immediately and folds in a learned model only as the audits an operator was already
going to run produce outcomes.

The blend weight is a function of how much evidence exists, not a preference::

    b = min(0.75, 0.75 * (1 - exp(-n / 150)))
    hybrid = (1 - b) * rule + b * ml

The cap is deliberate. Even with unlimited audit history a quarter of the score stays
rule-driven, so the screen never loses the explainable floor a vendor can contest.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, Sequence

from .rules import SIGNALS, Flag, RuleResult, Signal, score_vendor, tier_of

__all__ = [
    "BLEND_CAP",
    "BLEND_SCALE",
    "Verdict",
    "Screener",
    "blend_weight",
    "blend",
]

BLEND_CAP = 0.75
BLEND_SCALE = 150.0


class ProbabilityModel(Protocol):
    """Anything that can turn a vendor's filed values into a front-company probability."""

    def probability(self, features: Mapping[str, float]) -> float: ...


def blend_weight(n_labels: int) -> float:
    """Weight given to the learned model after ``n_labels`` audited outcomes."""
    if n_labels <= 0:
        return 0.0
    return min(BLEND_CAP, BLEND_CAP * (1.0 - math.exp(-n_labels / BLEND_SCALE)))


def blend(rule_score: float, ml_score: float, weight: float) -> float:
    """Combine the rule floor with the learned score at ``weight``."""
    return (1.0 - weight) * rule_score + weight * ml_score


@dataclass(frozen=True)
class Verdict:
    """What the screen returns for one vendor."""

    vendor_id: str
    name: str
    rule: RuleResult
    ml_score: float | None
    blend_weight: float
    score: float
    tier: str

    @property
    def flags(self) -> tuple[Flag, ...]:
        return self.rule.flags

    @property
    def red_flags(self) -> tuple[Flag, ...]:
        return self.rule.red_flags

    @property
    def flagged(self) -> bool:
        return self.tier == "HIGH"


class Screener:
    """Screen vendors and rank them into an audit worklist.

    With no model supplied the screen runs in Mode A: rules only, usable on day one.
    Supply a model trained on audit outcomes and it runs in Mode B, blending the two at a
    weight set by ``n_labels``.
    """

    def __init__(
        self,
        signals: Sequence[Signal] = SIGNALS,
        model: ProbabilityModel | None = None,
        n_labels: int = 0,
    ) -> None:
        self.signals = tuple(signals)
        self.model = model
        self.n_labels = int(n_labels)
        self.weight = blend_weight(n_labels) if model is not None else 0.0

    @property
    def mode(self) -> str:
        return "B" if self.model is not None else "A"

    @property
    def mode_label(self) -> str:
        if self.model is None:
            return "Mode A (rules-only) - no audit labels supplied"
        return (
            f"Mode B (hybrid) - {self.n_labels:,} audited outcomes, "
            f"ML weight {self.weight:.2f}"
        )

    def screen(self, vendor: Mapping[str, object]) -> Verdict:
        """Screen a single vendor record."""
        features = {s.key: float(vendor[s.key]) for s in self.signals if s.key in vendor}
        rule = score_vendor(features, self.signals)

        ml_score = None
        score = rule.score
        if self.model is not None:
            ml_score = float(self.model.probability(features))
            score = blend(rule.score, ml_score, self.weight)

        return Verdict(
            vendor_id=str(vendor.get("vendor_id", "")),
            name=str(vendor.get("vendor_name", "")),
            rule=rule,
            ml_score=ml_score,
            blend_weight=self.weight,
            score=score,
            tier=tier_of(score),
        )

    def worklist(self, vendors: Iterable[Mapping[str, object]]) -> list[Verdict]:
        """Screen every vendor and return them ranked by risk, highest first."""
        verdicts = [self.screen(v) for v in vendors]
        verdicts.sort(key=lambda v: (-v.score, v.name))
        return verdicts
