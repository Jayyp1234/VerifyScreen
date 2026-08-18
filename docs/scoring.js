// Browser port of verifyscreen/rules.py and verifyscreen/screener.py.
// Kept honest by models/check_browser_parity.py (Python side) and tools/verify.mjs
// (JavaScript side); both assert against public/data.json, so the two engines cannot
// drift apart without a check failing.
export function below(t, floor){ return v => v>=t ? 0 : Math.min(1,(t-v)/(t-floor)); }
export function above(t, ceil){  return v => v<=t ? 0 : Math.min(1,(v-t)/Math.max(ceil-t,1e-6)); }

export function makeTest(sig){ return sig.direction==="below" ? below(sig.threshold, sig.bound)
                                                              : above(sig.threshold, sig.bound); }

// rows: {featureKey: value}; signals: from data.json meta
export function ruleScore(features, signals){
  let num=0, den=0; const flags=[];
  for(const s of signals){
    if(!(s.key in features)) continue;
    const breach = makeTest(s)(features[s.key]);
    den += s.severity; num += s.severity*breach;
    if(breach>0.15) flags.push({rule:s.label, reason:s.reason,
      contribution: +(s.severity*breach).toFixed(3)});
  }
  const score = den ? num/den : 0;
  // normalized contributions sum to the score:
  for(const f of flags) f.share = +(f.contribution/den).toFixed(4);
  flags.sort((a,b)=>b.contribution-a.contribution);
  return { score:+score.toFixed(4), flags:flags.slice(0,8) };
}

// Additive helper (no change to the math above): the full per-signal breakdown.
// `share` is the signal's slice of the final score, so Σ share === ruleScore().score.
export function ruleBreakdown(features, signals){
  let den=0; const rows=[];
  for(const s of signals){
    if(!(s.key in features)) continue;
    const value = features[s.key];
    const breach = makeTest(s)(value);
    den += s.severity;
    rows.push({key:s.key, label:s.label, reason:s.reason, direction:s.direction,
      threshold:s.threshold, bound:s.bound, severity:s.severity, value, breach,
      contribution: s.severity*breach});
  }
  const score = den ? rows.reduce((a,r)=>a+r.contribution,0)/den : 0;
  for(const r of rows) r.share = den ? r.contribution/den : 0;
  return { score, denominator: den, rows };
}

export function blendWeight(nLabels){
  return nLabels<=0 ? 0 : Math.min(0.75, 0.75*(1-Math.exp(-nLabels/150.0)));
}
export function hybrid(rule, ml, b){ return +((1-b)*rule + b*ml).toFixed(4); }
export function tierOf(s){ return s>=0.66 ? "HIGH" : s>=0.40 ? "ELEVATED" : "LOW"; }
