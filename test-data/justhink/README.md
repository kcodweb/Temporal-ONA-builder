# JUSThink: real collaborative learning logs

`justhink-teams.csv` is **real data**: event logs from 39 teams of two children (aged 9–12) solving a graph problem together with a robot. Each team built a railway network linking Swiss "gold mines" at the lowest cost.

## Source and licence

Norman, U., Dinkar, T., Nasir, J., Bruno, B., Clavel, C., & Dillenbourg, P. (2021). *JUSThink Dialogue and Actions Corpus* (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.4627104

- **Licence:** CC BY 4.0. The files here are derived from the corpus; the changes are listed below.
- **Study:** Nasir, Norman, Bruno & Dillenbourg (2020), "When positive perception of the robot has no effect on learning", IEEE RO-MAN, doi:10.1109/RO-MAN47096.2020.9223343.
- **Downloaded:** 14 October 2026. The zip is 241,818 bytes with MD5 `29df994b770d1f5b62540a2f92d83c81`, matching Zenodo.

## Files

| File | Contents |
|---|---|
| `justhink-teams.csv` | 7,797 coded episodes. Columns: `learner` (team ID, e.g. T07), `behaviour`, `start_s`, `end_s` (seconds from the start of the activity), `group` |
| `justhink-team-summary.csv` | One row per team: pre- and post-test scores of both children, mean gain, group, number of submissions, best cost, whether the team found the optimum, activity length |
| `convert_justhink.py` | Rebuilds both files from the unzipped corpus: `python convert_justhink.py <corpus folder>` |
| `figures/` | Whole-session and groups-side-by-side SVGs exported from the tool (default settings, Paper theme) |

In the tool, each "learner" is a **team of two**. The tool does not know about teams, so the paper should say that the unit of analysis is the team.

## How the log was coded

Every logged action becomes one episode. An episode lasts until the team's next coded event, capped at **60 s** (`--cap`). Longer silences count as uncoded time; this affects 59 of 7,797 episodes. Each team's final event gets 3 s (`--last`).

| Code | Logged events | Events |
|---|---|---|
| Add track | A or B *adds* an edge | 3,076 |
| Remove track | A or B *removes* an edge | 740 |
| Review past solutions | *presses* compare, previous, next or apply; *loads* a past solution | 1,996 |
| Ready to submit | *presses* submit (enabled or selected); one child signals the solution is ready | 664 |
| Submit blocked | *presses* submit (disabled); the solution did not yet connect every mine | 155 |
| Team submits | *T submits*, once both children have pressed submit | 271 |
| Ask for help | *presses* help | 394 |
| Robot talks | *R says* (robot feedback and prompts) | 501 |

**Changes from the corpus:**
- Robot gestures (*R shows …*, 960 events) are dropped because they accompany the robot's speech; keeping them would count each robot turn twice.
- Who acted (child A or B) is not kept in the code.
- The transcripts (10 teams only) are not used.

## Groups: learning gain

- Each child's pre- and post-test (10 items) is scored against the key.
- A team's gain is the mean of its two children's post − pre scores.
- The median team gain is exactly 0, so the groups are **Gained** (mean gain > 0, 17 teams) and **No gain** (≤ 0, 22 teams). This mirrors CTAM4SRL's split into high and low scorers.
- `justhink-team-summary.csv` also has `found_optimal` (8 of 39 teams found the optimum) if a split by task performance is wanted instead.

## First look (default settings; exploratory, no statistical tests)

**Whole session:**
- 39 teams, session 0–36′.
- Coded time covers 23.9 of 36 min per team on average, because teams stopped at different times (11–36 min).
- Most time goes to Add track (11.5 min per team, 32%).
- The strongest link is Add track → Remove track (12 per team, around minute 15).
- Help and blocked submits peak in the first 5 minutes; reviewing past solutions peaks at 15–20′.

**Groups side by side** (Gained vs No gain):
- Gained teams spent more time reviewing past solutions (4.1 vs 2.6 min) and adding track (12.3 vs 10.8 min).
- No-gain teams asked for help more (1.6 vs 1.1 min) and more often went from Ask for help to Add track (3.1 vs 1.4 per team).

**Stability check** (200 resamples): with repeats merged and loops hidden, 14 of the 16 links shown hold up in at least 80% of resamples.

All of these are leads to check, not findings.
