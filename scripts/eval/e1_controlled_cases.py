"""E1: controlled cases with known answers.

Five cases, each with two conditions (X, Y) that differ in one temporal perspective only (case e: not at all).
For every case and view we compute how far the two conditions differ, relative to the difference between two
independent replicates of the same condition, over many repetitions:

    python scripts/eval/e1_controlled_cases.py [--reps 30] [--learners 30] [--out scripts/eval/out]

Writes e1_ratios.csv (median ratio per case, view and channel), e1_table.md (the paper's table) and, for each case,
a two-condition episode log (e1_case_<x>.csv, group = Condition X / Condition Y) that the tool can draw side by side.
"""
import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from temporal_views import VIEWS, channels, element_ratios  # noqa: E402

NAMES = ['Plan', 'Read', 'Code', 'Debug', 'Help']
P_, R_, C_, D_, H_ = range(5)
T = 60.0
BASE_DUR = np.array([1.5, 2.0, 3.0, 2.0, 1.5])  # mean episode minutes


def chain(rows):
    m = np.zeros((5, 5))
    for a, row in rows.items():
        for b, p in row.items():
            m[a, b] = p
    assert np.allclose(m.sum(axis=1), 1), m.sum(axis=1)
    return m


# Base chain: Read and Debug play exchangeable roles around Code, so swapping their rows keeps visit rates equal.
B0 = chain({
    P_: {R_: .3, D_: .3, C_: .3, H_: .1},
    R_: {C_: .6, P_: .1, H_: .15, D_: .15},
    D_: {C_: .6, P_: .1, H_: .15, R_: .15},
    C_: {R_: .35, D_: .35, P_: .2, H_: .1},
    H_: {C_: .5, R_: .2, D_: .2, P_: .1},
})


def without_help(m):
    m = m.copy()
    m[:, H_] = 0
    return m / m.sum(axis=1, keepdims=True)


B0_NOHELP = without_help(B0)

# Case b: the Read -> Code -> Debug cycle runs one way in X and the other way in Y. Plan and Help lead into the
# cycle evenly, so reversing it only relabels states: frequencies and timing stay the same.
CYCLE_X = chain({
    P_: {R_: .8 / 3, C_: .8 / 3, D_: .8 / 3, H_: .2},
    R_: {C_: .8, P_: .1, H_: .1},
    C_: {D_: .8, P_: .1, H_: .1},
    D_: {R_: .8, P_: .1, H_: .1},
    H_: {R_: 1 / 3, C_: 1 / 3, D_: 1 / 3},
})
CYCLE_Y = chain({
    P_: {R_: .8 / 3, C_: .8 / 3, D_: .8 / 3, H_: .2},
    R_: {D_: .8, P_: .1, H_: .1},
    D_: {C_: .8, P_: .1, H_: .1},
    C_: {R_: .8, P_: .1, H_: .1},
    H_: {R_: 1 / 3, C_: 1 / 3, D_: 1 / 3},
})
CYCLE_DUR = np.array([1.5, 2.0, 2.0, 2.0, 1.5])  # equal durations on the cycle, so only the direction differs

# Case d: in a "burst" Debug is followed by Help, outside it Read is; the two chains are the same up to swapping
# Read and Debug, so Help is equally frequent at all times and Debug -> Help totals are equal in X and Y.
BURST = chain({
    P_: {R_: .3, D_: .3, C_: .3, H_: .1},
    D_: {H_: .5, C_: .4, P_: .05, R_: .05},
    R_: {H_: .02, C_: .78, P_: .1, D_: .1},
    C_: {R_: .35, D_: .35, P_: .2, H_: .1},
    H_: {C_: .5, R_: .2, D_: .2, P_: .1},
})
CALM = BURST.copy()
CALM[[R_, D_]] = CALM[[D_, R_]]
CALM[:, [R_, D_]] = CALM[:, [D_, R_]]


def stationary(m):
    vals, vecs = np.linalg.eig(m.T)
    v = np.real(vecs[:, np.argmin(np.abs(vals - 1))])
    return v / v.sum()


def long_debug(m, base):
    """Debug lasts three times as long; other behaviours shrink so the mean episode length stays the same."""
    pi = stationary(m)
    d = base.copy()
    d[D_] *= 3
    others = [i for i in range(5) if i != D_]
    target = float(pi @ base)
    s = (target - pi[D_] * d[D_]) / float(pi[others] @ base[others])
    d[others] = base[others] * s
    return d


CASES = {
    'a': ('Same order, different timing', lambda t, c: (B0 if (t < 30) == (c == 'X') else B0_NOHELP, BASE_DUR)),
    'b': ('Same timing, different order', lambda t, c: (CYCLE_X if c == 'X' else CYCLE_Y, CYCLE_DUR)),
    'c': ('Same counts, different durations', lambda t, c: (B0, BASE_DUR if c == 'X' else long_debug(B0, BASE_DUR))),
    'd': ('Same transition, different moments',
          lambda t, c: (BURST if ((t < 15 or t >= 45) if c == 'X' else (15 <= t < 45)) else CALM, BASE_DUR)),
    'e': ('Negative control (no difference)', lambda t, c: (B0, BASE_DUR)),
}


def simulate(case, cond, n, rng):
    spec = CASES[case][1]
    log = []
    for _ in range(n):
        t, b, eps = 0.0, P_, []
        while t < T:
            m, dur = spec(t, cond)
            d = rng.gamma(2.0, dur[b] / 2.0)
            eps.append((b, t, min(t + d, T)))
            t += d
            if t >= T:
                break
            m, _ = spec(t, cond)
            b = int(rng.choice(5, p=m[b]))
        log.append(eps)
    return log


def element_name(ch, i):
    if ch in ('raincloud', 'clock', 'ona_nodes', 'share'):
        return NAMES[i]
    return NAMES[i // 5] + '>' + NAMES[i % 5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reps', type=int, default=30)
    ap.add_argument('--learners', type=int, default=30)
    ap.add_argument('--threshold', type=float, default=3.0)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows, table = [], []
    for case, (title, _) in CASES.items():
        chs_all = [ch for v in VIEWS.values() for ch in v]
        reps = {c: {ch: [] for ch in chs_all} for c in ('X', 'Y', 'X2', 'Y2')}
        for r in range(a.reps):
            rng = np.random.default_rng(20261026 + 1000 * ord(case) + r)
            for c in ('X', 'Y', 'X2', 'Y2'):
                ch_vals = channels(simulate(case, c[0], a.learners, rng), 5, T)
                for ch in chs_all:
                    reps[c][ch].append(ch_vals[ch])
        line = {'case': case, 'title': title}
        for view, chs in VIEWS.items():
            best = (0.0, '', '')
            for ch in chs:
                rr = element_ratios(reps['X'][ch], reps['Y'][ch], reps['X2'][ch], reps['Y2'][ch], ch)
                i = int(np.nanargmax(rr))
                rows.append([case, title, view, ch, round(float(np.nanmax(rr)), 2), element_name(ch, i)])
                if np.nanmax(rr) > best[0]:
                    best = (float(np.nanmax(rr)), ch, element_name(ch, i))
            line[view] = (round(best[0], 1), best[1] + ': ' + best[2], best[0] > a.threshold)
        table.append(line)
        # One two-condition log per case for the tool (group column), with a fixed seed.
        rng = np.random.default_rng(7 + ord(case))
        with open(os.path.join(a.out, 'e1_case_%s.csv' % case), 'w', newline='') as fh:
            wcsv = csv.writer(fh)
            wcsv.writerow(['learner', 'behaviour', 'start', 'end', 'group'])
            for cond in ('X', 'Y'):
                for li, eps in enumerate(simulate(case, cond, a.learners, rng)):
                    for b, s, e in eps:
                        wcsv.writerow(['%s%02d' % (cond, li + 1), NAMES[b], '%.3f' % s, '%.3f' % e, 'Condition ' + cond])

    with open(os.path.join(a.out, 'e1_ratios.csv'), 'w', newline='') as fh:
        wcsv = csv.writer(fh)
        wcsv.writerow(['case', 'title', 'view', 'channel', 'largest_element_ratio', 'element'])
        wcsv.writerows(rows)
    views = list(VIEWS)
    md = ['| Case | ' + ' | '.join(views) + ' |', '|' + ' --- |' * (len(views) + 1)]
    for line in table:
        cells = []
        for v in views:
            val, ch, yes = line[v]
            cells.append('%s %.1f (%s)' % ('**yes**' if yes else 'no', val, ch))
        md.append('| (%s) %s | %s |' % (line['case'], line['title'], ' | '.join(cells)))
    open(os.path.join(a.out, 'e1_table.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
