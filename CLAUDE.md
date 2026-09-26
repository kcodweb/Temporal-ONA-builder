# CLAUDE.md — Temporal ONA builder

Project brief for Claude Code. Read this before changing anything.

## What this is

A browser tool that turns a coded self-regulated learning (SRL) episode log into a **temporal ordered network**: one figure that shows how long learners spent in each behaviour, when in the session each behaviour happened, what followed what, and when each link happened.

- **Author:** Karan Bansal, IIT Bombay.
- **Origin:** a design question in ET 610, Learning Analytics and Educational Data Mining. The question asked how to add time spent and timing to an ENA/ONA co-occurrence network of SRL behaviours (Planning, Monitoring, Debugging, Help seeking, Evaluation) in a 60-minute programming lab.
- **Status:** working v0.1. It has been published once as a Claude artifact and is being prepared as a public website (GitHub Pages).

**Audience.** Learning analytics researchers and instructors.

**Positioning (keep this wording consistent everywhere).** The tool is *ONA-inspired*: it uses ordered network analysis's ground→response connection logic over a moving window. It is a descriptive visualisation, **not** a full ONA: there is no normalisation, dimensional reduction or statistical comparison. Never describe it as an ONA implementation.

## Repository layout

```
index.html                 the entire tool: HTML + CSS + JS in one file, no build step
README.md                  public-facing readme (usage, deploy, privacy, cite)
CLAUDE.md                  this file
preview.png                example figure used in README
package.json               dev tooling only (jsdom for tests/scripts)
tests/smoke.test.js        jsdom smoke tests that run the real page script (npm test)
scripts/export-figures.js  exports figure SVGs from the real page (npm run figures)
samples/sample-srl-log.csv built-in synthetic sample (30 learners, seed 610)
docs/white-paper-v1.html   first white paper draft (self-contained, figures embedded as WebP)
```

Keep `index.html` as a **single self-contained file**. If you refactor into modules, add a build step that still emits one `index.html`, and keep tests running against the built file.

## Commands

```
npm install          # jsdom only
npm test             # 14 smoke tests; must pass before any commit
npm run figures      # writes figures/*.svg (whole-timeline, whole-colour, frame-1..6)
npm run sample       # rewrites samples/sample-srl-log.csv from the page's generator
```

`figures/` is git-ignored. To convert SVG to PNG: `python -m cairosvg figures/whole-timeline.svg -o fig1.png -W 1600`.

## Input format

CSV, TSV or semicolon-separated text with a header row. Columns are matched case-insensitively via `ALIASES`.

| Column | Required | Accepted names | Notes |
|---|---|---|---|
| learner | yes | learner, student, student_id, user_id, participant, id … | pseudonymous IDs recommended |
| behaviour | yes | behaviour, behavior, activity, action, code, state, event … | grouped case-insensitively; first spelling is kept |
| start | yes | start, start_time, begin, timestamp, time … | minutes (`12.5`), `mm:ss`, `hh:mm:ss`, or anything `Date.parse` accepts |
| end | no | end, end_time, stop, finish … | if missing, an episode ends at the learner's next start |

**Known ambiguity:** a two-part time such as `09:12` is read as **mm:ss**, not hh:mm. The UI tells users to add `:00`.

## Code map (inside the `<script>` of index.html)

The code is ES5-style inside an IIFE, with no dependencies. Sections, in order:

1. **Helpers:** `esc`, `clamp`, `fmt` (1 dp below 100), `fmtMin`, `unit`, `f1`. `PR` = `'\u2032'` (prime for minutes).
2. **Constants:** `ALIASES`, `DEF` (default settings), node palettes `NODE_LIGHT`/`NODE_DARK`, time ramps `RAMP_LIGHT`/`RAMP_DARK` (violet → magenta → amber), ring width `RW = 6`.
3. **State:** `S` (settings), `P` (parsed log), `D` (derived: `seqs`, `links`, `L` = session length), `view` (`{t0, t1, frame}` where frame `-1` = whole, `-2` = custom), `selected` node, `downloads` (Claude capability or null).
4. **Colour/theme:** `tokens()` reads CSS variables so SVG gets literal colours, which exported files need.
5. **Parsing:** `splitRow`, `normH`, `parseTime`; `readTable(text)` returns `{delim, names, hdr, rows, nums}`; `autoMap(hdr)` guesses the column for each of `ROLES` via `ALIASES`; `parseRows(tb, idx)` returns `{ev, behaviours, counts, learners, clock, skipped, bad, hasEnd, rows, two, neg}` or `{error}` (`two` = rows with `mm:ss`-style times, `neg` = episodes ending before they start). `parseLog(text, idx?)` chains them.
6. **Derive:** `derive()` sorts each learner's episodes, fills missing ends, aligns (per learner to 0′ if `S.align`, else global min for clock data), optionally merges back-to-back repeats, sets `L` (auto = ceil to slice, or `S.sessionLen`), and builds `links`: for each episode *i*, a link from each of the previous `w−1` episodes; `time` = response start, `dur` = response duration.
7. **Compute:** `compute(t0, t1)` returns minutes per behaviour in the window, per-slice minutes (`slc`) and shares (`shr`), and aggregated edges `{f, t, w, mean, bins[]}` filtered by `S.loops` and `S.minShare`.
8. **Geometry:** `layoutNodes` (fixed circle; first behaviour at top, clockwise in order of first appearance), `edgeGeom` (quadratic curve offset to the left of direction, so reciprocal edges separate), `loopGeom`, `qpt`/`cpt` (quadratic/cubic points), `arcPath`, `swellSegs`.
9. **Draw:** `drawFigure(c)` builds the whole SVG as a string. It contains the background rect, title, colour bar (top right), edges, nodes (track ring, slice arcs, disc, selection ring), loops, labels (halo drawn as a duplicate stroked text **behind** the text, *not* `paint-order`, so exports render in cairosvg), and footer insights. `insights(c)` produces the three footer sentences.
10. **Side panels:** `drawDetail` (selected node: minutes, busiest slice, histogram, top next/before links), `drawLegend`.
11. **Window UI:** `buildFrames`, `syncWindowUI`, `setFrame`, `togglePlay` (1.6 s per frame), dual range slider (`#r0`, `#r1`).
12. **Data flow and steps:** the page has three stages, `#stage-start` (upload: drop zone, file input, paste box, sample, template), `#stage-check` (column selects `#map-*`, preview table, summary tiles, behaviour chips, warnings) and `#stage-explore` (settings, figure, legend, detail). `showStage(s, focus)` switches them and the step buttons in the app bar. `analyse(text, name, idx)` fills `pending` and draws the check step (`drawCheck`); `build(fromUser)` turns `pending` into `P` and opens the explore step; `rederive()`, `readSettingsUI`/`writeSettingsUI`, `applyTheme`. First visits open on the upload step; a saved log opens straight on its figure. Storage keys: `tona-data`, `tona-name`, `tona-map` (column names per role), `tona-settings-v2`, all wrapped in try/catch.
13. **Sample:** `mulberry32(610)` plus `sampleCSV()`, which generates phase-weighted synthetic data. **Do not change the seed or generator** without updating the tests and the white paper numbers.
14. **Export:** `svgString`, `savePNG` (SVG → canvas at 2×), `saveFile`, which uses the Claude `downloads` capability when running as a Claude artifact and `browserSave` (Blob + `<a download>`) when standalone. `TEMPLATE` is the small CSV behind **Download template**; elements marked `data-save` appear only when saving works.
15. **Init:** event wiring.

## Formulas (keep code, legend and paper consistent)

For behaviour *b*, window length *T*, *N* learners, per-learner scope (class-total scope drops the 1/*N*):

- minutes: `m_b = (1/N) Σ overlap(episode, window)`
- disc: `share = m_b / T`, `r = max(3, rMax·√share)`, `rMax = min(92, 0.88·R·sin(π/max(B,3)))`, with `R = 212` (165 if B ≤ 2)
- ring arc opacity: `0.12 + 0.88 · p_bk / max(p)`, where `p_bk = Σ overlap(episode, slice k) / (N · slice length)`; arcs outside the window are × 0.3
- link weight: `w_A→B = (1/N) · #pairs in window` (or minutes in B when thickness = minutes); link time = response start
- colour-mode edge width: `1.2 + 8.8 · w / max(w)`; colour = `ramp(mean / L)`
- timeline-mode segment width: `2 + 10 · bin / max(bin)`; segment colour = `ramp(binMid / L)`; bins follow the slice length and span the window from source to target

## Settings (DEF)

| Key | Default | UI | Effect |
|---|---|---|---|
| window | 2 | Link window | `w`; B counts as following A within w−1 actions |
| thick | count | Arrow thickness | `count` = transitions, `min` = minutes in B |
| scope | avg | Values | per learner vs class total |
| minShare | 0 | Hide weak links | hides edges below share × strongest |
| loops | true | Show loops | self-links |
| merge | false | Merge repeats | collapse consecutive same-behaviour rows |
| align | true (auto) | Start each learner at 0′ | set to `P.clock` on each new log |
| sessionLen | 0 = auto | Session length | |
| slice | 5 | Clock-ring slice | also the timeline-arrow bin size |
| frame | 10 | Frame length | |
| edgeStyle | swell | Arrows toggle above figure | `swell` (timeline) or `colour` |
| theme | auto | Theme | `light` = Paper, `dark` = Screen |

## Design invariants (do not break)

1. Disc **area** is strictly proportional to time share. There is no hidden minimum radius beyond the 3 px floor, and the printed minutes and % are always shown.
2. Arrow thickness has **one meaning at a time**, and the legend states it.
3. The **coverage line** (coded vs uncoded time) is always in the figure footer.
4. **Node positions are stable** across frames and windows; changes in the picture must come from data, not layout.
5. The **violet→amber ramp is reserved for time**; node colours must never use that range.
6. Everything needed to read an exported figure is inside the SVG: title with window, colour bar with window marker, insights, and coverage.
7. **Privacy:** there are no network calls except Google Fonts. Never add analytics, remote logging or uploads. Keep the "Clear saved data" button.
8. The wording is "ONA-inspired", never "ONA implementation".
9. **British spelling** in the UI and docs (behaviour, colour, visualisation). Minutes use the prime ′.

## Dual runtime

The same file runs in two places:

- **Claude artifact:** `window.claude.use('downloads')` exists. The page CSP only allows scripts from cdnjs.cloudflare.com, cdn.jsdelivr.net/npm, cdn.tailwindcss.com and code.jquery.com, and fonts from Google. No remote images; plain `<a download>` is inert there.
- **Standalone website:** no `window.claude`; exports use `browserSave`.

Keep both paths working. If you add a library, load it from cdnjs with a pinned version so the artifact still works, or vendor it inline.

## Known issues / limitations

- mm:ss vs hh:mm ambiguity for two-part times; sessions crossing midnight are not handled; `Date.parse` of ISO strings without a timezone uses local time.
- With more than 10 behaviours the circle gets crowded, and the palette repeats after 10.
- The circular layout does not minimise edge crossings; edges can pass behind unrelated nodes.
- PNG export uses system fallback fonts (web fonts are not embedded when an SVG is drawn to canvas).
- Timeline segments are placed by curve parameter, not arc length, so they are slightly uneven on strongly curved edges.
- Logs larger than 1.5 MB are not saved to local storage; large logs render on the main thread.
- The colour ramp has not been tested for colour-vision deficiency; segment width is the colour-free cue.
- No statistics: group or window differences shown by the figure are exploratory.

## Roadmap for Claude Code (in priority order)

### P0 — publish
- [x] `git init`, first commit, push to a public GitHub repo; enable GitHub Pages (branch `main`, root).
- [x] Add a LICENSE: MIT for the code, CC BY 4.0 for `docs/` (chosen by the author).
- [x] Add `CITATION.cff` (author Karan Bansal, 2026, title "Temporal ONA builder"); optionally link to Zenodo for a DOI.
- [x] GitHub Action running `npm test` on push and pull requests.

### P1 — features that support valid inference (from the research phase)
- [ ] **Group column support:** an optional `group` column; show side-by-side networks per group with shared scales, plus an optional difference view. Differences must be labelled exploratory.
- [ ] **Window-size sensitivity:** show the same figure for w = 2…5 as small multiples, or flag links that change a lot.
- [ ] **Episode counts per frame** in the frame buttons or footer, so thin frames are visible.
- [ ] **Individual-learner small multiples** (a grid of per-learner networks) to expose heterogeneity hidden by means.
- [ ] **"Copy figure caption"** that writes the reporting details: n, window, w, slice, aggregation, alignment, merge, coverage, thickness meaning.
- [ ] Optional **question prompt** before play mode ("What are you looking for?") to discourage fishing across frames.
- [ ] Optional **line-up view:** the real network hidden among networks from permuted episode orders (Wickham et al., 2010).
- [ ] Rename the UI title to make "ONA-inspired" visible (e.g. subtitle).

### P2 — white paper v2 (formal register)
Rewrite `docs/white-paper-v1.html` into v2, centred on **how users read the figure to show temporal and sequential characteristics together and what they may infer**. Planned structure:
1. Problem: the two facets of temporality (passage of time; ordered sequence) and why order-only networks lose duration and timing.
2. Mapping table: characteristic → definition (with source) → plot element → reading rule → what it cannot show.
3. Ten-step reading and inference protocol (question first; audit parameters and coverage; duration; timing; order; joint time-and-order; change across windows; disaggregate; state the claim at the right level; validate).
4. Pattern catalogue: visual signature → interpretation → alternative explanations → verification.
5. Inference taxonomy: descriptive / robust descriptive / comparative (needs ONA or permutation statistics) / causal (outside the tool), with example claim wording.
6. Threats to validity and mitigations.
7. Reporting checklist.
8. Positioning against prior work (below), limitations, ethics.

Regenerate the figures with `npm run figures`. Keep the synthetic data clearly labelled as a known-answer test, not a finding. The detailed research reports are in `docs/research/` (the author will add them); treat any reference marked unverified there as needing a check before citing.

### P3 — quality
- [ ] Accessibility pass: keyboard focus on nodes and controls, screen-reader text, colour-blind check of the ramp.
- [ ] Web Worker for parsing and derivation on large logs.
- [ ] Optional: a layout that reduces crossings while keeping positions stable across frames.

## Prior art and positioning (for docs and the paper)

No published work found combines the full design. Closest works:

- **Nath, Gašević, Fan & Rajendran (2024)**, CTAM4SRL, LAK '24, 645–655, doi:10.1145/3636555.3636926. It has the same goal (both temporal facets of SRL) but uses separate figures: raincloud plots of start times plus a frequency-sized ONA, joined in prose. **This tool's contribution is integrating both facets in one figure.**
- **Tan, Ruis, Marquart, Cai, Knowles & Shaffer (2023)**, Ordered network analysis, ICQE 2022, CCIS 1785, doi:10.1007/978-3-031-31726-2_8. The source of the connection logic. In ONA, node size = occurrences as a response, which differs from this tool's time share. Say so explicitly.
- **Infovis precedents for the encodings** (cite them; do not claim these primitives as new):
  - Shi et al. (2015), 1.5D egocentric dynamic network visualisation, ring-sector node glyph, IEEE TVCG 21(5), doi:10.1109/TVCG.2014.2383380
  - Reitz (2010), time-segmented edges, arXiv:1009.5183
  - Schmauder, Burch & Weiskopf (2015), links as timelines, IVAPP, doi:10.5220/0005303801230130
  - Fuchs et al. (2013), clock glyphs aid reading values at time points, CHI, doi:10.1145/2470654.2466443
  - Beck, Burch, Diehl & Weiskopf (2017), taxonomy of dynamic graph visualisation, CGF 36(1), doi:10.1111/cgf.12791
- **Process-mining maps** (bupaR/processmapR) already combine duration on nodes with transitions on edges, in layered layouts without within-session timing glyphs.

Draft positioning sentence: *"The temporal ordered network adopts ONA's ground→response connection logic over a moving window and adds three encodings not previously combined in learning-analytics networks: node area proportional to time share, a clock-ring glyph showing when each behaviour occurred, and edges that double as within-window timelines. It is ONA-inspired but descriptive."*

Word novelty claims as "to our knowledge".

## Working rules for Claude Code

- Run `npm test` after every change to `index.html`. If you intentionally change outputs (e.g. the sample), update the expected strings in `tests/smoke.test.js` in the same commit and explain why.
- Keep commits small, with messages that describe user-visible changes.
- Do not add frameworks, trackers or remote calls. Do not change the sample seed.
- Ask the author before any licence choice, renaming the tool, or changes to the paper's claims.
