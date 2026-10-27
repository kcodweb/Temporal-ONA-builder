"""E2 and E3 on a converted PyGuru lab day (student data: inputs and outputs stay local, never committed).

    python scripts/eval/e2_e3_pyguru.py test-data/pyguru/pyguru-day2.csv --out test-data/pyguru/eval-day2

E2: the separate views of the same data (raincloud plots of episode start times, a first-order transition-probability
network as in TNA) and the numbers behind the integrated view's answers to the eight temporal questions.
E3: consistency between the two random halves of the class (the workshop's Group A and Group B) and sensitivity of
the main readings to the link window, the duration cap and the slice length.
"""
import argparse
import csv
import os
from collections import defaultdict

import numpy as np
from scipy.stats import gaussian_kde, spearmanr

ORDER = ['Read', 'Highlight or annotate', 'Review notes', 'Run code', 'See errors', 'Watch video', 'Quiz',
         'Assessment', 'Verify or submit', 'Navigate']


def load(path):
    seqs, group = defaultdict(list), {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        seqs[r['learner']].append((ORDER.index(r['behaviour']), float(r['start_s']) / 60, float(r['end_s']) / 60))
        group[r['learner']] = r['group']
    for q in seqs.values():
        q.sort(key=lambda x: x[1])
    return seqs, group


def normalise(seqs):
    out = {}
    for l, q in seqs.items():
        st, en = q[0][1], max(e for _, _, e in q)
        k = 100 / (en - st) if en > st else 0
        out[l] = [(b, (s - st) * k, (e - st) * k) for b, s, e in q]
    return out


def session_length(seqs, sl):
    """Session length as the tool sets it: the last end, rounded up to a fine step (about 1/60 of the session)."""
    raw = max(e for q in seqs.values() for _, _, e in q)
    ladder = [0.25, 0.5, 1, 2, 5, 10, 15, 20, 30, 60, 120]
    g = min(sl, next(v for v in ladder if v >= raw / 60 - 1e-9))
    return float(np.ceil((raw - 1e-9) / g) * g)


def measures(seqs, L, sl, w=2, cap=None):
    """The integrated view's quantities: minutes per learner, clock profile, links with time profile and mean time."""
    B, n, ns = len(ORDER), len(seqs), int(np.ceil(L / sl - 1e-9))
    mins, prof = np.zeros(B), np.zeros((B, ns))
    links, ltime, lsum = np.zeros((B, B)), np.zeros((B, B, ns)), np.zeros((B, B))
    for q in seqs.values():
        q = [(b, s, min(e, s + cap) if cap else e) for b, s, e in q]
        for i, (b, s, e) in enumerate(q):
            mins[b] += max(0, min(e, L) - s)
            for k in range(ns):
                prof[b, k] += max(0, min(e, (k + 1) * sl, L) - max(s, k * sl))
            for j in range(max(0, i - (w - 1)), i):
                a = q[j][0]
                links[a, b] += 1
                lsum[a, b] += s
                if s < L:
                    ltime[a, b, min(int(s // sl), ns - 1)] += 1
    mean_t = np.divide(lsum, links, out=np.zeros_like(lsum), where=links > 0)
    return {'mins': mins / n, 'prof': prof / n, 'links': links / n, 'ltime': ltime / n, 'mean_t': mean_t, 'n': n,
            'ns': ns}


def peaks(m, sl):
    return {ORDER[b]: (int(np.argmax(m['prof'][b])) * sl, int(np.argmax(m['prof'][b])) * sl + sl)
            for b in range(len(ORDER)) if m['mins'][b] > 0}


def top_links(m, k=10, loops=True):
    pairs = [((a, b), m['links'][a, b]) for a in range(len(ORDER)) for b in range(len(ORDER))
             if m['links'][a, b] > 0 and (loops or a != b)]
    return sorted(pairs, key=lambda x: -x[1])[:k]


def name(ab):
    return '%s -> %s' % (ORDER[ab[0]], ORDER[ab[1]])


def raincloud(seqs, L, path, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    starts = defaultdict(list)
    for q in seqs.values():
        for b, s, _ in q:
            starts[b].append(s)
    fig, ax = plt.subplots(figsize=(8, 6.4), dpi=200)
    rng = np.random.default_rng(1)
    for row, b in enumerate(range(len(ORDER))):
        y = len(ORDER) - row
        xs = np.array(starts.get(b, []))
        if len(xs) > 2 and np.ptp(xs) > 0:
            grid = np.linspace(0, L, 300)
            dens = gaussian_kde(xs)(grid)
            ax.fill_between(grid, y, y + 0.42 * dens / dens.max(), color='#438CEB', alpha=0.55, lw=0)
        if len(xs):
            ax.boxplot(xs, positions=[y - 0.08], vert=False, widths=0.1, showfliers=False, manage_ticks=False)
            ax.scatter(xs, y - 0.28 + rng.uniform(-0.07, 0.07, len(xs)), s=2, color='#225B8D', alpha=0.5)
    ax.set_yticks([len(ORDER) - i for i in range(len(ORDER))], ORDER)
    ax.set_xlim(0, L)
    ax.set_xlabel('Minute of session (episode start times)')
    ax.set_title(title, loc='left', fontsize=11)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def transition_network(seqs, path, title, min_p=0.15):
    """First-order transition probabilities as in TNA, self-transitions included (shown as the number in each node)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    B = len(ORDER)
    counts = np.zeros((B, B))
    for q in seqs.values():
        for i in range(1, len(q)):
            counts[q[i - 1][0], q[i][0]] += 1
    rows = counts.sum(axis=1, keepdims=True)
    p = np.divide(counts, rows, out=np.zeros_like(counts), where=rows > 0)
    ang = -np.pi / 2 + 2 * np.pi * np.arange(B) / B
    xy = np.c_[np.cos(ang), -np.sin(ang)]  # clockwise from the top, as in the integrated view
    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=200)
    for a in range(B):
        for b in range(B):
            if a != b and p[a, b] >= min_p:
                ax.add_patch(FancyArrowPatch(xy[a], xy[b], connectionstyle='arc3,rad=0.15', arrowstyle='-|>',
                                             mutation_scale=12, lw=0.5 + 6 * p[a, b], color='#555', alpha=0.75,
                                             shrinkA=20, shrinkB=20))
    for i in range(B):
        ax.scatter(*xy[i], s=1000, color='#438CEB', zorder=3)
        ax.text(*xy[i], '%.2f' % p[i, i], ha='center', va='center', fontsize=7.5, color='white', zorder=4)
        lx, ly = xy[i] * 1.33
        ax.text(lx, ly, ORDER[i], ha='center', va='center', fontsize=9)
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.55, 1.55)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title + ': edges with p ≥ %.2f; number in node = self-transition' % min_p, loc='left', fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--out', required=True)
    ap.add_argument('--slice', type=float, default=10)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    seqs, group = load(a.csv)
    L = session_length(seqs, a.slice)
    rep = []

    # E2: separate views of the same data, and the integrated view's numbers for the eight questions.
    raincloud(seqs, L, os.path.join(a.out, 'baseline-raincloud.png'), 'Raincloud plots of episode start times')
    p = transition_network(seqs, os.path.join(a.out, 'baseline-tna.png'), 'Transition probabilities')
    m = measures(seqs, L, a.slice)
    tot = m['mins'].sum()
    rep.append('# E2 numbers (%d learners, session 0-%g min, slices of %g min)\n' % (m['n'], L, a.slice))
    rep.append('Q1 time per learner: ' + ', '.join('%s %.1f min (%.0f%%)' % (ORDER[b], m['mins'][b], 100 * m['mins'][b] / L)
                                                for b in np.argsort(-m['mins'])))
    rep.append('Q2 busiest slice: ' + ', '.join('%s %g-%g' % (k, *v) for k, v in sorted(peaks(m, a.slice).items(), key=lambda kv: kv[1])))
    rep.append('Q4/Q5 strongest links between behaviours (per learner, mean minute): ' + ', '.join(
        '%s %.2f (min %.0f)' % (name(ab), v, m['mean_t'][ab]) for ab, v in top_links(m, 8, loops=False)))
    se = ORDER.index('See errors')
    after = sorted(((b, m['links'][se, b]) for b in range(len(ORDER)) if m['links'][se, b] > 0), key=lambda x: -x[1])
    rep.append('Q6 after See errors: ' + ', '.join('%s %.2f per learner, mean minute %.0f, busiest slice %g-%g' % (
        ORDER[b], v, m['mean_t'][se, b], int(np.argmax(m['ltime'][se, b])) * a.slice, int(np.argmax(m['ltime'][se, b])) * a.slice + a.slice) for b, v in after[:4]))
    rep.append('Q7 coverage: %.1f of %g min per learner coded (%.0f%%)' % (tot, L, 100 * tot / L))
    rep.append('TNA probabilities from See errors: ' + ', '.join('%s %.2f' % (ORDER[b], p[se, b]) for b in np.argsort(-p[se])[:4]))
    mn = measures(normalise(seqs), 100, 10)
    rep.append('Normalised time, busiest tenth: ' + ', '.join('%s %g-%g%%' % (k, *v) for k, v in sorted(peaks(mn, 10).items(), key=lambda kv: kv[1])))
    rep.append('Normalised time, strongest link: %s, mean %.0f%% of session' % (name(top_links(mn, 1, False)[0][0]), mn['mean_t'][top_links(mn, 1, False)[0][0]]))

    # E3a: consistency between the two random halves.
    halves = sorted(set(group.values()))
    hm = [measures({l: q for l, q in seqs.items() if group[l] == g}, L, a.slice) for g in halves]
    rho = spearmanr(hm[0]['mins'], hm[1]['mins']).correlation
    pk = [peaks(h, a.slice) for h in hm]
    same = sum(1 for k in pk[0] if k in pk[1] and abs(pk[0][k][0] - pk[1][k][0]) <= a.slice)
    t10 = [set(ab for ab, _ in top_links(h, 10)) for h in hm]
    rep.append('\n# E3 consistency between random halves (%s: %d, %s: %d learners)' % (halves[0], hm[0]['n'], halves[1], hm[1]['n']))
    rep.append('Spearman rho of time per behaviour: %.2f' % rho)
    rep.append('Busiest slice the same or adjacent: %d of %d behaviours' % (same, len(pk[0])))
    rep.append('Overlap of the ten strongest links: %d of 10' % len(t10[0] & t10[1]))
    rep.append('Most time: %s vs %s; strongest link: %s vs %s' % (
        ORDER[int(np.argmax(hm[0]['mins']))], ORDER[int(np.argmax(hm[1]['mins']))],
        name(top_links(hm[0], 1, False)[0][0]), name(top_links(hm[1], 1, False)[0][0])))

    # E3b: sensitivity of the main readings to the settings.
    rep.append('\n# E3 sensitivity (reference: w = 2, cap 30 min, slice %g min)' % a.slice)
    ref = m
    ref_top5 = set(ab for ab, _ in top_links(ref, 5, False))
    ref_pk = peaks(ref, a.slice)
    for label, kw in [('w = 3', dict(w=3)), ('w = 4', dict(w=4)), ('cap 10 min', dict(cap=10)), ('slice 5 min', dict(sl=5))]:
        sl = kw.pop('sl', a.slice)
        mm = measures(seqs, L, sl, **kw)
        pk2 = peaks(mm, sl)
        moved = [k for k in ref_pk if k in pk2 and abs(((pk2[k][0] + pk2[k][1]) / 2) - ((ref_pk[k][0] + ref_pk[k][1]) / 2)) > a.slice]
        top5 = set(ab for ab, _ in top_links(mm, 5, False))
        rep.append('%s: most time %s (%.1f min); strongest link %s; top-5 links shared %d of 5; busiest slice moved by more than one slice for %s' % (
            label, ORDER[int(np.argmax(mm['mins']))], mm['mins'].max(), name(top_links(mm, 1, False)[0][0]),
            len(top5 & ref_top5), ', '.join(moved) if moved else 'none'))
    open(os.path.join(a.out, 'e2_e3_numbers.md'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
