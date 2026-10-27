"""Convert the coded CoAuthor events of Cheng et al. (LAK '24) into the tool's CSV format.

Source: Cheng, Lyons, Chen, Gasevic & Swiecki (2024), Evidence-centered Assessment for Writing with
Generative AI, LAK '24, doi:10.1145/3636555.3636866. Data and code: github.com/yixin-cheng/coAuthor (MIT).
The events come from the CoAuthor dataset (Lee, Liang & Yang, CHI 2022).

Download ENA-analysis/ena_all_new_v2.csv.zip from that repo, unzip it, then run:

    python convert_coauthor.py <ena_all_new_v2.csv> [--cap 60] [--out .]

Writes coauthor-sessions.csv (one row per episode; each "learner" is one writing session) and
coauthor-session-summary.csv (one row per session: writer, genre, ownership, temperature, length).
"""
import argparse
import csv
import os
from datetime import datetime, timezone

# The authors' event codes, folded into nine behaviours. An event with several codes takes the first
# that applies in this order: revising an existing sentence says more than the keystroke that did it.
# "reflect" (any edit in the last 10% of a session's events) and "relocate" are not used as codes:
# reflect is late by definition, and both always come with an edit that is coded anyway.
ORDER = [
    ('reviseSugg', 'Revise AI text'),
    ('reviseUser', 'Revise own text'),
    ('acceptSugg', 'Accept suggestion'),
    ('dismissSugg', 'Dismiss suggestion'),
    ('seekSugg', 'Ask AI'),
    ('reopenSugg', 'Ask AI'),
    ('hoverSugg', 'Browse suggestions'),
    ('delete', 'Delete'),
    ('compose', 'Compose'),
    ('cursorFwd', 'Move cursor'),
    ('cursorBwd', 'Move cursor'),
    ('cursorSelect', 'Move cursor'),
]
# Events without a usable code fall back on what the event was.
FALLBACK = {'text-insert': 'Compose', 'text-delete': 'Delete', 'cursor-forward': 'Move cursor',
            'cursor-backward': 'Move cursor', 'cursor-select': 'Move cursor', 'suggestion-get': 'Ask AI',
            'suggestion-hover': 'Browse suggestions', 'suggestion-close': 'Dismiss suggestion'}


def code_of(r):
    for col, name in ORDER:
        if r[col] == '1':
            return name
    if r['eventName'] == 'text-insert' and r['eventSource'] == 'api':
        return 'Accept suggestion'
    return FALLBACK.get(r['eventName'])


def seconds(s):  # "08/25/2021 05:27:40:192000"
    d, t = s.split(' ')
    h, m, sec, us = t.split(':')
    day = datetime.strptime(d, '%m/%d/%Y').replace(tzinfo=timezone.utc).timestamp()
    return day + int(h) * 3600 + int(m) * 60 + int(sec) + int(us) / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('events', help='ena_all_new_v2.csv from the coAuthor repo')
    ap.add_argument('--cap', type=float, default=60.0, help='longest episode in seconds; longer pauses count as uncoded')
    ap.add_argument('--last', type=float, default=1.0, help='length in seconds given to each session\'s final event')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    sessions = {}  # session -> {'meta':..., 'ev': [(t, code)]}
    skipped = 0
    with open(a.events, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            c = code_of(r)
            if not c:
                skipped += 1
                continue
            s = sessions.setdefault(r['session_id'], {'meta': r, 'ev': []})
            s['ev'].append((seconds(r['eventTimestamp']), int(r['event_id']), c))

    rows, summary = [], []
    ids = sorted(sessions, key=lambda k: (sessions[k]['meta']['worker_id'], k))
    for n, sid in enumerate(ids, 1):
        s = sessions[sid]
        ev = sorted(s['ev'], key=lambda x: (x[0], x[1]))
        t0 = ev[0][0]
        own = 'Writer-owned' if s['meta']['ownershipMetadata'] == 'user' else 'AI-owned'
        label = 'S%04d' % n
        # Merge runs of the same behaviour (a burst of keystrokes is one Compose episode).
        runs = []
        for t, _, c in ev:
            if runs and runs[-1][1] == c:
                continue
            runs.append([t, c])
        for i, (t, c) in enumerate(runs):
            nxt = runs[i + 1][0] if i + 1 < len(runs) else t + a.last
            end = min(nxt, t + a.cap)
            rows.append((label, c, '%.3f' % (t - t0), '%.3f' % (end - t0), own))
        summary.append({
            'learner': label, 'session_id': sid, 'worker_id': s['meta']['worker_id'],
            'genre': s['meta']['genre'], 'ownership': own,
            'temperature': 'high' if s['meta']['highTemp'] == '1' else 'low',
            'minutes': round((ev[-1][0] - t0) / 60, 2), 'events': len(ev), 'episodes': len(runs),
        })

    with open(os.path.join(a.out, 'coauthor-sessions.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['learner', 'behaviour', 'start_s', 'end_s', 'group'])
        w.writerows(rows)
    with open(os.path.join(a.out, 'coauthor-session-summary.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    print('%d sessions, %d writers, %d episodes, %d events without a code skipped' % (
        len(summary), len({s['worker_id'] for s in summary}), len(rows), skipped))


if __name__ == '__main__':
    main()
