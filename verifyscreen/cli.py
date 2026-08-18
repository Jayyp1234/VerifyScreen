"""Command-line interface.

    verifyscreen vendors.csv --out worklist.csv    rank a portfolio into an audit worklist
    verifyscreen vendors.csv --summary             tier counts and the top of the worklist
    verifyscreen vendors.csv --explain V0007       decompose one vendor's score
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .data import load_vendors, write_worklist
from .rules import ELEVATED, HIGH
from .screener import Screener, Verdict

RULE = "-" * 92


def _header(screener: Screener) -> list[str]:
    return [
        f"VerifyScreen {__version__} - vendor integrity screening",
        screener.mode_label,
        "",
    ]


def _table(verdicts: list[Verdict], limit: int) -> list[str]:
    lines = [
        f"{'Rank':>4}  {'Vendor':<38} {'Risk':>6}  {'Tier':<9} Leading red flag",
        RULE,
    ]
    for rank, verdict in enumerate(verdicts[:limit], start=1):
        red = verdict.red_flags
        lead = red[0].rule if red else "-"
        name = verdict.name if len(verdict.name) <= 38 else verdict.name[:37] + "…"
        lines.append(
            f"{rank:>4}  {name:<38} {verdict.score:>6.2f}  {verdict.tier:<9} {lead}"
        )
    if len(verdicts) > limit:
        lines.append(f"{'':>4}  ... {len(verdicts) - limit:,} further vendors not shown")
    return lines


def _summary(verdicts: list[Verdict], screener: Screener) -> list[str]:
    total = len(verdicts)
    high = sum(1 for v in verdicts if v.tier == "HIGH")
    elevated = sum(1 for v in verdicts if v.tier == "ELEVATED")
    low = total - high - elevated
    share = (high / total * 100) if total else 0.0

    lines = _header(screener)
    lines += [
        f"  Screened            {total:>6,} vendors",
        f"  Flagged for audit   {high:>6,}   HIGH       risk >= {HIGH:.2f}",
        f"  Routine             {total - high:>6,}   of which:",
        f"      elevated        {elevated:>6,}   ELEVATED   risk >= {ELEVATED:.2f}",
        f"      low             {low:>6,}   LOW",
        "",
        f"  The audit worklist concentrates on {share:.1f}% of the portfolio.",
        "",
    ]
    lines += _table(verdicts, limit=15)
    return lines


def _explain(verdict: Verdict) -> list[str]:
    lines = [
        f"VerifyScreen {__version__} - vendor verdict",
        "",
        f"  Vendor      {verdict.name} ({verdict.vendor_id})",
        f"  Risk score  {verdict.score:.2f} / 1.00",
        f"  Tier        {verdict.tier}"
        + ("  - audit before award" if verdict.flagged else "  - routine processing"),
    ]
    if verdict.ml_score is not None:
        lines += [
            f"  Composition rule {verdict.rule.score:.2f} "
            f"({1 - verdict.blend_weight:.0%})  +  ml {verdict.ml_score:.2f} "
            f"({verdict.blend_weight:.0%})",
        ]
    lines.append("")

    red = verdict.red_flags
    if not red:
        lines += ["  No material red flags. Every signal is within threshold.", ""]
        return lines

    lines += ["  Red flags driving the score", ""]
    for flag in red:
        lines.append(f"    +{flag.share:.3f}  {flag.rule}")
        lines.append(
            f"            {flag.label} {_num(flag.value)} "
            f"(threshold {_num(_threshold(flag))})"
        )
        for chunk in _wrap(flag.reason, 62):
            lines.append(f"            {chunk}")
        lines.append("")

    lines.append(f"    ------  {verdict.rule.score:.3f}  total rule score")
    clean = len(verdict.flags) - len(red)
    if clean:
        lines.append(f"            {clean} further signal(s) within threshold")
    lines.append("")
    return lines


def _threshold(flag) -> float:
    from .rules import SIGNALS

    return next(s.threshold for s in SIGNALS if s.key == flag.key)


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verifyscreen",
        description=(
            "Screen oil-service vendors for the front-company signature and rank them "
            "into an audit worklist."
        ),
        epilog=(
            "Scores are triage, not verdicts: a flag routes a vendor to a human audit "
            "and an appeal, never to an automatic sanction."
        ),
    )
    parser.add_argument("vendors", type=Path, help="CSV of vendors to screen")
    parser.add_argument("--out", type=Path, metavar="CSV", help="write the ranked worklist to CSV")
    parser.add_argument("--summary", action="store_true", help="print tier counts and the top of the worklist")
    parser.add_argument("--explain", metavar="VENDOR", help="decompose one vendor's score, by id or name")
    parser.add_argument("--top", type=int, default=15, metavar="N", help="rows to print (default: 15)")
    parser.add_argument("--tier", choices=("HIGH", "ELEVATED", "LOW"), help="restrict output to one tier")
    parser.add_argument("--version", action="version", version=f"verifyscreen {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        vendors = load_vendors(args.vendors)
    except (OSError, ValueError) as exc:
        print(f"verifyscreen: {exc}", file=sys.stderr)
        return 2

    screener = Screener()
    verdicts = screener.worklist(vendors)

    if args.explain:
        needle = args.explain.strip().lower()
        match = next(
            (v for v in verdicts if needle in (v.vendor_id.lower(), v.name.lower())),
            None,
        )
        if match is None:
            print(f"verifyscreen: no vendor matching '{args.explain}'", file=sys.stderr)
            return 2
        print("\n".join(_explain(match)))
        return 0

    if args.tier:
        verdicts = [v for v in verdicts if v.tier == args.tier]

    if args.out:
        written = write_worklist(args.out, verdicts)
        print(f"verifyscreen: wrote {written:,} ranked vendors to {args.out}")
        if not args.summary:
            return 0

    if args.summary:
        print("\n".join(_summary(verdicts, screener)))
    else:
        print("\n".join(_header(screener) + _table(verdicts, limit=args.top)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
