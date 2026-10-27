"""Quantities encoded by four temporal views of a coded episode log, for the paper's evaluation.

An episode log is a list of learners; each learner is a list of (behaviour index, start, end) in minutes, sorted by
start. The functions below compute, for each view, the numbers its marks encode:

  raincloud   episode start times per behaviour, as counts per learner in each slice (the points and their spread)
  tna         first-order transition probabilities (rows sum to 1), as in transition network analysis
  ona_nodes   episodes per learner for each behaviour (frequency-sized nodes)
  ona_edges   transitions per learner (frequency-weighted ordered links, link window w)
  share       time share of each behaviour (integrated view: disc area)
  clock       share of each slice spent in each behaviour (integrated view: clock ring)
  links       transitions per learner (integrated view: arrow strength), same as ona_edges
  link_time   transitions per learner in each slice, by response start (integrated view: arrow timeline)

The integrated-view formulas follow the tool (CLAUDE.md, "Formulas"): per-learner means, overlap with the window,
link A->B counted when B starts within w-1 episodes after A, timed at the response start.
"""
import numpy as np

VIEWS = {
    'Raincloud plots': ['raincloud'],
    'Transition network (TNA)': ['tna'],
    'Frequency-sized ordered network': ['ona_nodes', 'ona_edges'],
    'Integrated temporal network': ['share', 'clock', 'links', 'link_time'],
}


def overlap(s, e, a, b):
    return max(0.0, min(e, b) - max(s, a))


def channels(log, B, T, n_slices=12, w=2):
    N = len(log)
    sl = T / n_slices
    rain = np.zeros((B, n_slices))
    trans = np.zeros((B, B))
    nodes = np.zeros(B)
    share = np.zeros(B)
    clock = np.zeros((B, n_slices))
    link_time = np.zeros((B, B, n_slices))
    for eps in log:
        for i, (b, s, e) in enumerate(eps):
            nodes[b] += 1
            if s < T:
                rain[b, min(int(s // sl), n_slices - 1)] += 1
            share[b] += overlap(s, e, 0, T)
            for k in range(n_slices):
                clock[b, k] += overlap(s, e, k * sl, (k + 1) * sl)
            for j in range(max(0, i - (w - 1)), i):
                a = eps[j][0]
                trans[a, b] += 1
                if s < T:
                    link_time[a, b, min(int(s // sl), n_slices - 1)] += 1
    rows = trans.sum(axis=1, keepdims=True)
    tna = np.divide(trans, rows, out=np.zeros_like(trans), where=rows > 0)
    return {
        'raincloud': rain / N,
        'tna': tna,
        'ona_nodes': nodes / N,
        'ona_edges': trans / N,
        'share': share / (N * T),
        'clock': clock / (N * sl),
        'links': trans / N,
        'link_time': link_time / N,
    }


# A reader looks at one mark at a time: one behaviour's raincloud or clock ring, one disc, one link or one link's
# timeline. So differences are judged per element: the last axis holds the slices of a timeline, if any.
ELEMENT_AXES = {'raincloud': 1, 'clock': 1, 'link_time': 2, 'tna': 0, 'ona_nodes': 0, 'ona_edges': 0, 'share': 0,
                'links': 0}


def element_ratios(xs, ys, x2s, y2s, ch):
    """Median over repetitions of |X - Y| for each element, divided by the mean |X - X'| of replicates.

    xs, ys, x2s, y2s: lists (one per repetition) of the channel's array for condition X, Y and their replicates.
    Returns an array of ratios, one per element (behaviour, link or behaviour pair); elements that never vary are nan.
    """
    k = ELEMENT_AXES[ch]
    X, Y, X2, Y2 = (np.array(v) for v in (xs, ys, x2s, y2s))
    if k:  # a timeline per element: distance over its slices
        diff = np.linalg.norm(X - Y, axis=-1)
        noise = (np.linalg.norm(X - X2, axis=-1) + np.linalg.norm(Y - Y2, axis=-1)) / 2
    else:  # one number per element
        diff = np.abs(X - Y)
        noise = (np.abs(X - X2) + np.abs(Y - Y2)) / 2
    med = np.median(diff, axis=0)
    base = noise.mean(axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.where(base > 0, med / base, np.nan)
    return r.ravel()
