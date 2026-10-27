# CoAuthor: writing with GPT-3 (LAK '24 data)

These are real writing sessions in which people wrote stories or essays with GPT-3 suggestions. The coded events come from a LAK '24 paper that analysed them with epistemic network analysis (ENA).

## Source

- **Paper:** Cheng, Y., Lyons, K., Chen, G., Gašević, D., & Swiecki, Z. (2024). Evidence-centered assessment for writing with generative AI. *LAK '24*, 178–188. https://doi.org/10.1145/3636555.3636866
- **Data and code:** https://github.com/yixin-cheng/coAuthor (MIT licence). The input file is `ENA-analysis/ena_all_new_v2.csv.zip`, downloaded on 22 October 2026.
- **Original dataset:** Lee, M., Liang, P., & Yang, Q. (2022). CoAuthor: Designing a human-AI collaborative writing dataset for exploring language model capabilities. *CHI 2022*. https://coauthor.stanford.edu/ (63 writers recruited on Amazon Mechanical Turk, 1,445 sessions).
- **Licence:** the CoAuthor site states no licence for the data. The derived CSVs are therefore git-ignored; `convert_coauthor.py` rebuilds them from the download. Ask Mina Lee before publishing them.

## Files (rebuilt locally, not committed)

| File | Contents |
|---|---|
| `coauthor-sessions.csv` | 161,730 episodes. Columns: `learner` (one writing session, S0001–S1435), `behaviour`, `start_s`, `end_s` (seconds from the session's first event), `group` (Writer-owned / AI-owned) |
| `coauthor-session-summary.csv` | One row per session: session and worker IDs, genre, ownership, GPT-3 temperature, length, events, episodes |
| `figures/` | Whole-session and groups-side-by-side SVGs (15-minute window, 1-minute slices) |

## How it was coded

The LAK '24 authors coded every event (keystroke, suggestion request, cursor move …) into 16 codes. These are folded into nine behaviours. An event with several codes takes the first that applies in this order:

1. Revise AI text
2. Revise own text
3. Accept suggestion
4. Dismiss suggestion
5. Ask AI (suggestion requested or reopened)
6. Browse suggestions
7. Delete
8. Compose
9. Move cursor

Three of the authors' codes are not kept as behaviours:
- **reflect** marks any edit in the last 10% of a session's events, so its timing is fixed by its definition.
- **relocate** always comes with another code.
- **low/high modification** describe how much a revision changed, not a separate action.

**Episodes:**
- Runs of the same behaviour are merged, so a burst of keystrokes is one Compose episode.
- An episode lasts until the next different behaviour, capped at 60 s; 582 episodes hit the cap.
- "Ask AI" therefore includes waiting for GPT-3 and reading its suggestions.

**Unit:** each writing session. Sessions are nested in 60 writers (about 24 each), so the tool's stability check, which resamples sessions, is optimistic.

**Session length:** 1.9–31.3 min (median 10.3); 95.5% of sessions end by 15 min. Set **Session length = 15** and **Clock-ring slice = 1 min** in the tool.

## Groups

| Group | Sessions | Source |
|---|---|---|
| Ownership: Writer-owned / AI-owned | 704 / 731 | The authors' median split on the share of the final text written by the person |
| Genre: Creative / Argumentative | 821 / 614 | Prompt type |
| GPT-3 temperature: Low / High | in the summary file | Experimental setting per session |

Ownership is the authors' main comparison. It is partly circular: AI-owned texts contain more accepted suggestions by definition.

## First look (15-minute window; exploratory, no statistical tests)

**Whole session:**
- Compose takes the most time (6.0 min per session, 40%), then Ask AI (2.1 min, 14%).
- The strongest link is Delete → Compose (31 per session).
- All 18 links shown hold up in at least 80% of 50 bootstrap resamples.
- **Timing is steady:** per-minute profiles are flat from minute 0 to 9, then fall as sessions end. Revising peaks a little later (own text 6–7′, AI text 7–8′).
- In AI-owned sessions, asking the AI fades about a minute before composing does (minute 9: 45% vs 96% of the minute-0 rate).

**Writer-owned vs AI-owned:**
- Writer-owned sessions compose more (7.3 vs 4.8 min) and cycle Compose ↔ Delete far more (about 38 vs 23 each way).
- AI-owned sessions ask the AI more (2.9 vs 1.3 min). They also chain Ask AI → Accept suggestion (9.5 vs 2.4), Accept → Ask AI again (3.2 vs 0.2), and Move cursor → Revise AI text (2.9 vs 1.0).

**Genre and temperature:** differences are small (at most 0.8 min per behaviour).
