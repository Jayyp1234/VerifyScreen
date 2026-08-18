"""VerifyScreen - vendor integrity screening for local-content enforcement.

Screens oil-service vendors for the front-company signature: winning more contract value
than verified capacity can build, and passing the work on. The rule layer runs on day one
with no training data; a learned layer blends in as audit outcomes accumulate.

    from verifyscreen import Screener, load_vendors

    screener = Screener()
    for verdict in screener.worklist(load_vendors("vendors.csv"))[:10]:
        print(verdict.name, round(verdict.score, 2), verdict.tier)
"""

from .rules import (
    ELEVATED,
    HIGH,
    SIGNALS,
    Flag,
    MissingSignalError,
    RuleResult,
    Signal,
    score_vendor,
    tier_of,
)
from .screener import Screener, Verdict, blend, blend_weight
from .data import load_vendors, reference_vendors, simulate_vendors, write_worklist

__version__ = "0.1.0"

__all__ = [
    "ELEVATED",
    "HIGH",
    "SIGNALS",
    "Flag",
    "MissingSignalError",
    "RuleResult",
    "Screener",
    "Signal",
    "Verdict",
    "blend",
    "blend_weight",
    "load_vendors",
    "reference_vendors",
    "score_vendor",
    "simulate_vendors",
    "tier_of",
    "write_worklist",
    "__version__",
]
