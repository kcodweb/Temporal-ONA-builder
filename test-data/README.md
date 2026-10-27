# Test data: collaborative problem solving, 40 minutes (not SRL)

For real data, see [justhink/](justhink/README.md): event logs from 39 teams of children, from an open CC BY 4.0 corpus.

`collab-problem-solving-40min.csv` is **synthetic**: 23 learners in small groups, 1,327 coded discussion episodes, 14:00–14:40. It exists to test the tool, not to report findings. `generate_collab40.py` recreates it exactly (seed 2027).

**Columns:** `student_id`, `code`, `start_time`, `end_time`, all as clock times.

**Codes:** Propose idea, Ask question, Explain, Disagree, Agree, Summarise, Off-task.

## Mixed sequences

Three kinds of learner follow different habits:

| Type | Learners | Habit |
|---|---|---|
| Driver | 9 | Proposes and explains a lot |
| Questioner | 8 | Asks questions and agrees a lot |
| Drifter | 6 | Goes off-task, mostly in minutes 18–30 |

About a third of episodes are followed by a short uncoded gap.

## Answer key: what the tool should show

| Where | Planted pattern | What the tool showed (whole session; 5-min slices, 10-min frames) |
|---|---|---|
| 0–10′ | Proposing and asking dominate | Propose idea is the largest disc (3.4 min per learner); Propose ↔ Ask are the top links |
| 10–28′ | Questions are answered by explanations | Ask question → Explain is the strongest link overall (5.3 per learner, around minute 15) |
| 18–30′ | Drifters go off-task | Off-task peaks in frame 3 (20–30′: 1.4 min per learner, against 0.4–0.9 in the other frames) |
| 10–30′ | Disagreement leads to explaining | Disagree → Explain appears among the top links in frame 3 |
| 28–40′ | Agreement leads to summarising | Agree → Summarise is the top link in frame 4 (around minute 35); Summarise is the largest disc there (4.5 min) |
| Whole | Explaining takes the most time | Explain: 13.9 min per learner |

**Not planted, so it should not look like a strong pattern:**
- Agree and Disagree in the opening frame.
- Any difference between groups. Group IDs (G1, G2, …) carry no meaning.

The learner types are not in the file. That is deliberate, to see whether heterogeneity can be spotted without them.

`collab-problem-solving-40min-groups.csv` is the same log with a `group` column holding the learner type (Driver, Questioner, Drifter), for testing the group comparison. Recreate it with `python generate_collab40.py collab-problem-solving-40min-groups.csv --groups`. Expected: questioners spend far more time asking (about 6.4 vs 1.6 min per learner for drivers), drivers propose and explain more, and drifters have the most off-task time, peaking around 25–30′.
