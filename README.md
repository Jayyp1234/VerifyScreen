# VerifyScreen

**Catch the front company before the contract is awarded.**

[![tests](https://github.com/Jayyp1234/VerifyScreen/actions/workflows/ci.yml/badge.svg)](https://github.com/Jayyp1234/VerifyScreen/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.9%20%E2%80%93%203.13-blue)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![live demo](https://img.shields.io/badge/demo-live-1d4ed8)](https://jayyp1234.github.io/VerifyScreen/)

A local-content law counts contracts, not capability. A company with a registration, a
compliance certificate and no fabrication yard wins a scope, subcontracts the steel to a
yard abroad, and the participation percentage rises while nothing is built at home.

VerifyScreen ranks vendors by how much a filed profile looks like that company. It reads
the eight fields a vendor already submits at qualification, scores each against a
published threshold, and returns a ranked audit worklist with a plain-language reason
attached to every point of every score.

It is a triage tool. A flag routes a vendor to a human audit and an appeal — never to an
automatic sanction.

**[Try it in the browser](https://jayyp1234.github.io/VerifyScreen/)** — no install, the
full screen running on a sample portfolio.

## Install

```bash
pip install verifyscreen
```

Or from source:

```bash
git clone https://github.com/Jayyp1234/VerifyScreen.git
cd VerifyScreen
pip install -e .
```

The screen itself has **no dependencies**. scikit-learn is needed only for the optional
learned layer: `pip install 'verifyscreen[ml]'`.

## Use

```bash
verifyscreen vendors.csv --out worklist.csv
```

Your CSV needs one column per signal (`capacity_contract_ratio`, `subcontract_share`,
`yard_footprint_log`, `tech_staff_per_m`, `jqs_depth`, `expat_ratio`, `ncdf_compliance`,
`prior_delivery`), plus optional `vendor_id` and `vendor_name`.

```
$ verifyscreen vendors.csv --summary

VerifyScreen 0.1.0 - vendor integrity screening
Mode A (rules-only) - no audit labels supplied

  Screened             1,000 vendors
  Flagged for audit       13   HIGH       risk >= 0.66
  Routine                987   of which:
      elevated            63   ELEVATED   risk >= 0.40
      low                924   LOW

  The audit worklist concentrates on 1.3% of the portfolio.

Rank  Vendor                                   Risk  Tier      Leading red flag
--------------------------------------------------------------------------------
   1  Riverside Pipeline Nig. Ltd.             0.83  HIGH      Under-capacity for contract value
   2  Meridian Petroleum Group Ltd.            0.80  HIGH      Under-capacity for contract value
   3  Bayelsa Technical Partners Ltd.          0.75  HIGH      Excessive subcontracting
```

Every score decomposes:

```
$ verifyscreen vendors.csv --explain EX-BRIEFCASE

  Vendor      Briefcase Ventures Ltd. (EX-BRIEFCASE)
  Risk score  0.77 / 1.00
  Tier        HIGH  - audit before award

  Red flags driving the score

    +0.155  Under-capacity for contract value
            Capacity-to-Contract Ratio 0.1 (threshold 0.55)
            Verified fabrication capacity is far below the contract value
            won - the classic sign of winning work that must be built
            elsewhere.

    +0.151  Excessive subcontracting
            Subcontracting Share 0.9 (threshold 0.55)
            Most of the scope is passed to third parties (often abroad),
            so little real value is delivered in-country.
```

The full session is in [`cli_session.txt`](cli_session.txt).

As a library:

```python
from verifyscreen import Screener, load_vendors

for verdict in Screener().worklist(load_vendors("vendors.csv"))[:10]:
    print(f"{verdict.score:.2f}  {verdict.tier:<8}  {verdict.name}")
    for flag in verdict.red_flags:
        print(f"        +{flag.share:.3f}  {flag.rule}")
```

## How it scores

Each signal produces a *breach* between 0 (at or better than the threshold) and 1 (at or
past the saturation bound). The risk score is the severity-weighted mean:

```
rule score = Σ(severity × breach) ÷ Σ(severity)
```

Because the denominator is fixed, each signal's share of the score is exactly its own
contribution — which is why the numbers in `--explain` add up to the score. That is what
makes a flag contestable: a vendor can be shown precisely which field cost it how much.

| Signal | Flags | Severity | What it catches |
|---|---|---|---|
| Capacity-to-Contract Ratio | below 0.55 | 1.00 | Winning work you cannot build |
| Subcontracting Share | above 0.55 | 1.00 | Passing the scope on, often abroad |
| Fabrication Yard Footprint | below 3.2 | 0.80 | An office, not a yard |
| Technical Staff per US$m | below 1.5 | 0.70 | No welders, subsea or QA/QC depth |
| Prior-Delivery Record | below 2 | 0.65 | No comparable completed scopes |
| Expatriate-Quota Ratio | above 0.35 | 0.60 | Skills transfer not happening |
| JQS Depth | below 4.0 | 0.55 | A new or thin vendor |
| NCDF Compliance | below 0.6 | 0.50 | The capability levy going unpaid |

Tiers: **HIGH** ≥ 0.66 (audit before award) · **ELEVATED** ≥ 0.40 · **LOW** below that.

## The cold-start problem

No operator has a labelled register of confirmed front companies on day one, so a
supervised model cannot be trained yet. VerifyScreen is hybrid by design:

**Mode A — rules only.** Runs immediately on data already collected at qualification.
Zero training data, fully explainable, usable the day it is installed.

**Mode B — hybrid.** Once the audits an operator was already going to run produce
outcomes, a model is trained on those labels and blended with the rules. The weight given
to the model is a function of how much evidence exists, not a preference:

```
b = min(0.75, 0.75 × (1 − e^(−n/150)))
hybrid = (1 − b) × rule + b × ml
```

The cap is deliberate. Even with unlimited audit history a quarter of the score stays
rule-driven, so the screen never loses the explainable floor. The tool sharpens with use
and stays defensible throughout.

## Reproducing the analysis

```bash
pip install -e '.[research]'

python models/make_dataset.py           # regenerate the reference portfolio (seed 42)
python models/vendor_risk_model.py      # classifier, robustness → vendor_risk_metrics.json
python models/leakage_model.py          # Monte-Carlo value leakage → leakage_model.json
python models/check_browser_parity.py   # Python engine vs the browser port
python -m pytest                        # 8 tests
```

Everything is seeded, so every run reproduces exactly. Metrics are written to JSON rather
than printed, so they can be diffed between runs.

**On the data.** No public register of confirmed front companies exists — if one did, the
problem would already be solved. The reference portfolio of 1,000 vendors is simulated
from an openly documented process in [`verifyscreen/data.py`](verifyscreen/data.py):
class-conditional normals with deliberate overlap, a spectrum of fronts from blatant to
sophisticated, and 15% of genuine firms understated as small or newly registered. The
class separations are set from an explicit principle — no single filed field may be
decisive — so the screen has to earn its accuracy by combining eight weak-to-moderate
signals, as a real qualification file would force it to.

This demonstrates that the signal is learnable from data operators already collect. It is
not a claim about the behaviour of any real vendor, and the accuracy figures below are
properties of the simulation, not field results. Production accuracy is an empirical
question a pilot would answer.

| | Result |
|---|---|
| Rules only, no training data | ROC-AUC 0.86 · 98% precision in the top-50 flagged (3.5× the base rate) |
| Learned layer, held out | ROC-AUC 0.94 · 5-fold CV 0.954 ± 0.007 |
| Hybrid | ROC-AUC 0.953 (0.934–0.965 across held-out runs) |
| Under ±50% measurement error | 0.930 |
| Under 30% mislabelled audit outcomes | 0.927 |
| With half of all fields missing | 0.878 |

The screen degrades gracefully rather than collapsing, which matters more than the clean
number: real qualification records are incomplete and historical audit outcomes are
sometimes wrong.

## The browser console

[`docs/`](docs/) holds a self-contained two-panel console — a ranked worklist on the
left, the selected vendor's decomposed score on the right — served at
**[jayyp1234.github.io/VerifyScreen](https://jayyp1234.github.io/VerifyScreen/)**.

It runs a JavaScript port of the scoring engine so the page works with nothing installed.
A port is a liability unless it is checked, so both sides are pinned to the same dataset:
`python models/check_browser_parity.py` asserts it from Python, `npm run verify` in
`docs/` asserts it from JavaScript.

## Limitations

- Scores are triage, not verdicts. A flag is the start of an audit, not its conclusion.
- A screen whose rules are public can be gamed. Retrain on audit outcomes, keep some
  features non-public, and audit a control sample of unflagged vendors.
- Small and newly registered firms genuinely look thin. The rules are deliberately
  conservative and the appeal step is not optional — the point is to grow real vendors,
  not to strangle them.
- Garbage in, garbage out: the screen is only as good as the qualification data behind it.

## Repository layout

```
verifyscreen/            the package: rules, blend, CLI, reference data
tests/                   8 tests covering the guarantees above
models/                  the analysis scripts and their JSON outputs
docs/                    the browser console (GitHub Pages)
cli_session.txt          a captured end-to-end session
```

## License

MIT — see [LICENSE](LICENSE). Free for public-sector and commercial use without
restriction.
