/* VerifyScreen demo — UI layer.
 *
 * Every score shown here comes from one of two places, never from this file:
 *   1. public/data.json — produced by the Python VerifyScreen engine.
 *   2. window.VS_ENGINE — the verified browser port of that engine, used only to explain
 *      a score (per-signal breakdown) or to re-score a vendor the user has edited.
 * `npm run verify` asserts that (2) reproduces (1) for all 12 vendors.
 */
(function () {
  "use strict";

  var DATA = window.VS_DATA;
  var E = window.VS_ENGINE;
  if (!DATA || !E) throw new Error("assets/generated.js did not load — run `npm run sync`.");

  var META = DATA.meta;
  var SIGNALS = DATA.signals;
  var VENDORS = DATA.vendors;
  var B = E.blendWeight(META.n_audits); // 0.5986 at 240 audits — derived, not hard-coded
  var COLOUR = { HIGH: "#b5482f", ELEVATED: "#d98a00", LOW: "#0f6e6e" };
  var ORDER = ["LOW", "ELEVATED", "HIGH"];

  var MODES = {
    A: {
      head: 'Mode A &mdash; <span class="tag">Rules-Only</span>',
      sub: "Day one. No training data, no history — just eight qualification signals a vendor already files " +
           "with JQS/NIPEX, each with a published threshold. Every point of every score is attributable to a named red flag.",
      lead: "Rule score"
    },
    B: {
      head: 'Mode B &mdash; <span class="tag">Hybrid</span>',
      sub: "After " + META.n_audits + " audits. A logistic-regression layer trained on audited outcomes is blended " +
           "with the same rules, so the screen keeps its transparent floor and adds what the audits taught it.",
      lead: "Hybrid score"
    }
  };

  /* ---------------------------------------------------------------- state */

  var params = new URLSearchParams(location.search);
  var state = {
    mode: params.get("mode") === "B" ? "B" : "A",
    selId: null,
    query: "",
    tier: "",
    sort: "risk",
    whatIf: false,
    edits: {} // vendorId -> { featureKey: value }
  };

  var byId = {};
  VENDORS.forEach(function (v) { byId[v.id] = v; });
  var wanted = params.get("v");
  state.selId = byId[wanted] ? wanted : null;

  function $(id) { return document.getElementById(id); }

  /* ------------------------------------------------------------- scoring */

  function featuresOf(v) {
    var e = state.edits[v.id];
    if (!e) return v.features;
    var out = {};
    Object.keys(v.features).forEach(function (k) { out[k] = k in e ? e[k] : v.features[k]; });
    return out;
  }

  function isEdited(v) { return !!state.edits[v.id]; }

  // Unedited vendors keep the engine's own published numbers. Edited ones are re-scored live.
  function ruleOf(v) {
    return isEdited(v) ? E.ruleBreakdown(featuresOf(v), SIGNALS).score : v.rule_score;
  }
  function hybridOf(v) {
    return isEdited(v) ? E.hybrid(ruleOf(v), v.ml_score, B) : v.hybrid_score;
  }
  function scoreOf(v) { return state.mode === "A" ? ruleOf(v) : hybridOf(v); }
  function tierOf(v) { return E.tierOf(scoreOf(v)); }

  /* ------------------------------------------------------------ formatting */

  function f2(n) { return n.toFixed(2); }
  function f3(n) { return n.toFixed(3); }

  var INT_SIGNAL = {};
  var RANGE = {};
  SIGNALS.forEach(function (s) {
    var vals = VENDORS.map(function (v) { return v.features[s.key]; });
    var isInt = vals.every(function (x) { return Number.isInteger(x); });
    INT_SIGNAL[s.key] = isInt;
    var hi = Math.max.apply(null, vals.concat([s.threshold, s.bound]));
    var max = hi <= 1 ? 1 : isInt ? Math.ceil(hi * 1.15) : Math.ceil(hi * 1.15 * 10) / 10;
    RANGE[s.key] = { min: 0, max: max };
  });

  function fmtVal(key, v) {
    if (INT_SIGNAL[key]) return String(Math.round(v));
    return v.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  function testText(s) {
    return (s.direction === "below" ? "flags below " : "flags above ") + fmtVal(s.key, s.threshold);
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ------------------------------------------------------------- worklist */

  function visibleVendors() {
    var q = state.query.trim().toLowerCase();
    var list = VENDORS.filter(function (v) {
      if (q && v.name.toLowerCase().indexOf(q) === -1 && v.id.toLowerCase().indexOf(q) === -1) return false;
      if (state.tier && tierOf(v) !== state.tier) return false;
      return true;
    });
    list.sort(function (a, b) {
      switch (state.sort) {
        case "risk-asc": return scoreOf(a) - scoreOf(b);
        case "name": return a.name.localeCompare(b.name);
        case "gap": return (hybridOf(b) - ruleOf(b)) - (hybridOf(a) - ruleOf(a));
        default: return scoreOf(b) - scoreOf(a);
      }
    });
    return list;
  }

  function renderWorklist() {
    var list = visibleVendors();
    var tbody = $("rows");
    tbody.innerHTML = "";

    list.forEach(function (v, i) {
      var tier = tierOf(v);
      var tr = document.createElement("tr");
      tr.className = "row";
      tr.tabIndex = 0;
      tr.setAttribute("aria-selected", v.id === state.selId ? "true" : "false");
      tr.dataset.id = v.id;

      // In Hybrid mode, mark the vendors whose tier the rules alone got wrong.
      var shift = "";
      if (state.mode === "B") {
        var was = E.tierOf(ruleOf(v));
        if (was !== tier) {
          var worse = ORDER.indexOf(tier) > ORDER.indexOf(was);
          shift = '<span class="shift' + (worse ? "" : " down") +
            '" title="Rules alone put this vendor in ' + was + '">' +
            (worse ? "↑" : "↓") + " from " + was + "</span>";
        }
      }

      tr.innerHTML =
        '<td class="rank">' + (i + 1) + "</td>" +
        '<td class="vend">' + esc(v.name) +
          (isEdited(v) ? '<span class="edited">edited</span>' : "") +
          '<span class="id">' + v.id + "</span></td>" +
        '<td class="score num" style="color:' + COLOUR[tier] + '">' + f2(scoreOf(v)) + "</td>" +
        '<td><span class="badge" style="background:' + COLOUR[tier] + '">' + tier + "</span>" + shift + "</td>";

      tbody.appendChild(tr);
    });

    $("wl-empty").hidden = list.length > 0;
    $("wl-count").textContent = list.length === VENDORS.length
      ? VENDORS.length + " vendors"
      : list.length + " of " + VENDORS.length + " vendors";
  }

  /* -------------------------------------------------------------- verdict */

  function meterHTML(score, ghost) {
    return '' +
      '<div class="meter">' +
        '<div class="track"><i class="zone low"></i><i class="zone mid"></i><i class="zone high"></i></div>' +
        '<div class="fill" style="width:' + (score * 100) + '%;background:' + COLOUR[E.tierOf(score)] + '"></div>' +
        (ghost == null ? "" :
          '<div class="ghost" style="left:' + (ghost * 100) + '%" title="Rule-only score: ' + f2(ghost) + '"></div>') +
        '<div class="needle" style="left:' + (score * 100) + '%"></div>' +
      "</div>" +
      '<div class="ticks"><span style="left:0">0</span><span style="left:40%">0.40</span>' +
      '<span style="left:66%">0.66</span><span style="left:100%">1.00</span></div>';
  }

  function breakdownHTML(v) {
    var bd = E.ruleBreakdown(featuresOf(v), SIGNALS);
    var maxShare = Math.max.apply(null, bd.rows.map(function (r) { return r.share; }).concat([1e-4]));
    var rows = bd.rows.slice().sort(function (a, b) { return b.share - a.share; });

    var html =
      '<table class="bd"><thead><tr>' +
        '<th scope="col">Signal</th><th scope="col">Value</th>' +
        '<th scope="col" class="num">Contribution</th><th scope="col">Why it matters</th>' +
      "</tr></thead><tbody>";

    rows.forEach(function (r) {
      var clean = r.breach <= 0;
      html +=
        '<tr class="' + (clean ? "clean" : "") + '">' +
          '<td class="sig">' + esc(r.label) + "</td>" +
          '<td class="val">' + fmtVal(r.key, r.value) + '<span class="thr">' + testText(r) + "</span></td>" +
          '<td class="contrib">' +
            '<span class="n" style="color:' + (clean ? "var(--muted)" : "var(--rust)") + '">' +
              (clean ? "0.000" : "+" + f3(r.share)) + "</span>" +
            '<span class="bar"><i style="width:' + (r.share / maxShare * 100).toFixed(1) + '%"></i></span>' +
          "</td>" +
          '<td class="why">' + (clean ? "Within threshold." : esc(r.reason)) + "</td>" +
        "</tr>";
    });

    return html +
      "</tbody><tfoot><tr>" +
        '<td class="lbl" colspan="2">Rule score = &Sigma; contributions</td>' +
        '<td class="contrib"><span class="n">' + f3(bd.score) + "</span></td>" +
        '<td class="why">&Sigma;(severity &times; breach) &divide; ' + bd.denominator.toFixed(2) + "</td>" +
      "</tr></tfoot></table>";
  }

  function flagsHTML(v) {
    if (isEdited(v)) {
      return '<p class="note" style="margin:0">Named red flags describe the vendor&rsquo;s filed profile and are ' +
        "not rewritten for what-if edits. The per-signal table above is live.</p>";
    }
    if (!v.top_flags.length) {
      return '<div class="callout calm">✓ <b>No material red flags.</b> This profile clears every threshold ' +
        "that matters. Route to routine processing.</div>";
    }
    var html = '<table class="bd"><tbody>';
    v.top_flags.forEach(function (f) {
      html += "<tr>" +
        '<td class="sig" style="width:32%">' + esc(f.rule) + "</td>" +
        '<td class="why">' + esc(f.reason) + "</td>" +
      "</tr>";
    });
    return html + "</tbody></table>";
  }

  // Everything that changes when a what-if value moves. Kept in one container so the
  // what-if inputs themselves are never rebuilt mid-drag.
  function liveHTML(v) {
    var mode = state.mode;
    var rule = ruleOf(v);
    var hyb = hybridOf(v);
    var score = mode === "A" ? rule : hyb;
    var tier = E.tierOf(score);

    var html =
      '<div class="gauge">' +
        '<div class="big" style="color:' + COLOUR[tier] + '">' + f2(score) + '<span class="of"> / 1.00</span></div>' +
        '<div class="tierbadge" style="background:' + COLOUR[tier] + '">' + tier + " RISK</div>" +
        meterHTML(score, mode === "B" ? rule : null) +
        '<div class="caption">' +
          (mode === "B"
            ? "Black marker = hybrid. Grey marker = where the rules alone put this vendor (" + f2(rule) + ")."
            : "HIGH ≥ 0.66 &middot; ELEVATED ≥ 0.40 &middot; below that, LOW.") +
        "</div>" +
      "</div>";

    if (mode === "B") {
      var was = E.tierOf(rule);
      html +=
        '<div class="cards3">' +
          '<div class="mini"><div class="lab">Rule (floor)</div><div class="num">' + f2(rule) +
            '</div><div class="note">8 signals</div></div>' +
          '<div class="mini"><div class="lab">ML (learned)</div><div class="num">' + f2(v.ml_score) +
            '</div><div class="note">' + META.n_audits + " audits</div></div>" +
          '<div class="mini lead"><div class="lab">Hybrid</div><div class="num" style="color:' + COLOUR[tier] + '">' +
            f2(hyb) + '</div><div class="note">what the screen reports</div></div>' +
        "</div>" +

        '<div class="formula">' +
          "b = min(0.75, 0.75·(1 − e^(−" + META.n_audits + "/150))) = <b>" + B.toFixed(4) + "</b><br>" +
          "Hybrid = (1 − b)·Rule + b·ML = " + (1 - B).toFixed(4) + "·" + rule.toFixed(4) +
          " + " + B.toFixed(4) + "·" + v.ml_score.toFixed(4) + " = <b>" + hyb.toFixed(4) + "</b>" +
        "</div>" +

        '<p style="margin:12px 0 0"><span class="chip ink">Trained on ' + META.n_audits +
          " audited vendors &middot; ML weight " + META.blend_weight.toFixed(2) + "</span></p>";

      if (was !== tier) {
        var worse = ORDER.indexOf(tier) > ORDER.indexOf(was);
        html += '<div class="callout' + (worse ? "" : " calm") + '">' +
          "<b>Rules alone said " + was + ". The hybrid says " + tier + ".</b> " +
          (worse
            ? "This vendor clears the published thresholds but resembles vendors that failed audit. On rules " +
              "alone it would never have reached the review queue."
            : "The audited record is better than the raw filings suggest, so the screen steps the vendor down.") +
          "</div>";
      }
    }

    return html +
      '<h3 class="sect-h">' + (mode === "A" ? "Why this score — all eight signals" : "The rule floor — all eight signals") + "</h3>" +
      breakdownHTML(v) +
      '<h3 class="sect-h">Named red flags</h3>' +
      flagsHTML(v);
  }

  function whatIfHTML(v) {
    var feats = featuresOf(v);
    var html =
      '<div class="whatif">' +
        '<div class="hd"><span class="t">What-if — edit the filed values</span>' +
        '<button type="button" class="btn ghost" id="reset-wi">Reset to filed profile</button></div>' +
        '<p class="warn">The rule score re-computes live from these eight inputs using the same engine that ' +
        "produced the published scores. The ML score stays fixed at its trained value — the model itself is " +
        "not run in the browser.</p>";

    SIGNALS.forEach(function (s) {
      var r = RANGE[s.key];
      var val = feats[s.key];
      html +=
        '<div class="field" data-field="' + s.key + '">' +
          '<label class="fl" for="wi-' + s.key + '"><span>' + esc(s.label) + "</span>" +
            '<span class="rule">' + testText(s) + "</span></label>" +
          '<input type="range" id="wi-' + s.key + '" data-key="' + s.key + '" min="' + r.min +
            '" max="' + r.max + '" step="any" value="' + val + '" aria-label="' + esc(s.label) + '">' +
          '<input type="number" data-key="' + s.key + '" min="' + r.min + '" max="' + r.max +
            '" step="' + (INT_SIGNAL[s.key] ? 1 : 0.01) + '" value="' + fmtVal(s.key, val) +
            '" aria-label="' + esc(s.label) + ' value">' +
        "</div>";
    });

    return html + "</div>";
  }

  function markBreaches(v) {
    var bd = E.ruleBreakdown(featuresOf(v), SIGNALS);
    bd.rows.forEach(function (r) {
      var field = document.querySelector('.field[data-field="' + r.key + '"]');
      if (field) field.classList.toggle("breached", r.breach > 0);
    });
  }

  // Called on every what-if keystroke/drag: refresh the numbers, leave the inputs alone.
  function refreshLive() {
    var v = byId[state.selId];
    $("vd-live").innerHTML = liveHTML(v);
    $("vd-edited").hidden = !isEdited(v);
    renderWorklist();
    markBreaches(v);
    announce(v);
  }

  function announce(v) {
    var score = scoreOf(v);
    $("sr-status").textContent =
      v.name + ": " + MODES[state.mode].lead + " " + f2(score) + ", " + E.tierOf(score) + " risk.";
  }

  function renderVerdict() {
    var v = byId[state.selId];
    var el = $("verdict");
    if (!v) { el.innerHTML = '<h2 id="vd-h">Verdict</h2><p class="empty">Select a vendor.</p>'; return; }

    el.innerHTML =
      '<div class="verdict-head">' +
        '<div class="who">' +
          '<h2 id="vd-h" class="vname">' + esc(v.name) +
            '<span class="edited" id="vd-edited"' + (isEdited(v) ? "" : " hidden") + ">edited</span></h2>" +
          '<div class="vid">' + v.id + " &middot; " + MODES[state.mode].lead + "</div>" +
        "</div>" +
        '<button type="button" class="btn" id="toggle-wi" aria-pressed="' + state.whatIf + '">What-if</button>' +
      "</div>" +
      '<div id="vd-live">' + liveHTML(v) + "</div>" +
      (state.whatIf ? whatIfHTML(v) : "") +
      '<p class="note" style="margin-top:16px">' +
        (state.mode === "A"
          ? "Every point above is a weighted rule breach; all eight signals map to fields a vendor already files with JQS/NIPEX."
          : "Hybrid = (1 − b)·Rule + b·ML. The rules stay in force as a floor — the ML layer can raise a " +
            "score, and the reasons above still explain the rule half.") +
      "</p>";

    $("toggle-wi").addEventListener("click", function () {
      state.whatIf = !state.whatIf;
      renderVerdict();
      if (state.whatIf) {
        var first = document.querySelector(".whatif input[type=range]");
        if (first) first.focus();
      }
    });

    if (state.whatIf) wireWhatIf(v);
    announce(v);
  }

  function wireWhatIf(v) {
    $("reset-wi").addEventListener("click", function () {
      delete state.edits[v.id];
      renderVerdict();
      renderWorklist();
    });

    document.querySelectorAll(".whatif input").forEach(function (input) {
      input.addEventListener("input", function () {
        var key = input.dataset.key;
        var raw = parseFloat(input.value);
        if (!isFinite(raw)) return; // mid-typing ("", "-", "0.")

        var r = RANGE[key];
        var val = Math.min(r.max, Math.max(r.min, raw));
        val = INT_SIGNAL[key] ? Math.round(val) : Math.round(val * 1000) / 1000;

        if (!state.edits[v.id]) state.edits[v.id] = {};
        state.edits[v.id][key] = val;

        // Drop the override entirely once every value is back to the filed profile.
        var e = state.edits[v.id];
        if (Object.keys(e).every(function (k) { return e[k] === v.features[k]; })) delete state.edits[v.id];

        // Mirror the value into the paired control without disturbing the one in use.
        document.querySelectorAll('.whatif input[data-key="' + key + '"]').forEach(function (other) {
          if (other === input) return;
          other.value = other.type === "number" ? fmtVal(key, val) : val;
        });

        refreshLive();
      });
    });

    markBreaches(v);
  }

  /* ---------------------------------------------------------- methodology */

  function renderMethodology() {
    var rows = SIGNALS.map(function (s) {
      return "<tr>" +
        '<td class="sig">' + esc(s.label) + "</td>" +
        '<td class="val">' + testText(s) + '<span class="thr">saturates at ' + fmtVal(s.key, s.bound) + "</span></td>" +
        '<td class="contrib"><span class="n">' + s.severity.toFixed(2) + "</span></td>" +
        '<td class="why">' + esc(s.reason) + "</td>" +
      "</tr>";
    }).join("");

    $("method-body").innerHTML =
      "<p>VerifyScreen ranks vendors by how much a filed profile looks like a vendor that cannot self-deliver the " +
      "work it has won. It is a triage tool: it decides who gets looked at first, not who is guilty.</p>" +

      "<h3>Mode A &mdash; Rules-Only</h3>" +
      "<p>Each signal scores a continuous breach between 0 (at or better than the threshold) and 1 (at or past the " +
      "saturation bound), weighted by severity:</p>" +
      "<p><code>rule score = Σ(severity × breach) ÷ Σ(severity)</code></p>" +
      "<p>The denominator is fixed, so each signal's share of the final score is exactly its own contribution &mdash; " +
      "which is why the contribution column in the verdict adds up to the score. No training data is required, so " +
      "this mode works on day one.</p>" +

      '<table class="bd"><thead><tr><th scope="col">Signal</th><th scope="col">Test</th>' +
      '<th scope="col" class="num">Severity</th><th scope="col">Why it matters</th></tr></thead><tbody>' +
      rows + "</tbody></table>" +

      "<h3>Mode B &mdash; Hybrid</h3>" +
      "<p>Once audits produce labelled outcomes, a logistic-regression model is trained on them and blended with the " +
      "rules. The blend weight is a function of how much evidence exists, not a preference:</p>" +
      "<p><code>b = min(0.75, 0.75·(1 − e^(−N/150)))</code> &rarr; at N = " + META.n_audits +
      ", <code>b = " + B.toFixed(4) + "</code><br><code>hybrid = (1 − b)·rule + b·ml</code></p>" +
      "<p>The rules never switch off. They stay a floor and keep supplying the human-readable reasons an officer has " +
      "to give a vendor. The ceiling on <code>b</code> is deliberate: even with unlimited audits, a quarter of the " +
      "score remains rule-driven and explainable.</p>" +

      "<h3>What you can check</h3><ul>" +
      "<li>The contribution column in Mode A sums to the displayed rule score.</li>" +
      "<li>In Mode B the printed arithmetic &mdash; <code>(1 − b)·Rule + b·ML</code> &mdash; equals the displayed hybrid score.</li>" +
      "<li><code>npm run verify</code> re-derives all " + VENDORS.length + " rule scores, the blend weight, the hybrid " +
      "scores and every tier label from the raw feature values, and fails if any of them disagree.</li>" +
      "<li>Open <strong>What-if</strong> on any vendor and move a value: the rule score re-computes with that same engine.</li>" +
      "</ul>";

    $("honesty").innerHTML =
      esc(META.note) + '<hr class="rule">' +
      "<strong>Keyboard:</strong> <span class=\"kbd\">↑</span> <span class=\"kbd\">↓</span> move through the " +
      'worklist &middot; <span class="kbd">m</span> switch mode &middot; <span class="kbd">/</span> search. ' +
      "The URL tracks the selected vendor and the mode, so any view here can be linked to directly. " +
      "Nothing is uploaded: there is no backend, and every score is either read from a static file or computed in your browser." +
      '<hr class="rule">' +
      'Open source, MIT-licensed &mdash; <a href="https://github.com/Jayyp1234/VerifyScreen" ' +
      'target="_blank" rel="noopener">source code and the data behind every score on GitHub</a>. ' +
      "Run <span class=\"kbd\">npm run verify</span> in the repo to re-derive all " + VENDORS.length +
      " scores from the raw feature values.";
  }

  /* ----------------------------------------------------------------- glue */

  function syncURL() {
    var p = new URLSearchParams();
    if (state.selId) p.set("v", state.selId);
    if (state.mode !== "A") p.set("mode", state.mode);
    var q = p.toString();
    try {
      history.replaceState(null, "", q ? "?" + q : location.pathname);
    } catch (_) { /* file:// in some browsers refuses replaceState — harmless */ }
  }

  function render() {
    document.body.dataset.mode = state.mode;
    $("btn-A").setAttribute("aria-pressed", String(state.mode === "A"));
    $("btn-B").setAttribute("aria-pressed", String(state.mode === "B"));
    $("banner-head").innerHTML = MODES[state.mode].head;
    $("banner-sub").textContent = MODES[state.mode].sub;

    if (!state.selId || !byId[state.selId]) state.selId = (visibleVendors()[0] || VENDORS[0]).id;

    renderWorklist();
    renderVerdict();
    syncURL();
  }

  function setMode(m) {
    if (state.mode === m) return;
    state.mode = m;
    render();
  }

  function select(id, scroll) {
    if (!byId[id] || id === state.selId) return;
    state.selId = id;
    render();
    if (scroll && window.matchMedia("(max-width: 1000px)").matches) {
      $("verdict").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function move(delta) {
    var list = visibleVendors();
    if (!list.length) return;
    var i = list.findIndex(function (v) { return v.id === state.selId; });
    var next = list[Math.max(0, Math.min(list.length - 1, i < 0 ? 0 : i + delta))];
    select(next.id, false);
    var row = document.querySelector('tr.row[data-id="' + next.id + '"]');
    if (row) row.focus();
  }

  $("btn-A").addEventListener("click", function () { setMode("A"); });
  $("btn-B").addEventListener("click", function () { setMode("B"); });

  $("q").addEventListener("input", function (e) { state.query = e.target.value; renderWorklist(); });
  $("tier-filter").addEventListener("change", function (e) { state.tier = e.target.value; renderWorklist(); });
  $("sort").addEventListener("change", function (e) { state.sort = e.target.value; renderWorklist(); });

  $("rows").addEventListener("click", function (e) {
    var tr = e.target.closest("tr.row");
    if (tr) select(tr.dataset.id, true);
  });

  $("rows").addEventListener("keydown", function (e) {
    var tr = e.target.closest("tr.row");
    if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); select(tr.dataset.id, true); }
  });

  document.addEventListener("keydown", function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var t = e.target;
    var typing = t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA");

    if (e.key === "/" && !typing) { e.preventDefault(); $("q").focus(); return; }
    if (e.key === "Escape" && t === $("q")) { t.value = ""; state.query = ""; renderWorklist(); return; }
    if (typing) return;
    if (e.key === "m" || e.key === "M") { setMode(state.mode === "A" ? "B" : "A"); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
  });

  renderMethodology();
  render();
})();
