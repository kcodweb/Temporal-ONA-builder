# Evaluation scripts for the ECIS 2027 paper

| Script | What it does |
|---|---|
| `temporal_views.py` | The quantities each view encodes (raincloud, TNA-style probabilities, frequency-sized network, integrated view), and the element-by-element comparison |
| `e1_controlled_cases.py` | E1: five controlled cases (a–e) with known answers. Writes `out/n<learners>/e1_ratios.csv`, `e1_table.md` and one two-condition log per case |
| `e2_e3_pyguru.py` | E2 and E3 on a converted PyGuru day: baseline figures, the numbers behind the eight questions, split-half consistency and sensitivity. Student data: run it locally, outputs go under `test-data/pyguru/` (git-ignored) |
| `export_tool_figure.js` | Draws a log with the real page (jsdom) and saves the SVG, with optional fixed circle order, normalised time or groups side by side; `--brief` also saves the data the AI reading would send |
| `e4_llm_pilot.py` | E4: temporal questions answered by a language model from the integrated view's data and from the separate views' data (start counts as in raincloud plots, transition probabilities as in TNA, optionally time per behaviour), scored against the log. The question bank (35 candidates per log) is generated from the log, and unclear items are dropped before any run (`items.md` says why); `--bank pilot` asks the first pilot's nine questions. Needs the user's own API key. Student data: outputs go under `test-data/pyguru/` |

Reproduce E1 (synthetic, seeded):

    python scripts/eval/e1_controlled_cases.py --reps 60 --learners 60 --out scripts/eval/out/n60
    python scripts/eval/e1_controlled_cases.py --reps 60 --learners 30 --out scripts/eval/out/n30
    node scripts/eval/export_tool_figure.js scripts/eval/out/n60/e1_case_d.csv scripts/eval/out/figs/e1-case-d.svg --label "Case (d), 60 learners per condition" --groups

A view distinguishes a case when, for at least one element, the median (over repetitions) difference between conditions exceeds three times the mean difference between replicates of the same condition.

Run E4 on both converted PyGuru days (the circle order matches the paper figures), then pool them:

    node scripts/eval/export_tool_figure.js test-data/pyguru/pyguru-day1.csv test-data/pyguru/eval-llm/day1.svg --order "Read|Highlight or annotate|Review notes|Run code|See errors|Watch video|Quiz|Assessment|Verify or submit|Navigate" --brief test-data/pyguru/eval-llm/brief-day1.txt
    python scripts/eval/e4_llm_pilot.py test-data/pyguru/pyguru-day1.csv test-data/pyguru/eval-llm/brief-day1.txt --out test-data/pyguru/eval-llm/bank-day1 --model claude-sonnet-5-5 --reps 10
    python scripts/eval/e4_llm_pilot.py --combine test-data/pyguru/eval-llm/bank-day1 test-data/pyguru/eval-llm/bank-day2 --out test-data/pyguru/eval-llm --model claude-sonnet-5-5

(day 2 the same way, with `day2` in the paths). It needs `ANTHROPIC_API_KEY`; `--provider openai --model gpt-4o` (with `OPENAI_API_KEY`) runs the same questions on GPT-4o. `--dry-run` writes the prompts and `items.md` without sending anything. Runs are appended to `runs-<provider>-<model>.jsonl` and skipped when repeated, so an interrupted run resumes; `--score-only` rewrites the report from the saved runs. The first pilot (nine questions, day 2) is reproduced with `--bank pilot --out test-data/pyguru/eval-llm --score-only`.
