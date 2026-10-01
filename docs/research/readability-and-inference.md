# Making the figure easier to read and safer to infer from

Research note, 1 October 2026. It asks two questions about the temporal ordered network: which design changes would help people read it more accurately, and which would stop them drawing conclusions the data cannot support. Each recommendation names the evidence behind it, the part of the tool it changes, and a rough cost.

References are marked **✓** when the abstract or landing page was read in this pass, and **V\*** when only search-result text was seen. Check V\* references before citing them in the paper.

## Summary

The figure packs four facets into one picture: how long, when, what followed what, and when each link happened. The evidence suggests three changes would matter most:

1. **Show how sure we are about each link.** At present every arrow looks equally trustworthy. Resampling learners (bootstrap) and shuffling each learner's order (permutation) would show which links are stable and which are more than chance. TNA, the closest current method in learning analytics, already does both. Without this, the tool sits in the exploratory setting where most "insights" turn out to be false.
2. **Separate order from frequency.** A behaviour that fills 41% of the time will have thick arrows simply because it is common. An option to weight arrows by observed ÷ expected transitions would show order effects that frequency alone does not explain.
3. **Pair the integrated figure with linear, per-learner and small-multiple views.** Radial glyphs and animation are good at some tasks and poor at others. Linear timelines, a sequence plot per learner, and frames side by side cover the tasks the ring and Play button do badly, and let readers check a claim against the data underneath.

The integrated figure stays the centrepiece. The other views exist to check what it suggests.

## 1. Reading the parts of the figure

### Disc area (time spent)

- **Evidence.** People judge area less accurately than position or length, and they underestimate the area of large circles. Cartographers correct for this with Flannery scaling (Flannery 1956, V\*). The classic ranking of position, then length, then area is Cleveland & McGill (1984, V\*, not searched in this pass).
- **For the tool.** Keep area strictly proportional, as design invariant 1 requires; do not apply Flannery's correction. Accurate comparison should come from the printed minutes and %, which the figure already shows, plus a linear **time-budget strip**: one sorted horizontal bar per behaviour, next to the figure or in the *Behaviour* tab.
- **Sparse logs.** In clickstream-like logs every disc is tiny, because the window is mostly uncoded. A "share of coded time" option for disc area would fix this, but it changes the meaning of disc size and needs the author's decision.
- **Cost:** low for the strip, low for the option.

### Clock ring (when each behaviour happened)

- **Evidence: radial glyphs.** In small-multiple settings, radial glyphs are best for reading the value at a specific time, while line glyphs are best for peaks and trends (Fuchs et al. 2013, ✓).
- **Evidence: radial versus linear charts.** For daily patterns, a plain 24-hour linear bar chart was the most accurate and fastest, and also the one participants preferred, over radial variants (Waldner et al. 2019, ✓; 92 participants).
- **For the tool.** The ring is good for "how much at minute X?" and integrates well into the node. The most common question, though, is "when does it peak, and does it rise or fall?", which linear charts answer better.
- **Recommendation.** Add a linked **linear timeline view**, a state-distribution plot as in TraMineR (Gabadinho et al. 2011, ✓): x is session time, with one row or stacked band per behaviour, sharing the window and frame controls. Keep the ring as the compact summary and the peak label as its plain-text cue.
- **Cost:** medium.

### Edge direction

- **Evidence.** In a controlled study, tapered edges (wide at the source, narrow at the target) were read faster and more accurately than standard arrowheads and colour gradients. A later study extended this to curved and animated edges (Holten & van Wijk 2009; Holten et al. 2011; V\*, landing pages were blocked).
- **For the tool.**
  - *Colour-only mode:* use tapered edges, keeping a small arrowhead for print. Width can still carry weight if it is measured at the midpoint.
  - *Timeline mode:* width already encodes per-slice weight, so tapering would clash. Keep the arrowheads there.
- **Cost:** low.

### Crossings and layout

- **Evidence: crossings.** Edge crossings are one of the strongest readability penalties in node-link diagrams (Purchase's aesthetics work, V\*). In a circular layout, the number of crossings depends only on the order of nodes around the circle, and there are good heuristics for weighted graphs (Baur & Brandes 2004, ✓).
- **Evidence: matrices.** Above about 20 nodes, adjacency matrices beat node-link diagrams on most tasks except path finding (Ghoniem et al. 2005, ✓).
- **For the tool.**
  - Compute a crossing-reduced node order **once, on the whole-session network**. This keeps positions stable across frames (invariant 4) while reducing clutter.
  - Add an optional **transition matrix view** for logs with many codes: rows are "from", columns are "to", each cell shows the weight plus a small sparkline over time. It is also the most precise way to read exact link weights.
- **Cost:** low for the order, medium for the matrix.

### Colour for time

- **Evidence.** Colour hue ranks low for reading quantities. The tool already provides colour-free cues: segment position along the arrow, minute labels, and the tooltip average minute.
- **For the tool.** Keep the violet-to-amber ramp as reinforcement, never the only cue. The time-budget strip and timeline view also reduce reliance on colour.

## 2. Showing change over time

- **Evidence.** For dynamic graphs, small multiples were significantly faster than animation on every task tested. Animation had fewer errors only for "which nodes or edges appeared in the same time slice". Preserving the mental map made little difference in either condition (Archambault, Purchase & Pinaud 2011, ✓).
- **For the tool.** Add a **frames side by side** view: one small network per frame, all on the same scales, with the active window highlighted. Keep Play as a secondary option. The new episode counts per frame should show under each small network so thin frames are visible.
- **Comparing frames.** A "difference between two frames" view would follow, labelled exploratory.
- **Cost:** medium (the drawing code already takes a window).

## 3. Inference: what a reader may conclude

### Why this matters

- **Evidence: false insights.** In an exploratory visual analysis study on synthetic data with known answers, over 60% of users' reported insights were false (Zgraggen et al. 2018, ✓). The more views an analyst inspects, the more spurious patterns they find.
- **Evidence: forking paths.** Pu & Kay (2018, ✓) frame this as the garden of forking paths and list remedies: correcting for multiple comparisons, regularisation, and correcting perceptual bias.
- **Applied to this tool.** Every combination of frame, window, link window, slice and merge setting is a fork. The tool currently gives no guard against seeing patterns in noise.

### What other methods do

- **ENA** plots each unit's position and draws 95% confidence intervals around group means, then compares groups with t-tests or Mann-Whitney U tests (rENA documentation, V\*).
- **ONA** inherits ENA's statistics (Tan et al. 2023). It encodes self-transitions in the inner node size and responses in the outer size, with chevrons for direction (search-result descriptions, V\*).
- **TNA** (Saqr, López-Pernas, Törmänen, Kaliisa, Misiejuk & Tikka, LAK '25, ✓; R package `tna` on CRAN, ✓) models transition probabilities. It validates edges by bootstrapping, offers permutation tests between groups, and adds centralities, communities and clustering.
  - The abstract does not mention duration or within-session timing. If the full paper confirms that, this tool's contribution (time share plus timing in the same figure as order) still holds.
  - **TNA is missing from the prior-art list in CLAUDE.md and should be added before the ECIS submission.**
- **Psychological networks:** `bootnet` popularised bootstrapped confidence intervals for edges and case-dropping stability for centrality (Epskamp, Borsboom & Fried 2018, ✓).

### Recommendations

1. **Learners behind each link (low cost, high value).**
   - Show "*k* of *N* learners" for every link and node: in tooltips, in the *Behaviour* tab, and in the AI summary.
   - Add a filter such as "hide links made by fewer than 3 learners".
   - Reason: a per-learner mean of 1.2 transitions can come from everyone or from two very busy learners.
2. **Base-rate-adjusted links (low to medium cost).**
   - Add a link-weight option of observed ÷ expected transitions, where "expected" assumes order does not matter given how often each code occurs.
   - Alternatively, show adjusted residuals in the lag-sequential tradition (Bakeman & Quera 2011, V\*, not searched in this pass).
   - Reason: this separates "Debugging follows Monitoring because Debugging is everywhere" from "Debugging follows Monitoring more than its frequency predicts".
3. **Bootstrap stability (medium cost; a Web Worker for large logs).**
   - Resample learners with replacement, for example 500 times, and recompute the figure numbers each time.
   - For each link, report the share of resamples in which it appears above the weak-link threshold, plus a 95% interval for its weight.
   - Draw unstable links dashed or faded, and add a key entry for this.
   - The same resamples give intervals for disc minutes and for the peak slice.
4. **Permutation baseline and line-up (medium cost).**
   - Shuffle each learner's episode order while keeping durations, then rebuild the links. Links stronger than in, say, 95% of shuffles are "more than chance (exploratory)".
   - Use the same shuffles for the roadmap's **line-up view**: the real network hidden among 8 shuffled ones. If readers cannot pick it out, the order pattern is weak (Wickham et al. 2010, ✓).
5. **Comparisons between frames.**
   - Show the difference only when both frames have enough episodes, and label it exploratory.
   - Recent theory shows that the data needed to tell two directly-follows structures apart grows with the number of codes and shrinks as the processes differ more (Lee, Tiňo & Styles 2026, ✓, arXiv preprint). Six frames from 30 learners with five codes is a small sample for that purpose.
   - The tool should say so instead of showing confident differences.
6. **Optional: animate uncertainty.** Hypothetical outcome plots, and NetHOPs for networks, help non-statisticians judge uncertainty by watching sampled outcomes (Hullman et al. 2015, ✓; Zhang et al. 2021, V\*). The Play button could cycle through bootstrap samples. This is a later step.

### Heterogeneity

- **Evidence.** Averages describe a "typical learner" who may not exist. Person-specific (idiographic) analyses often find structure different from the group average (Saqr and colleagues, ✓ via search abstracts).
- **For the tool.** Add a **Learners view**, a sequence index plot: one row per learner, time on the x-axis, coloured by behaviour (Gabadinho et al. 2011, ✓). Sort it by time in the most common behaviour or by first appearance of a chosen code.
  - It is the raw ground truth behind every network claim.
  - It makes heterogeneity visible at a glance.
  - It is cheap to draw because the data are already in `D.seqs`.
- Per-learner network small multiples (already on the roadmap) can follow.

## 4. Guiding the reading, including the AI reading

- **Question first.** Asking "what are you looking for?" before exploring reduces fishing (Pu & Kay 2018). The AI tab already asks this; the Play button and frame views could ask too.
- **Claim levels in the UI.** Next to the insights, show which kind of claim the current view supports: descriptive, robust descriptive (stable under bootstrap), comparative (needs ONA, TNA or permutation tests), or causal (outside the tool). This mirrors the inference taxonomy planned for white paper v2.
- **AI reading.**
  - *Evidence:* multimodal LLMs read simple charts reasonably well but are inconsistent at judging visualisations, struggle with dense multi-encoding charts (bubble charts were among the worst), and miss misleading elements (Seto et al. 2026, ✓; VLAT/CALVI benchmarks, V\*).
  - *Already done:* the tool sends numbers rather than an image, which avoids the weakest case.
  - *Next:* include the bootstrap and permutation results in the summary so the model can qualify its claims, and check that every number the model quotes appears in the summary, flagging any that do not.
  - *For the paper:* evaluate AI readings against expert readings on the synthetic known-answer data.

## 5. Proposed order of work

| # | Change | Helps | Cost |
|---|---|---|---|
| 1 | Learners behind each link/node, plus a minimum-learners filter | inference | low |
| 2 | Observed ÷ expected link weight option | inference (frequency confound) | low–medium |
| 3 | Learners view (sequence index plot) | heterogeneity, checking claims | medium |
| 4 | Bootstrap stability of links and discs; unstable links dashed | inference | medium |
| 5 | Linear timeline / time-budget strip | reading "when" and "how much" | medium |
| 6 | Frames side by side with shared scales | reading change | medium |
| 7 | Crossing-reduced stable node order | reading links | low |
| 8 | Tapered edges in colour-only mode | reading direction | low |
| 9 | Permutation baseline and line-up view | inference | medium |
| 10 | Transition matrix view with sparklines | many codes, exact weights | medium |
| 11 | AI reading: number check and uncertainty in the summary | AI validity | low–medium |

Items 1–4 change what a reader may conclude, so they matter most for the paper's claims. Items 5–8 change how accurately the figure is read.

## 6. Evaluating it for ECIS (design science)

A small task-based study would give the paper its evaluation:

- **Tasks** (adapted from Ghoniem et al. and Archambault et al.):
  - Which behaviour took most time?
  - When did X peak?
  - Which link is strongest in the last third?
  - Did A→B become more frequent over the session?
  - Is this link more than chance?
- **Conditions:** the integrated figure, against an ONA-style network plus separate time charts (the CTAM4SRL approach).
- **Data:** synthetic logs with planted patterns (the existing seeded generator) plus one real log.
- **Measures:** accuracy, time, confidence, and the false-insight rate in free exploration (the Zgraggen et al. protocol).

## Sources

- Archambault, Purchase & Pinaud (2011). Animation, small multiples, and the effect of mental map preservation in dynamic graphs. *IEEE TVCG* 17(4), 539–552. ✓ https://pubmed.ncbi.nlm.nih.gov/20498503/
- Baur & Brandes (2004). Crossing reduction in circular layouts. *WG 2004*. ✓ https://i11www.iti.kit.edu/extra/publications/bb-crcl-04.pdf
- Chen, Knight & Wise (2018). Critical issues in designing and implementing temporal analytics. *Journal of Learning Analytics* 5(1), 1–9. ✓ https://learning-analytics.info/index.php/JLA/article/view/5940
- Epskamp, Borsboom & Fried (2018). Estimating psychological networks and their accuracy. *Behavior Research Methods* 50, 195–212. ✓ https://arxiv.org/abs/1604.08462v2
- Fuchs, Fischer, Mansmann, Bertini & Isenberg (2013). Evaluation of alternative glyph designs for time series data in a small multiple setting. *CHI '13*, 3237–3246. ✓ https://kops.uni-konstanz.de/entities/publication/9dc371f0-426e-4dba-8d76-a8ad22f0acae
- Gabadinho, Ritschard, Müller & Studer (2011). Analyzing and visualizing state sequences in R with TraMineR. *Journal of Statistical Software* 40(4). ✓ https://www.jstatsoft.org/v040/i04
- Ghoniem, Fekete & Castagliola (2005). On the readability of graphs using node-link and matrix-based representations. *Information Visualization* 4(2), 114–135. ✓ https://hal.archives-ouvertes.fr/hal-00343819
- Holten & van Wijk (2009). A user study on visualizing directed edges in graphs. *CHI '09*. V\* ; Holten, Isenberg, van Wijk & Fekete (2011). Performance evaluation of tapered, curved, and animated directed-edge representations. V\* https://hal.archives-ouvertes.fr/hal-00696823
- Hullman, Resnick & Adar (2015). Hypothetical outcome plots outperform error bars and violin plots for inferences about reliability of variable ordering. *PLOS ONE*. ✓ https://pmc.ncbi.nlm.nih.gov/articles/PMC4646698
- Lee, Tiňo & Styles (2026). Resolution limits for process comparison from event data. arXiv:2609.20489. ✓ (preprint) https://arxiv.org/pdf/2609.20489
- Pu & Kay (2018). The garden of forking paths in visualization. *BELIV*. ✓ https://mucollective.northwestern.edu/files/2018-ForkingPaths-BELIV.pdf
- Saint, Gašević, Matcha, Ahmad Uzir & Pardo (2020). Combining analytic methods to unlock sequential and temporal patterns of self-regulated learning. *LAK '20*. V\*
- Saqr, López-Pernas, Törmänen, Kaliisa, Misiejuk & Tikka (2025). Transition Network Analysis. *LAK '25*, 351–361. ✓ https://arxiv.org/abs/2411.15486 ; R package `tna` ✓ https://cran.csail.mit.edu/web/packages/tna/index.html
- Seto, Nguyen, Hong & Maciejewski (2026). LLMs have visualization literacy: now what? arXiv:2606.15136. ✓ https://arxiv.org/pdf/2606.15136
- Tan, Ruis, Marquart, Cai, Knowles & Shaffer (2023). Ordered network analysis. *ICQE 2022*, CCIS 1785. (In CLAUDE.md; plot conventions V\*.)
- van der Aalst (2019). A practitioner's guide to process mining: limitations of the directly-follows graph. V\* https://www.vdaalst.com/publications/p1101.pdf
- Waldner, Diehl, Gračanin, Splechtna, Delrieux & Matković (2019). A comparison of radial and linear charts for visualizing daily patterns. *IEEE TVCG*. ✓ https://www.cg.tuwien.ac.at/research/publications/2019/waldner-2019-rld/
- Wickham, Cook, Hofmann & Buja (2010). Graphical inference for infovis. *IEEE TVCG* 16(6), 973–979. ✓ https://vita.had.co.nz/papers/inference-infovis.html
- Zgraggen, Zhao, Zeleznik & Kraska (2018). Investigating the effect of the multiple comparisons problem in visual analysis. *CHI '18*. ✓ https://dspace.mit.edu/handle/1721.1/137892
- Not checked in this pass (well known, but confirm details): Cleveland & McGill (1984), Flannery (1956/1971), Purchase (1997), Bakeman & Quera (2011), Zhang et al. NetHOPs (2021).
