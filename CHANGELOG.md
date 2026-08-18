# Changelog

All notable changes to this project are documented here. This project adheres to
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0]

First public release.

### Added
- Rule layer: eight qualification signals with published thresholds, severity weights and
  plain-language reasons. No dependencies, no training data, usable on day one.
- Cold-start bridge: an optional learned layer blended with the rules at a weight that
  grows with the audit-label count and is capped at 0.75, so the explainable rule floor is
  never lost.
- `verifyscreen` command line: `--out` for a ranked audit worklist, `--summary` for tier
  counts, `--explain` for a full per-signal decomposition of one vendor.
- Reference portfolio of 1,000 simulated vendors generated from a documented process, plus
  two worked examples (a compliant manufacturer and a front).
- Analysis scripts: classifier and robustness study, Monte-Carlo value-leakage model, and
  a parity check between the Python engine and the browser port.
- Browser console served from `docs/`, running the same scoring engine with nothing to
  install.
- Eight tests covering score bounds, decomposition, tier thresholds, blend behaviour and
  the end-to-end command line.
