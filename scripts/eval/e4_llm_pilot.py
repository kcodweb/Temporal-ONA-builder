"""E4: does a language model answer temporal questions better from the integrated view than from separate views?

    node scripts/eval/export_tool_figure.js test-data/pyguru/pyguru-day2.csv test-data/pyguru/eval-llm/day2.svg \
        --order "Read|...|Navigate" --brief test-data/pyguru/eval-llm/brief-day2.txt
    python scripts/eval/e4_llm_pilot.py test-data/pyguru/pyguru-day2.csv test-data/pyguru/eval-llm/brief-day2.txt \
        --out test-data/pyguru/eval-llm/bank-day2 --model claude-sonnet-5-5 --reps 10
    python scripts/eval/e4_llm_pilot.py --combine test-data/pyguru/eval-llm/bank-day1 test-data/pyguru/eval-llm/bank-day2 \
        --out test-data/pyguru/eval-llm --model claude-sonnet-5-5

The question bank is generated from the log (--bank full, the default): the five behaviours with most time, the
busiest slice of every behaviour, what most often follows every behaviour, and when each of the ten strongest links
between different behaviours happens. --bank pilot asks the nine fixed questions of the first pilot. Before any run, an
item is dropped when its answer is not clear in the log (the runner-up within 10% of it), or when a condition whose
data hold the answer prints it too coarsely to tell it from the runner-up. items.md lists every item and why.

The questions go to a model three times per repetition: with the integrated view's data (the tool's own figureBrief,
exactly as the page sends it), with the data behind the separate views (start counts per slice as in raincloud plots,
first-order transition probabilities as in TNA), and with the separate views plus a bar chart of time per behaviour
(the fairer baseline: duration is then answerable from both). Answers come back as JSON constrained to the behaviour
names, the slice labels or "cannot tell", and are scored against values computed from the log.

Providers: anthropic (the default; the Anthropic SDK with ANTHROPIC_API_KEY) and openai (OPENAI_API_KEY; any
/v1/chat/completions endpoint via --base-url). Only aggregated numbers are sent, never rows or learner IDs.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

import numpy as np

from e2_e3_pyguru import ORDER, load, measures, session_length, top_links

SYSTEM = ('You help a teacher read learning-analytics data from a programming lab. You receive the numbers behind one '
          'or more figures, not images. Answer each question only from the data given. If the data do not contain the '
          'information a question needs, answer "cannot tell".')

LEGEND = {
    'integrated': ('The data below are the numbers behind one figure, a temporal network of the lab. Each behaviour is '
                   'a disc whose area shows the time spent in it, with a ring of bars showing when in the session that '
                   'time was spent (one bar per {sl:g}-minute slice). An arrow A → B shows that B started right '
                   'after A in a learner’s sequence of episodes; each arrow also shows in which slices of the '
                   'session this happened.'),
    'separate': ('The data below are the numbers behind two separate figures of the lab, as commonly used in learning '
                 'analytics. (1) Raincloud plots of episode start times: for each behaviour, how many episodes started '
                 'in each {sl:g}-minute slice of the session, with the median and quartiles of the start times. (2) A '
                 'transition network, as in transition network analysis: for each behaviour, the probability that the '
                 'next episode is each behaviour (consecutive episodes pooled over learners), and the share of learners '
                 'who began with each behaviour.'),
}
# The fairer baseline adds what CTAM4SRL's views lacked: total time per behaviour.
LEGEND['separate-duration'] = LEGEND['separate'].replace('two separate', 'three separate') + (
    ' (3) A bar chart of the time learners spent in each behaviour over the whole session (mean minutes per learner).')

# Question kinds: duration (how long), timing (when time was spent), order (what follows what), joint (when a
# transition happens). The separate views answer order, timing only through start counts, duration only with the time
# bars, and joint not at all, so "cannot tell" is the right answer there.
PILOT = [
    ('D1', 'duration', 'Which behaviour did learners spend the most time on, on average?', ('rank', 0)),
    ('D2', 'duration', 'Which behaviour did learners spend the second most time on, on average?', ('rank', 1)),
    ('T1', 'timing', 'In which {sl:g}-minute slice of the session did learners spend the most time on Run code?', ('peak', 'Run code')),
    ('T2', 'timing', 'In which {sl:g}-minute slice of the session did learners spend the most time on Assessment?', ('peak', 'Assessment')),
    ('T3', 'timing', 'In which {sl:g}-minute slice of the session did learners spend the most time on Watch video?', ('peak', 'Watch video')),
    ('O1', 'order', 'Not counting Read followed by Read, which behaviour most often came right after Read?', ('next', 'Read')),
    ('O2', 'order', 'Not counting See errors followed by See errors, which behaviour most often came right after See errors?', ('next', 'See errors')),
    ('J1', 'joint', 'In which {sl:g}-minute slice of the session did learners most often go from Read to Watch video?', ('when', 'Read', 'Watch video')),
    ('J2', 'joint', 'In which {sl:g}-minute slice of the session did learners most often go from See errors to Verify or submit?', ('when', 'See errors', 'Verify or submit')),
]
ORDINAL = ['most', 'second most', 'third most', 'fourth most', 'fifth most']
KINDS = ('duration', 'timing', 'order', 'joint')
MARGIN = 0.9  # an answer is clear when the runner-up is below 90% of it
CANNOT = 'cannot tell'


def bank(m):
    """Every question of each kind that the log supports."""
    items = [('D%d' % (k + 1), 'duration', 'Which behaviour did learners spend the %s time on, on average?' % o,
              ('rank', k)) for k, o in enumerate(ORDINAL)]
    items += [('T%d' % (i + 1), 'timing', 'In which {sl:g}-minute slice of the session did learners spend the most time '
               'on %s?' % b, ('peak', b)) for i, b in enumerate(ORDER)]
    items += [('O%d' % (i + 1), 'order', 'Not counting %s followed by %s, which behaviour most often came right after '
               '%s?' % (b, b, b), ('next', b)) for i, b in enumerate(ORDER)]
    items += [('J%d' % (i + 1), 'joint', 'In which {sl:g}-minute slice of the session did learners most often go from %s '
               'to %s?' % (ORDER[a], ORDER[b]), ('when', ORDER[a], ORDER[b]))
              for i, ((a, b), _) in enumerate(top_links(m, 10, loops=False))]
    return items


def slices(L, sl):
    """Slice labels as the tool prints them (20–30′) and as answer values (20-30)."""
    ns = int(np.ceil(L / sl - 1e-9))
    ends = [(k * sl, min((k + 1) * sl, L)) for k in range(ns)]
    return ['%g–%g′' % e for e in ends], ['%g-%g' % e for e in ends]


def values(rule, m, vals):
    """The log's value of every possible answer to an item."""
    if rule[0] == 'rank':
        return m['mins'], ORDER
    if rule[0] == 'peak':
        return m['prof'][ORDER.index(rule[1])], vals
    if rule[0] == 'next':
        a = ORDER.index(rule[1])
        v = m['links'][a].copy()
        v[a] = -1
        return v, ORDER
    return m['ltime'][ORDER.index(rule[1]), ORDER.index(rule[2])], vals


def ground_truth(items, m, starts, vals):
    """The answer to each item, the runner-up and both values, whether the answer is clear, and for timing items what
    start counts would say."""
    gt = {}
    for iid, _, _, rule in items:
        v, names = values(rule, m, vals)
        k = rule[1] if rule[0] == 'rank' else 0
        o = np.argsort(-v, kind='stable')
        near = [v[o[k + 1]] / v[o[k]] if v[o[k]] > 0 else 1.0] + ([v[o[k]] / v[o[k - 1]]] if k else [])
        gt[iid] = dict(answer=names[o[k]], value=float(v[o[k]]), runner_up=names[o[k + 1]],
                       runner_value=float(v[o[k + 1]]), clear=bool(max(near) < MARGIN))
        if rule[0] == 'peak':
            gt[iid]['start_peak'] = vals[int(np.argmax(starts[ORDER.index(rule[1])]))]
    return gt


def start_counts(seqs, L, sl):
    ns = int(np.ceil(L / sl - 1e-9))
    c = np.zeros((len(ORDER), ns), dtype=int)
    for q in seqs.values():
        for b, s, _ in q:
            c[b, min(int(s // sl), ns - 1)] += 1
    return c


def tna(seqs):
    """First-order transition probabilities (consecutive episodes pooled over learners) and initial probabilities."""
    B = len(ORDER)
    cnt, first = np.zeros((B, B)), np.zeros(B)
    for q in seqs.values():
        first[q[0][0]] += 1
        for (a, _, _), (b, _, _) in zip(q, q[1:]):
            cnt[a, b] += 1
    return cnt / np.maximum(cnt.sum(1, keepdims=True), 1), first / len(seqs)


def separate_views(seqs, L, sl, duration=False):
    """The numbers behind a raincloud plot of start times and a first-order transition network (and, with duration,
    a bar chart of time per behaviour), as text."""
    labels, _ = slices(L, sl)
    starts = start_counts(seqs, L, sl)
    B, n = len(ORDER), len(seqs)
    eps = sum(len(q) for q in seqs.values())
    o = [('FIGURES: three separate views of a coded episode log: raincloud plots of episode start times, a transition network (TNA-style transition probabilities), and a bar chart of time per behaviour.'
          if duration else
          'FIGURES: two separate views of a coded episode log: raincloud plots of episode start times, and a transition network (TNA-style transition probabilities).'),
         'Time units: minutes (′ for points in the session).',
         'Data: %d learners, %d episodes, %d behaviours; session length %g′.' % (n, eps, B, L),
         '', 'RAINCLOUD PLOTS: episode start times per behaviour (all learners together): number of episodes, median and quartiles of the start times, then episodes starting in each %g-min slice.' % sl]
    for b in range(B):
        st = [s for q in seqs.values() for x, s, _ in q if x == b]
        if not st:
            continue
        q1, md, q3 = np.percentile(st, [25, 50, 75])
        o.append('- %s: %d episodes; median start %.0f′, quartiles %.0f′–%.0f′. By slice: %s.' % (
            ORDER[b], len(st), md, q1, q3, ', '.join('%s %d' % (labels[k], starts[b, k]) for k in range(len(labels)))))
    p, first = tna(seqs)
    o += ['', 'TRANSITION NETWORK: probability that the next episode is each behaviour (rows sum to 1; probabilities below 0.01 left out).']
    for a in range(B):
        if p[a].sum():
            o.append('- From %s: %s.' % (ORDER[a], ', '.join('%s %.2f' % (ORDER[b], p[a, b]) for b in np.argsort(-p[a]) if p[a, b] >= 0.005)))
    o.append('Initial probabilities (share of learners whose first episode is each behaviour): %s.' % ', '.join(
        '%s %.2f' % (ORDER[b], first[b]) for b in np.argsort(-first) if first[b]))
    if duration:
        mins = measures(seqs, L, sl)['mins']
        o += ['', 'BAR CHART: time spent in each behaviour over the whole session (mean per learner, and %% of the %g′ session).' % L]
        o += ['- %s: %.1f min (%.0f%%).' % (ORDER[b], mins[b], 100 * mins[b] / L) for b in range(B)]
    return '\n'.join(o)


def read_brief(text):
    """What the integrated view's text prints: minutes and busiest slice per behaviour, and each drawn link's weight and
    weight per slice."""
    beh, links = {}, {}
    for line in text.splitlines():
        b = re.match(r'- (.+?): ([\d.]+) min, .*?peak (\d+)–(\d+)′', line)
        if b:
            beh[b.group(1)] = (float(b.group(2)), '%s-%s' % b.group(3, 4))
            continue
        k = re.match(r'- (.+?) → (.+?): ([\d.]+), .*?By slice: (.*)\.$', line)
        if k:
            to = k.group(1) if k.group(2) == 'itself' else k.group(2)
            links[k.group(1), to] = (float(k.group(3)), {'%s-%s' % (x, y): float(w) for x, y, w in
                                                          re.findall(r'(\d+)–(\d+)′ ([\d.]+)', k.group(4))})
    return beh, links


def single_out(p, ans, k=0):
    """'yes' when the printed values single out the answer as the k-th largest, 'tie' when it shares that place with
    another option, 'mismatch' when they point elsewhere, 'no' when the answer is not printed at all."""
    if ans not in p:
        return 'mismatch' if p else 'no'
    above = sum(1 for x in p.values() if x > p[ans])
    same = sum(1 for x in p.values() if x == p[ans]) - 1
    return 'yes' if above == k and not same else 'tie' if above <= k <= above + same else 'mismatch'


def holds(rule, g, brief, mins, prob, vals):
    """Per condition, whether its data hold the answer: yes, no, proxy (start counts only), or tie / mismatch when they
    hold it but print it too coarsely, or differently from the log."""
    beh, links = brief
    ans = g['answer']
    if rule[0] == 'rank':
        return {'integrated': single_out({b: x[0] for b, x in beh.items()}, ans, rule[1]), 'separate': 'no',
                'separate-duration': single_out({b: float('%.1f' % mins[i]) for i, b in enumerate(ORDER)}, ans, rule[1])}
    if rule[0] == 'peak':
        pk = beh.get(rule[1], (0, None))[1]
        return {'integrated': 'no' if pk is None else 'yes' if pk == ans else 'mismatch', 'separate': 'proxy',
                'separate-duration': 'proxy'}
    if rule[0] == 'next':
        a = ORDER.index(rule[1])
        shown = {b: w for (f, b), (w, _) in links.items() if f == rule[1] and b != rule[1]}
        t = single_out({b: float('%.2f' % prob[a, j]) for j, b in enumerate(ORDER) if j != a and prob[a, j] >= 0.005}, ans)
        return {'integrated': single_out(shown, ans), 'separate': t, 'separate-duration': t}
    w = links.get((rule[1], rule[2]))
    return {'integrated': 'no' if w is None else single_out({s: w[1].get(s, 0.0) for s in vals}, ans),
            'separate': 'no', 'separate-duration': 'no'}


def dropped(g, s):
    """'yes' for an item that is kept, else why it is dropped."""
    if not g['clear']:
        return 'no: runner-up within 10% in the log'
    bad = ['%s in %s' % (v, c) for c, v in s.items() if v in ('tie', 'mismatch')]
    return 'no: printed values %s' % ', '.join(bad) if bad else 'yes'


def schema(items, vals):
    enum = {'behaviour': ORDER + [CANNOT], 'slice': vals + [CANNOT]}
    props = {iid: {'type': 'string', 'enum': enum['behaviour' if rule[0] in ('rank', 'next') else 'slice']}
             for iid, _, _, rule in items}
    return {'type': 'object', 'properties': props, 'required': [i[0] for i in items], 'additionalProperties': False}


def prompt(cond, data, sl, items):
    qs = '\n'.join('%s. %s' % (iid, q.format(sl=sl)) for iid, _, q, _ in items)
    return ('%s\n\n%s\n\nQUESTIONS (if the data above do not contain what a question needs, answer "cannot tell"; '
            'write slices as start-end in minutes, e.g. 20-30):\n%s\n\nReturn a JSON object with one key per question (%s).'
            % (LEGEND[cond].format(sl=sl), data, qs, ', '.join(i[0] for i in items)))


def post(url, body, headers, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(), dict({'content-type': 'application/json'}, **headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError('HTTP %d: %s' % (e.code, e.read()[:300].decode('utf-8', 'replace'))) from None


def ask(a, user, sch, seed):
    """One request; returns (answer text, stop reason, usage notes)."""
    if a.provider == 'openai':
        j = post((a.base_url or 'https://api.openai.com/v1') + '/chat/completions', {
            'model': a.model, 'temperature': a.temperature, 'seed': seed,
            'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answers', 'strict': True, 'schema': sch}}},
            {'authorization': 'Bearer ' + os.environ['OPENAI_API_KEY']}, 600)
        u = j.get('usage', {})
        return j['choices'][0]['message']['content'], j['choices'][0].get('finish_reason'), {'in': u.get('prompt_tokens'), 'out': u.get('completion_tokens')}
    # Claude: the API takes no sampling parameters, so effort is the only setting; no fallback model, so every
    # scored answer comes from the model named here (a refusal counts as a failed run).
    import anthropic
    r = anthropic.Anthropic().messages.create(
        model=a.model, max_tokens=16000, system=SYSTEM, messages=[{'role': 'user', 'content': user}],
        output_config={'effort': a.effort, 'format': {'type': 'json_schema', 'schema': sch}})
    text = next((b.text for b in r.content if b.type == 'text'), '')
    return text, r.stop_reason, {'in': r.usage.input_tokens, 'out': r.usage.output_tokens}


def tally(runs, items, gt, st, t=None):
    """Counts per condition and item, per kind, and split by whether the condition's data hold the answer."""
    t = {} if t is None else t
    for r in runs:
        for iid, kind, _, _ in items:
            ans = (r['answers'] or {}).get(iid)
            k = 'failed' if ans is None else 'abstain' if ans == CANNOT else 'correct' if ans == gt[iid]['answer'] else 'wrong'
            for key in (iid, 'all', kind, 'holds' if st[iid][r['cond']] == 'yes' else 'lacks'):
                x = t.setdefault((r['cond'], key), {'correct': 0, 'abstain': 0, 'wrong': 0, 'failed': 0, 'answers': {}})
                x[k] += 1
                if key == iid:
                    x['answers'][ans] = x['answers'].get(ans, 0) + 1
    return t


def summary(t, conds):
    def pct(c, key, k):
        x = t.get((c, key), {})
        n = sum(x.get(j, 0) for j in ('correct', 'abstain', 'wrong', 'failed'))
        return '%.0f%%' % (100 * x.get(k, 0) / n) if n else '–'

    def count(c, key, ks):
        x = t.get((c, key), {})
        return ' / '.join(str(x.get(k, 0)) for k in ks)

    out = ['| Condition | All correct | Duration | Timing | Order | Joint | Data hold the answer: correct / cannot tell / wrong '
           '| Data lack it: cannot tell / correct / wrong |', '|---|---|---|---|---|---|---|---|']
    for c in conds:
        out.append('| %s | %s | %s | %s |' % (c, ' | '.join(pct(c, k, 'correct') for k in ('all',) + KINDS),
                                             count(c, 'holds', ('correct', 'abstain', 'wrong')),
                                             count(c, 'lacks', ('abstain', 'correct', 'wrong'))))
    fails = {c: t.get((c, 'all'), {}).get('failed', 0) for c in conds}
    if any(fails.values()):
        out.append('\nFailed answers (refusal, cut-off or invalid JSON): %s' % ', '.join('%s %d' % kv for kv in fails.items()))
    return out


def report(runs, items, gt, st, a, conds):
    t = tally(runs, items, gt, st)
    n = {c: sum(1 for r in runs if r['cond'] == c) for c in conds}

    def cell(c, iid):
        x = t.get((c, iid), {})
        wrong = sorted(((k, v) for k, v in x.get('answers', {}).items() if k not in (None, CANNOT, gt[iid]['answer'])), key=lambda kv: -kv[1])
        return '%d / %d / %d' % tuple(x.get(k, 0) for k in ('correct', 'abstain', 'wrong')) + (
            ' (%s)' % ', '.join('%s %d' % kv for kv in wrong) if wrong else '')

    out = ['# E4: %s %s, %s, %s bank (%d items)' % (a.provider, a.model, os.path.basename(a.csv), a.bank, len(items)), '',
           '%s. Settings: %s.' % ('; '.join('%d runs with %s' % (n[c], c) for c in conds),
                                 'effort %s' % a.effort if a.provider == 'anthropic' else 'temperature %g' % a.temperature), '']
    out += summary(t, conds) + ['', 'Per item (correct / cannot tell / wrong; data hold the answer: yes, no or proxy):', '',
                                '| Item | Kind | Answer (runner-up) | %s |' % ' | '.join(conds), '|---|---|---|' + '---|' * len(conds)]
    for iid, kind, _, _ in items:
        g = gt[iid]
        out.append('| %s | %s | %s %.2f (%s %.2f) | %s |' % (iid, kind, g['answer'], g['value'], g['runner_up'], g['runner_value'],
                                                         ' | '.join('%s: %s' % (st[iid][c], cell(c, iid)) for c in conds)))
    return '\n'.join(out)


def item_table(cand, gt, st, kept):
    out = ['| Item | Kind | Question | Answer (runner-up) | Start peak | %s | Kept |' % ' | '.join(LEGEND),
           '|---|---|---|---|---|' + '---|' * len(LEGEND) + '---|']
    for iid, kind, q, _ in cand:
        g = gt[iid]
        out.append('| %s | %s | %s | %s %.2f (%s %.2f) | %s | %s | %s |' % (
            iid, kind, q.format(sl=10), g['answer'], g['value'], g['runner_up'], g['runner_value'], g.get('start_peak', ''),
            ' | '.join(st[iid][c] for c in LEGEND), kept[iid]))
    return '\n'.join(out)


def combine(a):
    tag = '%s-%s' % (a.provider, a.model.replace(':', '_').replace('/', '_'))
    t, n, out = {}, 0, []
    for d in a.combine:
        meta = json.load(open(os.path.join(d, 'items.json'), encoding='utf-8'))
        items = [tuple(i[:3]) + (tuple(i[3]),) for i in meta['items']]
        runs = [json.loads(l) for l in open(os.path.join(d, 'runs-%s.jsonl' % tag), encoding='utf-8')]
        runs = [r for r in runs if r.get('bank') == meta['sig']]
        tally(runs, items, meta['gt'], meta['status'], t)
        n += len(items)
        out.append('%s: %d items, %d runs' % (d, len(items), len(runs)))
    conds = [c for c in LEGEND if (c, 'all') in t]
    rep = '\n'.join(['# E4 pooled: %s %s' % (a.provider, a.model), '', '; '.join(out), ''] + summary(t, conds))
    open(os.path.join(a.out, 'e4-pooled-%s.md' % tag), 'w', encoding='utf-8').write(rep + '\n')
    print(rep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', nargs='?')
    ap.add_argument('brief', nargs='?', help='figureBrief text saved by export_tool_figure.js --brief')
    ap.add_argument('--out', required=True)
    ap.add_argument('--bank', choices=['full', 'pilot'], default='full')
    ap.add_argument('--provider', choices=['anthropic', 'openai'], default='anthropic')
    ap.add_argument('--model', default='claude-sonnet-5-5')
    ap.add_argument('--base-url')
    ap.add_argument('--reps', type=int, default=5)
    ap.add_argument('--temperature', type=float, default=0.2)
    ap.add_argument('--effort', default='medium', help='Claude only')
    ap.add_argument('--slice', type=float, default=10)
    ap.add_argument('--dry-run', action='store_true', help='write the prompts and items.md, send nothing')
    ap.add_argument('--score-only', action='store_true')
    ap.add_argument('--combine', nargs='+', metavar='DIR', help='pool the saved runs of several --out folders')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.combine:
        return combine(a)
    seqs, _ = load(a.csv)
    L, sl = session_length(seqs, a.slice), a.slice
    m, (_, vals) = measures(seqs, L, sl), slices(L, sl)
    brief = open(a.brief, encoding='utf-8').read().strip()
    cand = bank(m) if a.bank == 'full' else PILOT
    gt = ground_truth(cand, m, start_counts(seqs, L, sl), vals)
    st = {i[0]: holds(i[3], gt[i[0]], read_brief(brief), m['mins'], tna(seqs)[0], vals) for i in cand}
    kept = {iid: 'yes' if a.bank == 'pilot' else dropped(gt[iid], st[iid]) for iid, *_ in cand}
    items = [i for i in cand if kept[i[0]] == 'yes']
    sig = ','.join(i[0] for i in items)
    open(os.path.join(a.out, 'items.md'), 'w', encoding='utf-8').write(
        '# Items for %s (%s bank): %d of %d kept\n\n%s\n' % (os.path.basename(a.csv), a.bank, len(items), len(cand), item_table(cand, gt, st, kept)))
    json.dump({'sig': sig, 'items': items, 'gt': {i[0]: gt[i[0]] for i in items}, 'status': {i[0]: st[i[0]] for i in items}},
              open(os.path.join(a.out, 'items.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sch = schema(items, vals)
    data = {'integrated': brief, 'separate': separate_views(seqs, L, sl), 'separate-duration': separate_views(seqs, L, sl, duration=True)}
    for c in LEGEND:
        open(os.path.join(a.out, 'prompt-%s.txt' % c), 'w', encoding='utf-8').write('SYSTEM:\n%s\n\nUSER:\n%s\n' % (SYSTEM, prompt(c, data[c], sl, items)))
    print('%d of %d items kept (%s); prompts and items.md written to %s' % (
        len(items), len(cand), ', '.join('%s %d' % (k, sum(1 for i in items if i[1] == k)) for k in KINDS), a.out))
    if a.dry_run:
        return
    tag = '%s-%s' % (a.provider, a.model.replace(':', '_').replace('/', '_'))
    log = os.path.join(a.out, 'runs-%s.jsonl' % tag)
    # Runs of another question set (the first pilot's lines carry no bank) are kept in the file but not counted here.
    runs = [json.loads(l) for l in open(log, encoding='utf-8')] if os.path.exists(log) else []
    runs = [r for r in runs if r.get('bank', ','.join(i[0] for i in PILOT)) == sig]
    done = {(r['cond'], r['rep']) for r in runs}
    for rep in range(0 if a.score_only else a.reps):
        for c in LEGEND:
            if (c, rep) in done:
                continue
            t0, rec = time.time(), {'cond': c, 'rep': rep, 'provider': a.provider, 'model': a.model, 'bank': sig, 'answers': None}
            # A refusal or a cut-off answer is a result and is kept; a failed request is not, so a rerun retries it.
            try:
                text, stop, use = ask(a, prompt(c, data[c], sl, items), sch, rep)
            except Exception as e:
                print('rep %d %-17s not saved: %s: %s' % (rep, c, type(e).__name__, e), flush=True)
                continue
            rec.update(raw=text, stop=stop, usage=use)
            try:
                rec['answers'] = json.loads(text) if stop not in ('refusal', 'max_tokens', 'length') else None
            except ValueError:
                rec['error'] = 'invalid JSON'
            rec['secs'] = round(time.time() - t0, 1)
            runs.append(rec)
            open(log, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
            x = rec['answers'] or {}
            print('rep %d %-17s %5.0fs %s' % (rep, c, rec['secs'], rec.get('error') or '%d correct, %d cannot tell' % (
                sum(1 for i in items if x.get(i[0]) == gt[i[0]]['answer']), sum(1 for v in x.values() if v == CANNOT))), flush=True)
    rep = report(runs, items, gt, st, a, [c for c in LEGEND if any(r['cond'] == c for r in runs)])
    open(os.path.join(a.out, 'e4-%s.md' % tag), 'w', encoding='utf-8').write(rep + '\n')
    print(rep)


if __name__ == '__main__':
    main()
