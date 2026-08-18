"""The learned layer, trained on outcomes from audits an operator already runs.

This module is optional. The rule layer in :mod:`verifyscreen.rules` is the day-one
product and needs nothing beyond the standard library; scikit-learn is required only once
an operator has audit labels to learn from.

Logistic regression is the default on purpose. A gradient-boosted comparison performs
about the same on this problem, so the simpler model wins: its coefficients can be read,
argued with, and put in front of a vendor contesting a flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .rules import SIGNAL_KEYS

__all__ = ["MLModel", "train"]

_IMPORT_HINT = (
    "the learned layer needs scikit-learn - install it with:\n"
    "    pip install 'verifyscreen[ml]'\n"
    "the rule layer (Mode A) runs without it."
)


@dataclass
class MLModel:
    """A fitted front-company classifier over the eight qualification signals."""

    pipeline: object
    keys: tuple[str, ...] = SIGNAL_KEYS
    n_labels: int = 0

    def probability(self, features: Mapping[str, float]) -> float:
        """Probability that this vendor is a front."""
        row = [[float(features[key]) for key in self.keys]]
        return float(self.pipeline.predict_proba(row)[0][1])

    def probabilities(self, records: Sequence[Mapping[str, float]]) -> list[float]:
        """Vectorised form of :meth:`probability`."""
        rows = [[float(r[key]) for key in self.keys] for r in records]
        return [float(p[1]) for p in self.pipeline.predict_proba(rows)]

    @property
    def coefficients(self) -> dict[str, float]:
        """Fitted weight per signal, for inspection."""
        model = self.pipeline[-1]
        return dict(zip(self.keys, (float(c) for c in model.coef_[0])))


def train(
    records: Sequence[Mapping[str, object]],
    labels: Sequence[int],
    seed: int = 42,
) -> MLModel:
    """Fit the learned layer on audited vendors.

    ``records`` are vendor rows; ``labels`` are 1 for a confirmed front, 0 for a vendor
    the audit cleared.
    """
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover - exercised only without sklearn
        raise ImportError(_IMPORT_HINT) from exc

    if len(records) != len(labels):
        raise ValueError("records and labels must be the same length")
    if len(set(labels)) < 2:
        raise ValueError("training needs at least one front and one cleared vendor")

    rows = [[float(r[key]) for key in SIGNAL_KEYS] for r in records]
    pipeline = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=seed),
    )
    pipeline.fit(rows, list(labels))
    return MLModel(pipeline=pipeline, n_labels=len(labels))
