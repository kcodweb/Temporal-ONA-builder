# Evaluation scripts for the paper

| Script | Evaluation in the paper | What it does |
|---|---|---|
| `temporal_views.py` | E1 | The quantities each view encodes (raincloud, TNA-style probabilities, frequency-sized network, integrated view), and the element-by-element comparison |
| `e1_controlled_cases.py` | E1 | Five controlled cases (a–e) with known answers. Writes `out/n<learners>/e1_ratios.csv`, `e1_table.md` and one two-condition log per case |
| `e5_educator_inferences.py` | E2 | A language model reads each figure as an image, with a short description of the activity and its codes, and writes five inferences for teachers (the prompt is in the script). Needs the user's own API key; `--dry-run` writes the prompts without sending anything |
| `e2_e3_pyguru.py` | E3 | Split-half consistency and sensitivity to the link window, duration cap and slice length on a converted PyGuru session (link stability comes from the tool's own **Check stability** setting). Student data: run it locally, outputs go under `test-data/pyguru/` (git-ignored) |
| `export_tool_figure.js` | E1–E3 | Draws a log with the real page (jsdom) and saves the SVG, with optional fixed circle order, normalised time, session length, slice length or groups side by side |

The PyGuru logs are student data and are not included; the JUSThink and CoAuthor converters are in `test-data/`.

Reproduce E1 (synthetic, seeded):

    python scripts/eval/e1_controlled_cases.py --reps 60 --learners 60 --out scripts/eval/out/n60
    python scripts/eval/e1_controlled_cases.py --reps 60 --learners 30 --out scripts/eval/out/n30
    node scripts/eval/export_tool_figure.js scripts/eval/out/n60/e1_case_d.csv scripts/eval/out/figs/e1-case-d.svg --label "Case (d), 60 learners per condition" --groups

A view distinguishes a case when, for at least one element, the median (over repetitions) difference between conditions exceeds three times the mean difference between replicates of the same condition.
