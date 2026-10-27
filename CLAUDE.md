# CLAUDE.md — Temporal ONA builder

Project brief for Claude Code. Read this before changing anything.

## What this is

A browser tool that turns a coded self-regulated learning (SRL) episode log into a **temporal ordered network**: one figure that shows how long learners spent in each behaviour, when in the session each behaviour happened, what followed what, and when each link happened.

- **Author:** Karan Bansal, IIT Bombay.
- **Origin:** a design question in ET 610, Learning Analytics and Educational Data Mining. The question asked how to add time spent and timing to an ENA/ONA co-occurrence network of SRL behaviours (Planning, Monitoring, Debugging, Help seeking, Evaluation) in a 60-minute programming lab.
- **Status:** working v0.1. It has been published once as a Claude artifact and is being prepared as a public website (GitHub Pages).

**Audience.** Learning analytics researchers and instructors.

**Scope of data.** SRL is the origin and the built-in sample, but nothing in the code is SRL-specific: any coded episode log (collaboration moves, clickstream events, think-aloud codes …) over seconds, minutes, hours or days works. Keep UI wording generic and use SRL as the example.

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
npm test             # 40 smoke tests; must pass before any commit
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
| start | yes | start, start_time, begin, timestamp, time, start_s, time_ms … | a plain number, `mm:ss`, `hh:mm:ss`, or anything `Date.parse` accepts (ISO date-times) |
| end | no | end, end_time, stop, finish … | if missing, an episode ends at the learner's next start |
| group | no | group, condition, cohort, class, section, team … | one group per learner (their first row wins); enables **Learners → one group / Groups side by side** |

Column matching tries exact `ALIASES` first, then likely names (`FUZZY`: e.g. `discourse_code`, `event_type`, `pid`), never reusing a column.

**Plain numbers** are minutes unless the Check step says otherwise: `guessUnit` reads the start column's name (`_s`, `_ms`, `_h`, `_min` …) and treats values above 1e8 as Unix seconds and above 1e11 as Unix milliseconds; the user can switch between minutes, seconds, milliseconds and hours (`#map-unit`, kept in `tona-map.unit`). Scaled numbers beyond a year of minutes count as clock times, so learners are aligned.

**Known ambiguity:** a two-part time such as `09:12` is read as **mm:ss**, not hh:mm. The UI tells users to add `:00`.

## Code map (inside the `<script>` of index.html)

The code is ES5-style inside an IIFE, with no dependencies. Sections, in order:

1. **Helpers:** `esc`, `clamp`, `fmt` (1 dp below 100), `fmtMin`, `unit`, `f1`. `PR` = `'\u2032'` (prime for minutes). **Time labels:** all times are stored in minutes; `TU = timeUnit(L)` picks the display unit from the session length (seconds up to 3 min, minutes up to 4 h, hours up to 3 days, then days). Use `tp` (a point: `15′`, `90s`, `1.5h`, `3d`), `tr` (a span), `ta` (an amount: s, min, or h for long sessions), `td` (a slice length: `5-min`), `fw` (a link weight in the legend's unit), `when` ("around minute 32" / "around day 4.7") and `tword`. Never print raw minutes in the UI. `LADDER` and `nice(x)` give the sizes slices, frames and the slider step snap to.
2. **Constants:** `ALIASES`, `DEF` (default settings), node palettes `NODE_LIGHT`/`NODE_DARK` (blues, greens, teal and olive only, clear of the time hues; the first five pass the colour-vision checks for every pair in both themes, slots 6–10 rely on the always-visible labels), time ramps `RAMP_LIGHT`/`RAMP_DARK` (violet → magenta → amber; the light amber is darkened to `#CC7612` for 3.4:1 contrast), longest clock-ring bar `BAR = 16`.
3. **State:** `S` (settings), `P` (parsed log), `D` (derived: `seqs`, `links`, `L` = session length), `view` (`{t0, t1, frame}` where frame `-1` = whole, `-2` = custom), `selected` node, `downloads` (Claude capability or null).
4. **Colour/theme:** `tokens()` reads CSS variables so SVG gets literal colours, which exported files need.
5. **Parsing:** `splitRow`, `normH`, `parseTime`; `parseRows` also returns `groups`/`lgroup` (group per learner) when a group column is chosen. **Code manager** (Check step, `#codes`): `pending.codes` = `[{o, label, keep}]` in circle order; `codeGroups` merges codes with the same label (any case), `applyCodes` builds `P` with renamed/merged/left-out codes (left-out episodes are removed, so their time counts as uncoded; without an end column, ends are filled from the full log first, `P.prefilled`). Choices persist in `tona-codes` when the code list matches. `readTable(text)` returns `{delim, names, hdr, rows, nums}`; `autoMap(hdr)` guesses the column for each of `ROLES` via `ALIASES`; `parseRows(tb, idx)` returns `{ev, behaviours, counts, learners, clock, skipped, bad, hasEnd, rows, two, neg}` or `{error}` (`two` = rows with `mm:ss`-style times, `neg` = episodes ending before they start). `parseLog(text, idx?)` chains them.
6. **Derive:** `derive()` picks the slice (`D.sl`: the user's choice if it gives 1–144 slices, else `nice(raw/12)`) and frame (`D.fr`: the user's choice if it gives 1–24 frames, else `nice(L/6)`), sets `L` to the last episode end rounded up to `min(slice, nice(raw/60))` (so no invented uncoded time; the last slice may be partial) and sets `TU`. It sorts each learner's episodes, fills missing ends, aligns (per learner to 0′ if `S.align`, else global min for clock data), optionally merges back-to-back repeats, optionally normalises each learner to 0–100% (`S.norm`), sets `L` (auto = ceil to slice, or `S.sessionLen`), and builds `links`: for each episode *i*, a link from each of the previous `w−1` episodes; `time` = response start, `dur` = response duration.
7. **Compute:** `compute(t0, t1, wts, o)` (`wts` weights each learner: null = all, 0/1 = a group, counts = a bootstrap resample; `o.thr` fixes the link threshold for group comparison) returns minutes per behaviour in the window, per-slice minutes (`slc`) and shares (`shr`), learners with time in each behaviour (`nlb`), and aggregated edges `{f, t, w, nl, mean, bins[]}` (`nl` = learners who made the link) filtered by `S.loops`, `S.minLearners` and `S.minShare`. With `S.thick === 'lift'`, `e.w` = observed ÷ expected (`e.cnt` observed pairs, `e.exp` expected from how often each code is a ground and a response); pairs with `cnt < LIFT_MIN` (5) or lift ≤ 1 are dropped. `stability(c, wts)` resamples learners 200 times (seeded `mulberry32(20261007)`; 100/50 for large logs) and stores `c.stab.map["f>t"] = {p, lo, hi}`; links shown in fewer than `STAB_HOLD` (80%) of resamples are drawn dashed with a hollow arrowhead, and `stabNote` adds a footer line.
8. **Geometry:** `rMaxOf(B)`, `layoutNodes` (fixed circle; first behaviour at top, clockwise in order of first appearance; each node has `r` disc, `r0` = r+5 bar baseline, `ro` = r0+BAR+1 outer edge, `side` for left/right nodes), `edgeGeom` (quadratic curve offset to the left of direction, so reciprocal edges separate), `loopGeom` (side nodes loop up and outward, clear of their labels), `qpt`/`cpt` (quadratic/cubic points), `arcPath`, `sectorPath` (annular sector for a clock bar), `swellSegs`, `wrapText`, `haloText`, `peakSlice`.
9. **Draw:** `figureMarkup(c, opt)` builds the SVG content as a string (`opt.static` for group panels: no selection or hover keys; `opt.maxW/maxBin/maxShr` share scales across panels); `drawFigure(c)` puts it into `#net`. **Groups:** `grp` = -1 (all), a group index, or `'cmp'`; `drawCompare` draws up to 6 group panels with per-learner values, the all-learner link threshold and shared scales, plus `drawDiff` (largest differences between two chosen groups, labelled exploratory, no tests). In compare mode `exportSVG` writes one SVG with all panels and Numbers as CSV has one block per group. The figure contains the background rect, title and subtitle (plus a "Highlighted: links of X" line when a disc is selected), colour bar with 0′ / mid / end minutes (top right), edges (weakest first; links not touching the selected disc drop to 0.08 opacity), nodes (bar baseline, one clock bar per slice, dark 0′ tick, disc, selection ring), loops, labels (minute numbers at the quarter points of the selected disc's ring only, then name / minutes (%) / peak slice, beside side nodes and above or below the others; a long name beside a side node wraps onto two lines (`splitName`) rather than dropping below the disc; halo drawn as a duplicate stroked text **behind** the text, *not* `paint-order`, so exports render in cairosvg), wrapped footer insights, a size key (10% and 25% circles) and a clock key. `insights(c)` produces the three footer sentences. Clicking a disc toggles `selected` (focus + detail panel); clicking the background or pressing Escape clears it.
**Simple by default (progressive disclosure):** keep the first view calm and put extras one click away rather than removing them. The explore header is one row (Learners, frames, **View** menu with arrow style, Key points and **Custom window**); the window slider and activity strip (`#win`) show only for a custom window (`winOpen`, key W, or when the window is dragged). Settings show three essentials (link window, arrow thickness, hide weak links); other groups start closed and their summaries show "N changed" (`settingBadges`, `data-keys`). The Guide shows one short line per element; `.long` parts appear with **Show full explanations**. The Check step shows behaviour chips; the code manager (`#codes-box`) opens on request or when codes were changed. The AI model setup (`#ai-cfg`) folds away once it has what it needs.

10. **Side panel:** one tabbed panel beside the figure (`.side`, sticky on wide screens) with four tabs: *Guide* (`drawLegend`), *Settings* (the `#s-*` controls), *Behaviour* (`drawDetail`: selected node's minutes, busiest slice, histogram, top next/before links) and *AI reading*. `showTab(k)` switches tabs (arrow keys move between them; last tab kept in `tona-tab`); clicking a disc opens *Behaviour*.
11. **Window UI:** `buildFrames` (each frame button shows the number of episodes that start in it; `ACT` = episodes starting per slice, drawn as the activity strip above the window slider), `syncWindowUI`, `setFrame`, `togglePlay` (1.6 s per frame), dual range slider (`#r0`, `#r1`).
12. **Data flow and steps:** the page has three stages, `#stage-start` (upload: drop zone, file input, paste box, sample, template), `#stage-check` (column selects `#map-*`, preview table, summary tiles, behaviour chips, warnings) and `#stage-explore` (settings, figure, legend, detail). `showStage(s, focus)` switches them and the step buttons in the app bar. `analyse(text, name, idx)` fills `pending` and draws the check step (`drawCheck`); `build(fromUser)` turns `pending` into `P` and opens the explore step; `rederive()`, `readSettingsUI`/`writeSettingsUI`, `applyTheme`. First visits open on the upload step; a saved log opens straight on its figure. Storage keys: `tona-data`, `tona-name`, `tona-map` (column names per role), `tona-codes`, `tona-settings-v4` (older saves are read once without their old defaults for minShare, slice and frame), `tona-tab`, `tona-ai` (provider, model, endpoint), `tona-ai-key` (only when the user ticks *Remember the key*), all wrapped in try/catch and all removed by **Clear saved data**.
13. **Sample:** `mulberry32(610)` plus `sampleCSV()`, which generates phase-weighted synthetic data. **Do not change the seed or generator** without updating the tests and the white paper numbers.
14. **Export:** `svgString`, `savePNG` (SVG → canvas at 2×), `saveFile`, which uses the Claude `downloads` capability when running as a Claude artifact and `browserSave` (Blob + `<a download>`) when standalone. `TEMPLATE` is the small CSV behind **Download template**; elements marked `data-save` appear only when saving works. **Download tool** saves `SELF`, a copy of the page's HTML taken at the top of the script before `init` touches the DOM, as `temporal-ona-builder.html`; it runs offline from `file://` (a test loads the copy in jsdom and builds the sample).
15. **Caption and AI reading:** `caption(c)` writes the reporting details for **Copy caption**; `copyText` uses the Clipboard API with an `execCommand` fallback. The AI reading is optional and off until the user presses **Read this figure**. `figureBrief(c)` is the only data that leaves the page: aggregated numbers behind the current figure (settings, coverage, minutes and slice profile per behaviour, link weights, mean minute and per-slice weights; at most 30 links) plus the fixed instructions `AI_SYS`, which encode the reading rules and forbid causal, significance or prediction claims. Providers (`AI_PROV`): `anthropic` (Messages API called directly from the browser with the user's key and the `anthropic-dangerous-direct-browser-access` header; default model `claude-opus-5-5`, effort `medium`, server-side refusal fallback), `openai` (any `/v1/chat/completions` endpoint) and `local` (Ollama or LM Studio on localhost; no key). `aiRequest` builds the request, `aiStream` reads either SSE shape (or a plain JSON reply), `aiHttpError` maps status codes to plain messages, `mdHtml` renders the reply as Markdown **after escaping it**, so model output can never become live HTML. `aiAfterRender` marks a reading as stale when the window or settings change. There is no SDK: the page has no build step and must keep working offline.
16. **Explore extras:** on screen, `drawFigure` moves each `<title>` into a `data-tip` attribute and the hover card (`onHover`, `edgeCard`, `nodeCard`, `#tip`) replaces native tooltips: pointing at an arrow lights it and its two discs, pointing at a disc lights its links; cards show weight, timing, learners who made the link and a mini timeline. `svgString` puts the titles back and strips screen-only classes. `edgeCard`/`EDGE` index edges by `"f>t"`; each edge has an invisible 12 px hit path. **Key points** (`S.notes`, button `#kp`, key K): `keyPoints` puts numbered badges on the most-time disc, the strongest shown link and the busiest slice in the window, matching numbered footer lines (adds a "Busiest moment" line). **Dataset name:** `dsName`, renamed inline (`startRename`), shown in the figure subtitle and file names via `dsLabel()` (generic names such as "Pasted data" are left out). **Export menu** (`#export-menu`): PNG, SVG, **Numbers as CSV** (`numbersCSV`: one row per behaviour and link in the window, plain minutes, learners) and Copy caption. **Keys:** ← → frames, Home whole session, Space play, K key points, Esc clears.
17. **About dialog:** `openAbout`/`closeAbout` (`<dialog>`, with a fallback to the `open` attribute); it holds the privacy note, **Clear saved data** and the citation.
18. **Init:** event wiring.

## Formulas (keep code, legend and paper consistent)

For behaviour *b*, window length *T*, *N* learners, per-learner scope (class-total scope drops the 1/*N*):

- minutes: `m_b = (1/N) Σ overlap(episode, window)`
- disc: `share = m_b / T`, `r = max(3, rMax·√share)`, `rMax = min(92, 0.88·R·sin(π/max(B,3)))`, with `R = 212` (165 if B ≤ 2)
- clock bar length: `max(1.5, 16 · p_bk / max(p))` px outward from the baseline at `r + 5`, where `p_bk = Σ overlap(episode, slice k) / (N · slice length)`; bars outside the window are drawn at 0.28 opacity, bars inside at 0.9
- size key: circles at 10% and 25% share, `r = rMax·√share`, the same scale as the discs
- link weight: `w_A→B = (1/N) · #pairs in window` (or minutes in B when thickness = minutes); link time = response start
- colour-mode edge width: `1.2 + 8.8 · w / max(w)`; colour = `ramp(mean / L)`
- timeline-mode segment width: `2 + 10 · bin / max(bin)`, drawn only when `bin ≥ 0.12 · max(bin)` so tiny slices do not turn arrows into confetti; segment colour = `ramp(binMid / L)`; bins follow the slice length and span the window from source to target
- timeline-mode link emphasis (colour-free, so width keeps one meaning): base line opacity `0.18 + 0.62 · w / max(w)`, segment opacity `0.35 + 0.65 · w / max(w)`, arrowhead opacity `0.4 + 0.6 · w / max(w)`

## Settings (DEF)

| Key | Default | UI | Effect |
|---|---|---|---|
| window | 2 | Link window | `w`; B counts as following A within w−1 actions |
| thick | count | Arrow thickness | `count` = transitions, `min` = minutes in B |
| scope | avg | Values | per learner vs class total |
| minShare | -1 = auto | Hide weak links | auto keeps the `max(6, 2·B)` strongest links (ties kept); a positive value hides edges below share × strongest; 0 shows all. `linkNote(c)` puts the hidden count in the figure footer, caption and AI summary |
| loops | true | Show loops | self-links |
| merge | false | Merge repeats | collapse consecutive same-behaviour rows |
| align | true (auto) | Start each learner at 0′ | set to `P.clock` on each new log |
| norm | false | Time as % of each session | stretches each learner's session (first start to last end) to 0–100%; `TU.k = 'pct'`, so labels read in % and `sessionLen` is ignored |
| sessionLen | 0 = auto | Session length | |
| slice | 0 = auto (about 12 bars; 5 min for a 60-min session) | Clock-ring slice | also the timeline-arrow bin size; the menu lists only sizes that fit the session |
| frame | 0 = auto (about 6 frames; 10 min for a 60-min session) | Frame length | the menu lists only sizes that fit the session |
| edgeStyle | swell | Arrows toggle above figure | `swell` (timeline) or `colour` |
| notes | false | Key points button / K | numbered badges for the main findings |
| minLearners | 0 | Fewest learners per link | hide links made by fewer learners (`-10`/`-25` = 10%/25% of learners) |
| stab | false | Check stability | bootstrap over learners; unstable links dashed |
| theme | auto | Theme | `light` = Paper, `dark` = Screen |

## Design invariants (do not break)

1. Disc **area** is strictly proportional to time share. There is no hidden minimum radius beyond the 3 px floor, and the printed minutes and % are always shown.
2. Arrow thickness has **one meaning at a time**, and the legend states it.
3. The **coverage line** (coded vs uncoded time) is always in the figure footer.
4. **Node positions are stable** across frames and windows; changes in the picture must come from data, not layout.
5. The **violet→amber ramp is reserved for time**; node colours must never use that range.
6. Everything needed to read an exported figure is inside the SVG: title with window, colour bar with window marker, insights, and coverage.
7. **Privacy:** there are no network calls except Google Fonts and, only when the user presses **Read this figure**, one request to the AI endpoint they chose. That request carries `figureBrief` and `AI_SYS` only; never send rows, learner IDs or the raw log, and keep **See exactly what will be sent** accurate. Never add analytics, remote logging or uploads. Keep the "Clear saved data" button, and make it remove every storage key.
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
- The time ramp passes the colour-vision separation check for its three stops, but reading an exact minute from colour is still hard; segment position along the arrow and the minute numbers are the colour-free cues.
- With more than five behaviours some node colour pairs fall below the colour-vision target; the labels carry identity.
- No statistics: group or window differences shown by the figure are exploratory.
- AI reading: the model reads numbers, not the image, and can still misread them or overreach despite `AI_SYS`; the UI labels it a draft. Browser calls only work with providers that allow cross-origin requests; local servers may need their CORS origin set (`OLLAMA_ORIGINS`, LM Studio's CORS switch). Keys typed into the page are visible to anything else running in that page, so the key is kept in memory unless the user asks to remember it.

## Roadmap for Claude Code (in priority order)

### P0 — publish
- [x] `git init`, first commit, push to a public GitHub repo; enable GitHub Pages (branch `main`, root).
- [x] Add a LICENSE: MIT for the code, CC BY 4.0 for `docs/` (chosen by the author).
- [x] Add `CITATION.cff` (author Karan Bansal, 2026, title "Temporal ONA builder"); optionally link to Zenodo for a DOI.
- [x] GitHub Action running `npm test` on push and pull requests.

### P1 — features that support valid inference (from the research phase)
- [x] **Group column support:** an optional `group` column; one group at a time or side-by-side networks with shared scales, plus a table of the largest differences labelled exploratory.
- [ ] **Window-size sensitivity:** show the same figure for w = 2…5 as small multiples, or flag links that change a lot.
- [x] **Episode counts per frame** in the frame buttons, so thin frames are visible.
- [ ] **Individual-learner small multiples** (a grid of per-learner networks) to expose heterogeneity hidden by means.
- [x] **"Copy figure caption"** that writes the reporting details: n, window, w, slice, aggregation, alignment, merge, coverage, thickness meaning.
- [ ] Optional **question prompt** before play mode ("What are you looking for?") to discourage fishing across frames. (The AI reading already asks this question.)
- [ ] Optional **line-up view:** the real network hidden among networks from permuted episode orders (Wickham et al., 2010).
- [ ] Rename the UI title to make "ONA-inspired" visible (e.g. subtitle).

### Done outside the original roadmap
- [x] **Code manager** on the Check step (rename, merge, leave out, reorder) and smarter column matching.
- [x] **Times more than chance** arrow weight (observed ÷ expected), **fewest learners per link**, and a seeded **stability check** (bootstrap over learners). These are descriptive robustness aids, not statistical tests; keep the "no statistical comparison" positioning and ask the author before adding p-values or permutation tests.
- [x] **Offline copy:** Download tool saves the page as one HTML file that runs from disk.
- [x] **AI reading (beta):** optional draft reading of the current figure from Claude, an OpenAI-compatible API or a local model; sends only `figureBrief`.
- [x] **Layout:** figure in the main column; settings, guide, behaviour details and AI reading in one tabbed, sticky side panel; frames and window slider above the figure; About in a dialog.

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

- **Nath, Gašević, Fan & Rajendran (2024)**, CTAM4SRL, LAK '24, 645–655, doi:10.1145/3636555.3636926. It has the same goal (both temporal facets of SRL) but uses separate figures: raincloud plots of start times plus a frequency-sized ONA, joined in prose. **This tool's contribution is integrating both facets in one figure.** Its limitations section says the method gave no information on the absolute duration learners spent in each process, and suggests integrating duration in future. That is direct motivation for disc area = time share. It defines passage of time as duration, rate of occurrence and points in time, after Knight, Wise & Chen (2017) and Molenaar & Järvelä (2014).
- **Saqr, López-Pernas, Törmänen, Kaliisa, Misiejuk & Tikka (2025)**, Transition network analysis, LAK '25, 351–361, doi:10.1145/3706468.3706513.
  - **Encoding:** nodes show the initial probability (a pie); edge thickness shows first-order transition probability.
  - **Validation:** edges are validated with bootstrapping and null models. Permutation-based group comparison is in the `tna` R package (Tikka, López-Pernas & Saqr 2025, *Applied Psychological Measurement*), not in the LAK paper.
  - **Assumption:** transition probabilities do not change over time. TNA therefore cannot show when a transition happens, which this tool's link timelines do.
- **Nath, Desai, Rajendran & Gašević (2026)**, Making advanced temporal visualizations accessible to educators using generative AI, AIED 2026, LNAI 16583, 389–397, doi:10.1007/978-3-032-29760-0_43. It comes from the same group.
  - **TemporLA:** a Streamlit dashboard with separate plots for passage of time (raincloud), order (TNA) and cotemporality (ENA), a time slider and two-group comparison.
  - **AI layer:** ChatGPT-4o (zero-shot, temperature 0.2) joins the plots into one text narrative.
  - **Results:** 87–91% of claims were correct for one group and 65–76% for group differences, with overreach. Image inputs were less reliable than text.
  - **Implications:**
    - They integrate the facets in language; this tool integrates them in one figure.
    - The AI reading is **not** a contribution here; cite them for it. It follows the same lessons: text not images, claims anchored to figure elements, guards against overreach.
    - Cotemporality is only partly covered by the moving-window links.
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
