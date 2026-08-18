# VerifyScreen browser console

A self-contained two-panel screening console: a ranked vendor worklist on the left, the
selected vendor's decomposed score on the right. Live at
**[jayyp1234.github.io/VerifyScreen](https://jayyp1234.github.io/VerifyScreen/)**.

No build step, no framework, no dependencies at runtime. Open `index.html` directly or
serve the folder.

```bash
npm run serve   # http://localhost:8080
```

## Why the scoring is duplicated here

`scoring.js` is a port of `verifyscreen/rules.py` and `verifyscreen/screener.py`. The
console needs it because the page must work with nothing installed, and browsers block
both `fetch` and ES modules over `file://`.

A port is a liability unless it is checked. Both sides are pinned to the same dataset:

```bash
npm run verify                              # the JavaScript port vs public/data.json
python ../models/check_browser_parity.py    # the Python engine vs public/data.json
```

If either fails, the two engines have drifted and one of them is wrong.

## Editing

`assets/generated.js` is generated — it bundles `public/data.json` and `scoring.js` into
one classic script so the page loads over `file://`. After changing either source:

```bash
npm run check   # regenerate the bundle, then verify it
```

Source files: `index.html` (markup), `assets/styles.css`, `assets/app.js` (UI logic),
`scoring.js` (engine), `public/data.json` (the portfolio).

## Deep links

The URL carries the selected vendor and mode, so any single view can be cited:
`?v=V005&mode=B`.
