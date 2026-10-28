# Synthetic 40-minute collaborative problem-solving log (not SRL) with mixed learner sequences
# and planted, known patterns for testing the Integrated Temporal Network builder.
import random, csv, sys

random.seed(2027)  # run: python generate_collab40.py collab-problem-solving-40min.csv [--groups]
CODES = ['Propose idea', 'Ask question', 'Explain', 'Disagree', 'Agree', 'Summarise', 'Off-task']
P, A, E, D, G, S, O = range(7)
DUR = {P: (20, 60), A: (8, 25), E: (30, 90), D: (10, 30), G: (5, 15), S: (30, 75), O: (40, 150)}  # seconds

# Three learner types with different habits (the "mixed sequences").
TYPES = {'driver': 9, 'questioner': 8, 'drifter': 6}
BIAS = {
    'driver':     {P: 2.0, E: 1.8, A: 0.5, O: 0.3},
    'questioner': {A: 2.4, G: 1.4, P: 0.5, E: 0.7, O: 0.5},
    'drifter':    {O: 1.0, G: 1.2, D: 0.6},
}

def phase_weights(t):
    """Base weights by minute: opening (0-10), working (10-28), closing (28-40)."""
    if t < 10:
        return {P: 4, A: 3, E: 1, D: 0.5, G: 1, S: 0.2, O: 0.4}
    if t < 28:
        return {P: 1, A: 2.5, E: 3.5, D: 1.6, G: 1, S: 0.4, O: 0.6}
    return {P: 0.5, A: 1, E: 1.2, D: 0.4, G: 2.5, S: 3.5, O: 0.4}

# Planted order effects (multipliers on the next code, given the previous one).
FOLLOW = {
    A: {E: 3.0},           # a question is usually answered by an explanation
    D: {E: 2.5, P: 1.5},   # disagreement leads to explaining or a new idea
    G: {S: 2.0},           # agreement leads to summarising, mostly late
    O: {A: 2.0},           # returning from off-task often starts with a question
}

def pick(t, prev, kind):
    w = dict(phase_weights(t))
    for c, m in BIAS[kind].items():
        w[c] *= m
    if kind == 'drifter' and 18 <= t < 30:
        w[O] *= 4          # planted: drifters go off-task in minutes 18-30
    if prev is not None:
        for c, m in FOLLOW.get(prev, {}).items():
            w[c] *= m
        w[prev] *= 0.35    # fewer immediate repeats
    r, acc = random.random() * sum(w.values()), 0
    for c, v in w.items():
        acc += v
        if r <= acc:
            return c
    return c

def clock(sec):
    sec = int(round(sec)) + 14 * 3600   # session starts at 14:00:00
    return '%02d:%02d:%02d' % (sec // 3600, sec // 60 % 60, sec % 60)

rows, n = [], 0
for kind, count in TYPES.items():
    for _ in range(count):
        n += 1
        lid = 'G%d-%02d' % ((n - 1) // 6 + 1, n)    # group-learner IDs, e.g. G1-03
        t, prev = random.uniform(0, 20), None        # seconds; small staggered start
        while t < 40 * 60 - 5:
            c = pick(t / 60, prev, kind)
            d = random.uniform(*DUR[c])
            end = min(t + d, 40 * 60)
            rows.append((lid, CODES[c], clock(t), clock(end), kind.capitalize()))
            prev = c
            t = end + (random.uniform(3, 25) if random.random() < 0.35 else 0)   # some uncoded gaps

rows.sort(key=lambda r: (r[0], r[2]))
out = sys.argv[1]
groups = '--groups' in sys.argv   # also write the hidden learner type as a group column
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['student_id', 'code', 'start_time', 'end_time'] + (['group'] if groups else []))
    w.writerows([r if groups else r[:4] for r in rows])
print(len(rows), 'rows,', n, 'learners ->', out)
