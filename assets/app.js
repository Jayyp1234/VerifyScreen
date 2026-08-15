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
  var COLOUR = { HIGH: "#dc2626", ELEVATED: "#d97706", LOW: "#16a34a" };
  var ORDER = ["LOW", "ELEVATED", "HIGH"];

  var ICON = {
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">' +
          '<circle cx="12" cy="12" r="9.5"/><path d="M12 11v5.5"/><path d="M12 7.6v.6"/></svg>',
    chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">' +
           '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/></svg>'
  };

  var MODES = {
    A: {
      title: 'Mode A — Rules-Only<span class="dot">•</span><span class="lede">Transparent</span>' +
             '<span class="dot">•</span><span class="lede">Works Day One</span>',
      sub: "Scores are calculated from 8 qualification signals using transparent rules.",
      scoreLabel: "Overall Risk Score (Rules-Only)",
      tableTitle: "Red Flags (Rule Contributions)",
      totalLabel: "Total (Rules-Only)"
    },
    B: {
      title: 'Mode B — Hybrid<span class="dot">•</span><span class="lede">Self-improving</span>' +
             '<span class="dot">•</span><span class="lede">Trained on ' + META.n_audits + ' audits</span>',
      sub: "ML model trained on audited outcomes, blended with rules.",
      scoreLabel: "Overall Risk Score (Hybrid)",
      tableTitle: "Red Flags (Rule Contributions — the transparent floor)",
      totalLabel: "Total (Rule Floor)"
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
  function pct(n) { return Math.round(n * 100); }

  var INT_SIGNAL = {};
  var RANGE = {};
  SIGNALS.forEach(function (s) {
    var vals = VENDORS.map(function (v) { return v.features[s.key]; });
    var isInt = vals.every(function (x) { return Number.isInteger(x); });
    INT_SIGNAL[s.key] = isInt;
    var hi = Math.max.apply(null, vals.concat([s.threshold, s.bound]));
    RANGE[s.key] = { min: 0, max: hi <= 1 ? 1 : isInt ? Math.ceil(hi * 1.15) : Math.ceil(hi * 1.15 * 10) / 10 };
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
        '<td class="vend">' + esc(v.name) + (isEdited(v) ? '<span class="tag-edit">edited</span>' : "") + "</td>" +
        '<td class="score" style="color:' + COLOUR[tier] + '">' + f2(scoreOf(v)) + "</td>" +
        '<td class="tier"><span class="badge ' + tier + '">' + tier + "</span>" + shift + "</td>";

      tbody.appendChild(tr);
    });

    $("wl-empty").hidden = list.length > 0;
    $("wl-count").textContent = list.length === VENDORS.length
      ? "Showing all " + VENDORS.length + " vendors"
      : "Showing " + list.length + " of " + VENDORS.length + " vendors";
  }

  /* -------------------------------------------------------------- verdict */

  function scaleHTML(score) {
    var p = Math.max(0, Math.min(1, score));
    // Stretch the gradient so it always spans the whole track, not just the filled part.
    var bg = p > 0.001 ? ";background-size:" + (100 / p).toFixed(2) + "% 100%" : "";
    return '' +
      '<div class="scale">' +
        '<div class="track"><div class="fill" style="width:' + (p * 100).toFixed(2) + "%" + bg + '"></div></div>' +
        '<div class="ticks"><span style="left:0">0</span><span style="left:40%">0.40</span>' +
          '<span style="left:66%">0.66</span><span style="left:100%">1.00</span></div>' +
        '<div class="zones">' +
          '<span class="z-low" style="flex:0 0 40%">LOW</span>' +
          '<span class="z-mid" style="flex:0 0 26%">ELEVATED</span>' +
          '<span class="z-high" style="flex:1 1 34%">HIGH</span>' +
        "</div>" +
      "</div>";
  }

  function contributionsHTML(v) {
    var bd = E.ruleBreakdown(featuresOf(v), SIGNALS);
    var rows = bd.rows.slice().sort(function (a, b) { return b.share - a.share; });

    var html =
      '<div class="box">' +
        '<div class="bt">' + MODES[state.mode].tableTitle + "</div>" +
        '<table><thead><tr>' +
          '<th scope="col">Signal</th><th scope="col">Value</th>' +
          '<th scope="col" class="num">Contribution</th><th scope="col">Why it matters</th>' +
        "</tr></thead><tbody>";

    rows.forEach(function (r, i) {
      var clean = r.breach <= 0;
      html +=
        '<tr class="' + (clean ? "clean" : "") + '">' +
          '<td><span class="n-circle">' + (i + 1) + '</span><span class="sig">' + esc(r.label) + "</span></td>" +
          '<td class="val">' + fmtVal(r.key, r.value) + '<span class="thr">' + testText(r) + "</span></td>" +
          '<td class="contrib">' + (clean ? "0.000" : "+" + f3(r.share)) + "</td>" +
          '<td class="why">' + (clean ? "Within threshold." : esc(r.reason)) + "</td>" +
        "</tr>";
    });

    return html +
      "</tbody><tfoot><tr>" +
        '<td colspan="2">' + MODES[state.mode].totalLabel + "</td>" +
        '<td class="contrib">+' + f3(bd.score) + "</td>" +
        '<td class="why">&Sigma;(severity &times; breach) &divide; ' + bd.denominator.toFixed(2) + "</td>" +
      "</tr></tfoot></table></div>";
  }

  function namedFlagsHTML(v) {
    if (isEdited(v)) {
      return '<div class="box"><div class="bt">Named Red Flags</div><table><tbody><tr><td class="why">' +
        "Named red flags describe the vendor&rsquo;s filed profile and are not rewritten for what-if edits. " +
        "The per-signal table above is live.</td></tr></tbody></table></div>";
    }
    if (!v.top_flags.length) {
      return '<div class="info calm">' + ICON.info +
        "<div><b>No material red flags.</b> This profile clears every threshold that matters. " +
        "Route to routine processing.</div></div>";
    }
    var html = '<div class="box"><div class="bt">Named Red Flags</div><table><tbody>';
    v.top_flags.forEach(function (f) {
      html += "<tr><td style=\"width:32%\"><span class='sig'>" + esc(f.rule) + "</span></td>" +
        '<td class="why">' + esc(f.reason) + "</td></tr>";
    });
    return html + "</tbody></table></div>";
  }

  // Everything that changes when a what-if value moves. Kept in one container so the
  // what-if inputs themselves are never rebuilt mid-drag.
  function liveHTML(v) {
    var mode = state.mode;
    var rule = ruleOf(v);
    var hyb = hybridOf(v);
    var score = mode === "A" ? rule : hyb;
    var tier = E.tierOf(score);
    var html = "";

    if (mode === "A") {
      html +=
        '<div class="score-row">' +
          "<div>" +
            '<div class="lab">' + MODES.A.scoreLabel + "</div>" +
            '<div class="big" style="color:' + COLOUR[tier] + '">' + f2(score) +
              '<span class="of"> / 1.00</span></div>' +
          "</div>" +
          scaleHTML(score) +
        "</div>";
    } else {
      var was = E.tierOf(rule);
      html +=
        '<div class="trio">' +
          '<div><div class="lab"><b>Rule Score</b> (Transparent Floor)</div>' +
            '<div class="num" style="color:' + COLOUR[E.tierOf(rule)] + '">' + f2(rule) +
              '<span class="of"> / 1.00</span></div>' +
            '<div class="bar"><i style="width:' + pct(rule) + "%;background:" + COLOUR[E.tierOf(rule)] + '"></i></div></div>' +
          '<div><div class="lab"><b>ML Score</b> (Data Learned)</div>' +
            '<div class="num" style="color:' + COLOUR[E.tierOf(v.ml_score)] + '">' + f2(v.ml_score) +
              '<span class="of"> / 1.00</span></div>' +
            '<div class="bar"><i style="width:' + pct(v.ml_score) + "%;background:" + COLOUR[E.tierOf(v.ml_score)] + '"></i></div></div>' +
          '<div><div class="lab"><b>Hybrid Score</b> (Blended)</div>' +
            '<div class="num" style="color:' + COLOUR[tier] + '">' + f2(hyb) +
              '<span class="of"> / 1.00</span></div>' +
            '<div class="bar"><i style="width:' + pct(hyb) + "%;background:" + COLOUR[tier] + '"></i></div></div>' +
        "</div>" +

        '<div class="blend">' +
          '<span class="t">Blend Weight</span>' +
          '<span class="split"><i class="ml" style="width:' + (B * 100).toFixed(1) + '%"></i>' +
            '<i class="rules" style="width:' + ((1 - B) * 100).toFixed(1) + '%"></i></span>' +
          '<span class="k"><b>' + pct(B) + "%</b> ML &nbsp;&middot;&nbsp; <b>" + pct(1 - B) + "%</b> Rules</span>" +
        "</div>" +

        '<div style="margin-top:18px">' + scaleHTML(score) + "</div>";

      if (was !== tier) {
        var worse = ORDER.indexOf(tier) > ORDER.indexOf(was);
        html += '<div class="info ' + (worse ? "warn" : "calm") + '">' + ICON.info +
          "<div><b>Rules alone said " + was + ". The hybrid says " + tier + ".</b> " +
          (worse
            ? "This vendor clears the published thresholds but resembles vendors that failed audit. On rules " +
              "alone it would never have reached the review queue."
            : "The audited record is better than the raw filings suggest, so the screen steps the vendor down.") +
          "</div></div>";
      }
    }

    html += contributionsHTML(v) + namedFlagsHTML(v);

    html += '<div class="info">' + ICON.info + "<div>" +
      (mode === "A"
        ? "Score is the sum of rule contributions. All 8 signals are mapped to JQS/NIPEX data, so every point is " +
          "attributable to a named, published threshold."
        : "Hybrid score = (" + (1 - B).toFixed(2) + " &times; Rule Score) + (" + B.toFixed(2) + " &times; ML Score) = " +
          "<code>" + (1 - B).toFixed(4) + "&middot;" + rule.toFixed(4) + " + " + B.toFixed(4) + "&middot;" +
          v.ml_score.toFixed(4) + " = " + hyb.toFixed(4) + "</code>. The ML weight rises as more audits are " +
          "completed, capped at 0.75. The ML layer returns one score, not per-signal reasons — which is why the " +
          "rules stay in force as the explainable floor.") +
      "</div></div>";

    return html;
  }

  function whatIfHTML(v) {
    var feats = featuresOf(v);
    var html =
      '<div class="whatif">' +
        '<div class="hd"><span class="t">What-if — edit the filed values</span>' +
        '<button type="button" class="btn" id="reset-wi">Reset to filed profile</button></div>' +
        '<p class="warn-txt">The rule score re-computes live from these eight inputs using the same engine that ' +
        "produced the published scores. The ML score stays fixed at its trained value — the model itself is not " +
        "run in the browser.</p>";

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
    E.ruleBreakdown(featuresOf(v), SIGNALS).rows.forEach(function (r) {
      var field = document.querySelector('.field[data-field="' + r.key + '"]');
      if (field) field.classList.toggle("breached", r.breach > 0);
    });
  }

  function announce(v) {
    var score = scoreOf(v);
    $("sr-status").textContent =
      v.name + ": " + MODES[state.mode].scoreLabel + " " + f2(score) + ", " + E.tierOf(score) + " risk.";
  }

  // Called on every what-if keystroke/drag: refresh the numbers, leave the inputs alone.
  function refreshLive() {
    var v = byId[state.selId];
    $("vd-live").innerHTML = liveHTML(v);
    $("vd-edited").hidden = !isEdited(v);
    $("vd-risk").className = "risk-badge badge " + tierOf(v);
    $("vd-risk").textContent = tierOf(v) + " RISK";
    renderWorklist();
    markBreaches(v);
    announce(v);
  }

  function renderVerdict() {
    var v = byId[state.selId];
    var el = $("verdict");
    if (!v) { el.innerHTML = '<h2 class="card-title" id="vd-h">Verdict</h2><p class="empty">Select a vendor.</p>'; return; }

    var tier = tierOf(v);

    el.innerHTML =
      '<div class="vd-head">' +
        '<h2 class="vname" id="vd-h">' + esc(v.name) +
          '<span class="tag-edit" id="vd-edited"' + (isEdited(v) ? "" : " hidden") + ">edited</span></h2>" +
        '<div class="right">' +
          '<button type="button" class="btn" id="toggle-wi" aria-pressed="' + state.whatIf + '">What-if</button>' +
          (state.mode === "B"
            ? '<span class="chip">' + ICON.chart + "Trained on " + META.n_audits +
              " audited vendors &middot; ML weight " + B.toFixed(2) + "</span>"
            : "") +
          '<span class="risk-badge badge ' + tier + '" id="vd-risk">' + tier + " RISK</span>" +
        "</div>" +
      "</div>" +
      '<div id="vd-live">' + liveHTML(v) + "</div>" +
      (state.whatIf ? whatIfHTML(v) : "");

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
    var rows = SIGNALS.map(function (s, i) {
      return "<tr>" +
        '<td><span class="n-circle">' + (i + 1) + '</span><span class="sig">' + esc(s.label) + "</span></td>" +
        '<td class="val">' + testText(s) + '<span class="thr">saturates at ' + fmtVal(s.key, s.bound) + "</span></td>" +
        '<td class="sev">' + s.severity.toFixed(2) + "</td>" +
        '<td class="why">' + esc(s.reason) + "</td>" +
      "</tr>";
    }).join("");

    $("method-body").innerHTML =
      "<p>VerifyScreen ranks vendors by how much a filed profile looks like a vendor that cannot self-deliver the " +
      "work it has won. It is a triage tool: it decides who gets looked at first, not who is guilty.</p>" +

      "<h3>Mode A — Rules-Only</h3>" +
      "<p>Each signal scores a continuous breach between 0 (at or better than the threshold) and 1 (at or past the " +
      "saturation bound), weighted by severity:</p>" +
      "<p><code>rule score = Σ(severity × breach) ÷ Σ(severity)</code></p>" +
      "<p>The denominator is fixed, so each signal's share of the final score is exactly its own contribution — " +
      "which is why the contribution column in the verdict adds up to the score. No training data is required, so " +
      "this mode works on day one.</p>" +

      '<div class="box"><div class="bt">The eight signals</div><table><thead><tr>' +
      '<th scope="col">Signal</th><th scope="col">Test</th><th scope="col" class="num">Severity</th>' +
      '<th scope="col">Why it matters</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +

      "<h3>Mode B — Hybrid</h3>" +
      "<p>Once audits produce labelled outcomes, a logistic-regression model is trained on them and blended with the " +
      "rules. The blend weight is a function of how much evidence exists, not a preference:</p>" +
      "<p><code>b = min(0.75, 0.75·(1 − e^(−N/150)))</code> → at N = " + META.n_audits +
      ", <code>b = " + B.toFixed(4) + "</code><br><code>hybrid = (1 − b)·rule + b·ml</code></p>" +
      "<p>The rules never switch off. They stay a floor and keep supplying the human-readable reasons an officer has " +
      "to give a vendor. The ceiling on <code>b</code> is deliberate: even with unlimited audits, a quarter of the " +
      "score remains rule-driven and explainable. The ML layer returns a single probability, not per-signal " +
      "attributions — the contribution table therefore stays a rules-only breakdown in both modes.</p>" +

      "<h3>What you can check</h3><ul>" +
      "<li>The contribution column in Mode A sums to the displayed rule score.</li>" +
      "<li>In Mode B the printed arithmetic — <code>(1 − b)·Rule + b·ML</code> — equals the displayed hybrid score.</li>" +
      "<li><code>npm run verify</code> re-derives all " + VENDORS.length + " rule scores, the blend weight, the hybrid " +
      "scores and every tier label from the raw feature values, and fails if any of them disagree.</li>" +
      "<li>Open <strong>What-if</strong> on any vendor and move a value: the rule score re-computes with that same engine.</li>" +
      "</ul>";

    $("honesty").innerHTML =
      esc(META.note) + '<hr class="rule">' +
      "The URL tracks the selected vendor and the mode, so any view here can be linked to directly. " +
      "Nothing is uploaded: there is no backend, and every score is either read from a static file or computed in " +
      "your browser." + '<hr class="rule">' +
      'Open source, MIT-licensed — <a href="https://github.com/Jayyp1234/VerifyScreen" target="_blank" ' +
      'rel="noopener">source code and the data behind every score on GitHub</a>. Run ' +
      '<span class="kbd">npm run verify</span> in the repo to re-derive all ' + VENDORS.length +
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
    $("mode-title").innerHTML = MODES[state.mode].title;
    $("mode-sub").textContent = MODES[state.mode].sub;

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
    if (scroll && window.matchMedia("(max-width: 1180px)").matches) {
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

  $("info-btn").addEventListener("click", function () {
    var m = $("method");
    m.open = true;
    m.scrollIntoView({ behavior: "smooth", block: "start" });
  });

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
