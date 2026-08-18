# Contributing

Bug reports, threshold arguments and new signals are all welcome.

## Setup

```bash
git clone https://github.com/Jayyp1234/VerifyScreen.git
cd VerifyScreen
python -m venv .venv && source .venv/bin/activate
pip install -e '.[research,dev]'
python -m pytest
```

## Before opening a pull request

```bash
python -m pytest                        # the 8 guarantees must hold
python models/check_browser_parity.py   # Python and the browser port must agree
```

If you change `verifyscreen/rules.py`, the JavaScript port in `docs/scoring.js` has to
change with it, and `docs/npm run check` has to pass. The parity script is what stops the
two drifting.

## Changing a threshold or severity

Thresholds are the argument, not an implementation detail. A pull request that moves one
should say what evidence moves it and what it does to the reference portfolio:

```bash
python models/make_dataset.py
python models/vendor_risk_model.py
```

Include the before-and-after tier counts. A change that flags many more vendors is not
automatically better — audit capacity is the binding constraint, and a screen that flags
everything has triaged nothing.

## Adding a signal

A signal earns its place if it is (a) already collected at qualification, so it costs an
operator nothing to supply, (b) hard for a front to fake without incurring the real cost
it is avoiding, and (c) explainable to a vendor contesting the flag. Signals that fail
(c) do not go in, however predictive they are.

## Scope

VerifyScreen triages. It does not decide, sanction, or score anyone's character. Proposals
that turn a flag into an automatic consequence are out of scope by design.
