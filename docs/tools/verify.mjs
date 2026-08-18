// Proves the demo does not invent numbers.
//
// Every score rendered in the browser comes from public/data.json, which was produced by
// the Python VerifyScreen engine. This script re-derives those scores in JavaScript with
// scoring.js and asserts they match. If this passes, the browser port and the Python
// engine agree, and the what-if editor can be trusted to re-score live.
//
//   npm run verify
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { ruleScore, ruleBreakdown, blendWeight, hybrid, tierOf } from "../scoring.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const data = JSON.parse(readFileSync(join(ROOT, "public/data.json"), "utf8"));
const { meta, signals, vendors } = data;

const EPS = 5e-4;
let checks = 0, failures = 0;

function ok(label, actual, expected, eps = EPS) {
  checks++;
  const pass = Math.abs(actual - expected) <= eps;
  if (!pass) {
    failures++;
    console.error(`  FAIL ${label}: got ${actual}, expected ${expected}`);
  }
  return pass;
}

function same(label, actual, expected) {
  checks++;
  if (actual !== expected) {
    failures++;
    console.error(`  FAIL ${label}: got ${actual}, expected ${expected}`);
  }
}

console.log(`VerifyScreen — engine verification (${vendors.length} vendors, ${signals.length} signals)\n`);

// 1. Blend weight is a function of the audit count, not a hand-picked constant.
const b = blendWeight(meta.n_audits);
ok(`blendWeight(${meta.n_audits}) == meta.blend_weight`, b, meta.blend_weight);
console.log(`b = min(0.75, 0.75·(1 − e^(−${meta.n_audits}/150))) = ${b.toFixed(4)}  (data.json: ${meta.blend_weight})`);

// 2. Tier thresholds in the data match the ones the engine applies.
same("tier threshold HIGH", meta.tiers.HIGH, 0.66);
same("tier threshold ELEVATED", meta.tiers.ELEVATED, 0.4);

console.log("\nvendor                          rule    recomputed   Σ share   hybrid   recomputed");
console.log("-".repeat(84));

for (const v of vendors) {
  // 3. The rule score is reproducible from the 8 raw feature values.
  const rs = ruleScore(v.features, signals);
  ok(`${v.id} rule_score`, rs.score, v.rule_score);

  // 4. The per-signal contributions sum to the rule score (Mode A's core claim).
  const bd = ruleBreakdown(v.features, signals);
  const shareSum = bd.rows.reduce((a, r) => a + r.share, 0);
  ok(`${v.id} Σ contributions == rule_score`, shareSum, v.rule_score);

  // 5. Hybrid is exactly (1 − b)·rule + b·ml.
  const h = hybrid(v.rule_score, v.ml_score, b);
  ok(`${v.id} hybrid_score`, h, v.hybrid_score);

  // 6. Tier labels follow from the scores.
  same(`${v.id} rule_tier`, tierOf(v.rule_score), v.rule_tier);
  same(`${v.id} hybrid_tier`, tierOf(v.hybrid_score), v.hybrid_tier);

  // 7. Every narrative flag carries a reason the UI can show.
  for (const f of v.top_flags) {
    checks++;
    if (!f.rule || !f.reason || typeof f.contribution !== "number") {
      failures++;
      console.error(`  FAIL ${v.id} malformed top_flag: ${JSON.stringify(f)}`);
    }
  }

  console.log(
    `${v.name.padEnd(30)}  ${v.rule_score.toFixed(4)}  ${rs.score.toFixed(4)}     ` +
    `${shareSum.toFixed(4)}    ${v.hybrid_score.toFixed(4)}   ${h.toFixed(4)}`
  );
}

// 8. Every signal referenced by the UI exists for every vendor.
for (const v of vendors) {
  for (const s of signals) {
    checks++;
    if (!(s.key in v.features)) {
      failures++;
      console.error(`  FAIL ${v.id} missing feature ${s.key}`);
    }
  }
}

console.log("-".repeat(84));
console.log(`\n${checks} checks, ${failures} failure(s).`);
if (failures) {
  console.error("\nVERIFICATION FAILED — do not ship: the browser engine and the data disagree.");
  process.exit(1);
}
console.log("VERIFIED — the browser engine reproduces every score in public/data.json.");
