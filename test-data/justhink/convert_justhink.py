"""Convert the JUSThink Dialogue and Actions Corpus into the tool's CSV format.

Source: Norman, Dinkar, Nasir, Bruno, Clavel & Dillenbourg (2021), JUSThink Dialogue and Actions Corpus v1.0.0,
Zenodo, doi:10.5281/zenodo.4627104, CC BY 4.0. Download and unzip it, then run:

    python convert_justhink.py <unzipped corpus folder> [--cap 60] [--out .]

Writes justhink-teams.csv (one row per coded episode; each "learner" is a team of two children)
and justhink-team-summary.csv (one row per team: tests, gain group, submissions, best cost).
"""
import argparse
import csv
import os
import re
import statistics

# Event -> code. Robot gestures ("R shows ...") accompany its speech and are dropped,
# so each robot turn counts once. "loads" belongs to reviewing past solutions.
def code_of(subject, verb, obj):
    if subject == 'R':
        return 'Robot talks' if verb == 'says' else None
    if subject == 'T' and verb == 'submits':
        return 'Team submits'
    if verb == 'adds':
        return 'Add track'
    if verb == 'removes':
        return 'Remove track'
    if verb == 'loads':
        return 'Review past solutions'
    if verb == 'presses':
        button = obj.split(' ')[0]
        if button == 'submit':
            return 'Submit blocked' if '(disabled)' in obj else 'Ready to submit'
        if button == 'help':
            return 'Ask for help'
        if button in ('compare', 'previous', 'next', 'apply'):
            return 'Review past solutions'
    return None


def test_scores(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    key = next(r for r in rows if r['team_no'] == 'key')
    out = {}
    for r in rows:
        if r['team_no'] == 'key':
            continue
        out[r['team_no']] = {p: sum(r['q%d_%s' % (i, p)] == key['q%d_%s' % (i, p)] for i in range(1, 11)) for p in 'AB'}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('corpus', help='unzipped corpus folder (contains logs/ and test_responses/)')
    ap.add_argument('--cap', type=float, default=60.0, help='longest episode in seconds; longer gaps count as uncoded')
    ap.add_argument('--last', type=float, default=3.0, help='length in seconds given to each team\'s final event')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    pre = test_scores(os.path.join(a.corpus, 'test_responses', 'justhink19_pretest.csv'))
    post = test_scores(os.path.join(a.corpus, 'test_responses', 'justhink19_posttest.csv'))
    logdir = os.path.join(a.corpus, 'logs')
    files = sorted(f for f in os.listdir(logdir) if re.match(r'justhink19_log_\d+\.csv$', f))

    episodes, summary = [], []
    for f in files:
        rows = list(csv.DictReader(open(os.path.join(logdir, f), encoding='utf-8'), delimiter='\t'))
        team = rows[0]['team_no']
        gain = statistics.mean(post[team][p] - pre[team][p] for p in 'AB')
        group = 'Gained' if gain > 0 else 'No gain'
        ev = [(float(r['time']), code_of(r['subject'], r['verb'], r['object'])) for r in rows]
        ev = [(t, c) for t, c in ev if c]
        ev.sort(key=lambda x: x[0])
        for i, (t, c) in enumerate(ev):
            nxt = ev[i + 1][0] if i + 1 < len(ev) else t + a.last
            end = min(nxt, t + a.cap)
            episodes.append(('T%02d' % int(team), c, '%.3f' % t, '%.3f' % end, group))
        costs = [int(m.group(1)) for r in rows if r['verb'] == 'submits' for m in [re.search(r'cost=(\d+)', r['object'])]]
        opt = int(re.search(r'opt_cost=(\d+)', next(r['object'] for r in rows if r['verb'] == 'submits')).group(1))
        summary.append({
            'learner': 'T%02d' % int(team),
            'pre_A': pre[team]['A'], 'pre_B': pre[team]['B'],
            'post_A': post[team]['A'], 'post_B': post[team]['B'],
            'mean_gain': gain, 'group': group,
            'submissions': len(costs), 'best_cost': min(costs), 'optimal_cost': opt,
            'found_optimal': 'yes' if min(costs) == opt else 'no',
            'activity_s': round(float(rows[-1]['time']), 1), 'coded_events': len(ev),
        })

    with open(os.path.join(a.out, 'justhink-teams.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['learner', 'behaviour', 'start_s', 'end_s', 'group'])
        w.writerows(episodes)
    with open(os.path.join(a.out, 'justhink-team-summary.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    groups = {}
    for s in summary:
        groups[s['group']] = groups.get(s['group'], 0) + 1
    print('%d teams, %d episodes, groups %s, %d found the optimum' % (
        len(summary), len(episodes), groups, sum(s['found_optimal'] == 'yes' for s in summary)))


if __name__ == '__main__':
    main()
