"""Convert the PyGuru lab log into the tool's CSV format.

The PyGuru export has one row per action with a timestamp, the seconds until the student's next action
(Timespent_seconds), the action and its one-hot code. 30 students in two groups worked in two class labs
(11 and 12 September 2023, about 90 minutes each, different topics each day).

    python convert_pyguru.py <PyGuru_dataset.csv> [--cap 30] [--out .]

Writes, for each lab day and for both days together (one row per episode):
    pyguru-day1.csv, pyguru-day2.csv, pyguru-both-days.csv   group = Group A / Group B
    pyguru-by-day.csv                                        group = Day 1 / Day 2
Each "learner" is one student on one day (the student's ID plus -D1 or -D2). The data is student data: keep the output local.
"""
import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime

# The export's 14 codes, folded into 10 behaviours (rare codes join the closest one).
BEHAVIOUR = {
    'Read': 'Read', 'Video_watch': 'Watch video', 'Execute': 'Run code', 'See_Errors': 'See errors',
    'Quiz': 'Quiz', 'Assessment': 'Assessment', 'Verify_assessment': 'Verify or submit', 'Submit': 'Verify or submit',
    'Highlight': 'Highlight or annotate', 'Annotate': 'Highlight or annotate',
    'View_Highlight': 'Review notes', 'View_Annotation': 'Review notes',
    'Browse_Topics': 'Navigate', 'Check_messages': 'Navigate',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log', help='PyGuru_dataset.csv')
    ap.add_argument('--cap', type=float, default=30.0, help='longest episode in minutes; longer gaps count as uncoded')
    ap.add_argument('--min-minutes', type=float, default=30.0, help='drop student-days shorter than this (incomplete attendance)')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.log, encoding='utf-8')))
    codes = list(BEHAVIOUR)
    T = lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    days = sorted({r['timestamp'][:10] for r in rows})
    day_no = {d: i + 1 for i, d in enumerate(days)}
    day_end = {d: max(T(r['timestamp']) for r in rows if r['timestamp'].startswith(d)) for d in days}

    per = defaultdict(list)  # (user, day) -> [(time, order, behaviour, timespent)]
    group = {}
    for r in rows:
        on = [c for c in codes if r.get(c) == '1']
        if len(on) != 1:
            continue
        d = r['timestamp'][:10]
        u = r['user_id'].split('.')[0]
        ts = r['Timespent_seconds']
        per[(u, d)].append((T(r['timestamp']), int(r['']), BEHAVIOUR[on[0]], float(ts) if ts not in ('', 'nan') else None))
        group[u] = r['group_name']

    out = {'day1': [], 'day2': [], 'both': [], 'byday': []}
    capped, dropped = 0, []
    # Group A's students first, so the tool lists and draws Group A before Group B.
    for (u, d), ev in sorted(per.items(), key=lambda kv: (group[kv[0][0]], kv[0][1], kv[0][0])):
        ev.sort(key=lambda x: (x[0], x[1]))
        t0 = ev[0][0]
        label = '%s-D%d' % (u, day_no[d])
        if (ev[-1][0] - t0).total_seconds() < a.min_minutes * 60:
            dropped.append(label)
            continue
        for i, (t, _, b, ts) in enumerate(ev):
            gap = (ev[i + 1][0] - t).total_seconds() if i + 1 < len(ev) else None
            dur = ts if ts is not None else gap
            if gap is None:  # last action of the day: it can last no longer than the class
                dur = min(dur if dur is not None else 0, (day_end[d] - t).total_seconds())
            if dur is None:
                dur = 0
            if dur > a.cap * 60:
                dur = a.cap * 60
                capped += 1
            dur = max(dur, 1.0)
            s = (t - t0).total_seconds()
            row = (label, b, '%.0f' % s, '%.0f' % (s + dur))
            out['day%d' % day_no[d]].append(row + (group[u],))
            out['both'].append(row + (group[u],))
            out['byday'].append(row + ('Day %d' % day_no[d],))

    names = {'day1': 'pyguru-day1.csv', 'day2': 'pyguru-day2.csv', 'both': 'pyguru-both-days.csv', 'byday': 'pyguru-by-day.csv'}
    for k, fn in names.items():
        with open(os.path.join(a.out, fn), 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['learner', 'behaviour', 'start_s', 'end_s', 'group'])
            w.writerows(out[k])
    print('%d student-days, %d kept, %d episodes, %d capped at %g min; dropped as shorter than %g min: %s' % (
        len(per), len(per) - len(dropped), len(out['both']), capped, a.cap, a.min_minutes, ', '.join(dropped) or 'none'))


if __name__ == '__main__':
    main()
