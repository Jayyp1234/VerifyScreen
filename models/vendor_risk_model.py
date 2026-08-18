"""Front-company detection as a supervised classification problem.

    python models/vendor_risk_model.py

Trains an interpretable logistic-regression screen on the reference portfolio, compares
it against a gradient-boosted ensemble, measures what the rule layer achieves with no
training data at all, and stress-tests the signal against measurement noise, label noise
and missing fields. Writes every headline number to vendor_risk_metrics.json.

Detection, not prediction. The question "is this vendor a front?" is supervised
classification - the same species of problem as fraud screening - which is what machine
learning genuinely does well. No attempt is made to project outcomes forward in time.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifyscreen.data import reference_vendors
from verifyscreen.rules import SIGNAL_KEYS, SIGNALS, score_vendor

SEED = 42
TEST_SIZE = 0.30
OUT = Path(__file__).resolve().parent / "vendor_risk_metrics.json"

DEGRADATIONS = {
    "measurement_noise": (0.10, 0.25, 0.50),
    "label_noise": (0.10, 0.20, 0.30),
    "missingness": (0.10, 0.30, 0.50),
}
DRAWS = 25


def load():
    vendors = reference_vendors()
    X = np.array([[float(v[k]) for k in SIGNAL_KEYS] for v in vendors])
    y = np.array([int(v["is_front"]) for v in vendors])
    return vendors, X, y


def pipeline(seed=SEED):
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))


def degrade_features(X, kind, level, rng):
    """Corrupt what the regulator observes. Applies to train and test alike."""
    X = X.copy()
    if kind == "measurement_noise":
        return X + rng.normal(0.0, level * X.std(axis=0), X.shape)
    if kind == "missingness":
        mask = rng.random(X.shape) < level
        medians = np.nanmedian(np.where(mask, np.nan, X), axis=0)
        return np.where(mask, medians, X)
    return X


def corrupt_labels(y, level, rng):
    """Corrupt the audit record the model learns from - never the ground truth it is
    scored against. Evaluating on corrupted labels would measure the corruption."""
    y = y.copy()
    flip = rng.random(len(y)) < level
    y[flip] = 1 - y[flip]
    return y


def main() -> int:
    vendors, X, y = load()
    prevalence = float(y.mean())
    print(f"reference portfolio: {len(y):,} vendors, {int(y.sum())} fronts ({prevalence:.1%})\n")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED
    )

    model = pipeline().fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_te, pred).ravel()

    logistic = {
        "roc_auc": float(roc_auc_score(y_te, proba)),
        "pr_auc": float(average_precision_score(y_te, proba)),
        "precision": float(precision_score(y_te, pred)),
        "recall": float(recall_score(y_te, pred)),
        "f1": float(f1_score(y_te, pred)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "test_size": int(len(y_te)),
        "test_fronts": int(y_te.sum()),
    }

    cv = cross_val_score(
        pipeline(), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED), scoring="roc_auc"
    )
    logistic["cv_roc_auc_mean"] = float(cv.mean())
    logistic["cv_roc_auc_sd"] = float(cv.std())

    print("logistic regression (held-out)")
    print(f"  ROC-AUC {logistic['roc_auc']:.4f}   PR-AUC {logistic['pr_auc']:.4f}")
    print(f"  precision {logistic['precision']:.4f}   recall {logistic['recall']:.4f}"
          f"   F1 {logistic['f1']:.4f}")
    print(f"  confusion  TN {tn}  FP {fp}  FN {fn}  TP {tp}   (n={len(y_te)}, fronts={int(y_te.sum())})")
    print(f"  5-fold CV ROC-AUC {cv.mean():.4f} +/- {cv.std():.4f}\n")

    gbt = GradientBoostingClassifier(random_state=SEED).fit(X_tr, y_tr)
    gbt_proba = gbt.predict_proba(X_te)[:, 1]
    gbt_metrics = {
        "roc_auc": float(roc_auc_score(y_te, gbt_proba)),
        "pr_auc": float(average_precision_score(y_te, gbt_proba)),
    }
    print(f"gradient-boosted trees: ROC-AUC {gbt_metrics['roc_auc']:.4f} "
          f"(logistic preferred: same signal, readable coefficients)\n")

    rule_scores = np.array([score_vendor({k: v[k] for k in SIGNAL_KEYS}).score for v in vendors])
    order = np.argsort(-rule_scores)
    top50 = y[order[:50]]
    rules_only = {
        "roc_auc": float(roc_auc_score(y, rule_scores)),
        "pr_auc": float(average_precision_score(y, rule_scores)),
        "precision_at_50": float(top50.mean()),
        "uplift_over_base_rate": float(top50.mean() / prevalence),
        "base_rate": prevalence,
    }
    print("rules-only layer (zero training data)")
    print(f"  ROC-AUC {rules_only['roc_auc']:.4f}")
    print(f"  precision in top-50 flagged {rules_only['precision_at_50']:.0%} "
          f"({rules_only['uplift_over_base_rate']:.1f}x the {prevalence:.0%} base rate)\n")

    hybrid_runs = []
    for seed in range(SEED, SEED + 5):
        Xa, Xb, ya, yb = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=seed)
        ml = pipeline(seed).fit(Xa, ya)
        ml_p = ml.predict_proba(Xb)[:, 1]
        idx = train_test_split(np.arange(len(y)), test_size=TEST_SIZE, stratify=y, random_state=seed)[1]
        rule_p = rule_scores[idx]
        b = min(0.75, 0.75 * (1 - np.exp(-len(ya) / 150.0)))
        hybrid_runs.append(float(roc_auc_score(yb, (1 - b) * rule_p + b * ml_p)))
    hybrid = {
        "roc_auc_mean": float(statistics.mean(hybrid_runs)),
        "roc_auc_min": float(min(hybrid_runs)),
        "roc_auc_max": float(max(hybrid_runs)),
        "blend_weight": float(min(0.75, 0.75 * (1 - np.exp(-700 / 150.0)))),
    }
    print(f"hybrid layer: ROC-AUC {hybrid['roc_auc_mean']:.4f} "
          f"({hybrid['roc_auc_min']:.4f}-{hybrid['roc_auc_max']:.4f} across 5 held-out runs)\n")

    perm = permutation_importance(model, X_te, y_te, n_repeats=30, random_state=SEED, scoring="roc_auc")
    importance = sorted(
        ({"signal": s.label, "key": s.key, "drop": float(m)}
         for s, m in zip(SIGNALS, perm.importances_mean)),
        key=lambda r: -r["drop"],
    )
    print("permutation importance (mean drop in ROC-AUC)")
    for row in importance:
        print(f"  {row['signal']:<30} {row['drop']:.4f}")
    print()

    rng = np.random.default_rng(SEED)
    robustness = {}
    clean = []
    for draw in range(DRAWS):
        Xa, Xb, ya, yb = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED + draw)
        clean.append(roc_auc_score(yb, pipeline().fit(Xa, ya).predict_proba(Xb)[:, 1]))
    robustness["clean"] = {"mean": float(np.mean(clean)), "sd": float(np.std(clean))}
    print(f"robustness (mean +/- SD over {DRAWS} draws)")
    print(f"  clean{'':<26} {np.mean(clean):.4f} +/- {np.std(clean):.4f}")

    for kind, levels in DEGRADATIONS.items():
        robustness[kind] = {}
        for level in levels:
            aucs = []
            for draw in range(DRAWS):
                Xa, Xb, ya, yb = train_test_split(
                    X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED + draw
                )
                if kind == "label_noise":
                    ya = corrupt_labels(ya, level, rng)
                else:
                    Xa = degrade_features(Xa, kind, level, rng)
                    Xb = degrade_features(Xb, kind, level, rng)
                fitted = pipeline().fit(Xa, ya)
                aucs.append(roc_auc_score(yb, fitted.predict_proba(Xb)[:, 1]))
            robustness[kind][f"{level:.2f}"] = {
                "mean": float(np.mean(aucs)),
                "sd": float(np.std(aucs)),
            }
            label = f"{kind} {level:.0%}"
            print(f"  {label:<31} {np.mean(aucs):.4f} +/- {np.std(aucs):.4f}")

    metrics = {
        "seed": SEED,
        "n_vendors": int(len(y)),
        "front_prevalence": prevalence,
        "test_split": TEST_SIZE,
        "logistic_regression": logistic,
        "gradient_boosted_trees": gbt_metrics,
        "rules_only": rules_only,
        "hybrid": hybrid,
        "permutation_importance": importance,
        "robustness": robustness,
    }
    OUT.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
