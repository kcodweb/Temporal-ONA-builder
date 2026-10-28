"""Educator study: a language model reads each figure as an image and writes inferences for teachers to rate.

    python scripts/eval/e5_educator_inferences.py --out test-data/educator-study --dry-run
    python scripts/eval/e5_educator_inferences.py --out test-data/educator-study --reps 3

Each dataset's figure (a PNG exported from the tool) goes to the model as an image, with a short description of the
activity and its codes and nothing else: none of the numbers behind the figure. The model returns five inferences for a
teacher, each linking what learners do with when and what follows, what it may mean and what the teacher could do
and when, with the evidence it read, another reading of it and its confidence, plus one caution for the figure. Run 1 of each figure is the set educators rate, fixed before any output is read; the
other runs show how stable the inferences are.

Needs ANTHROPIC_API_KEY. The images show aggregates only (no learner IDs), but the PyGuru figure comes from student
data, so outputs stay under test-data/ (git-ignored).
"""
import argparse
import base64
import io
import json
import os
import time

DATASETS = {
    'pyguru': dict(
        image='pyguru.png', title='PyGuru: a Python programming lab',
        context=('A Python programming lab in PyGuru, a learning environment with an e-book reader (with highlighting '
                 'and notes), a video player, a code editor, quizzes and assessment questions. 29 students; sessions '
                 'up to 114 minutes. Each "learner" in the figure is one student. Codes: Read (reading the e-book); '
                 'Highlight or annotate; Review notes (viewing their own highlights or notes); Run code; See errors '
                 '(viewing error messages after running code); Watch video; Quiz; Assessment; Verify or submit '
                 '(checking or submitting assessment answers); Navigate (browsing topics or checking messages). An '
                 'episode lasts until the student\'s next action, at most 30 minutes.')),
    'justhink': dict(
        image='justhink.png', title='JUSThink: children solving a puzzle with a robot',
        context=('39 teams of two children (aged 9 to 12) solved a puzzle together with a robot: building a railway '
                 'network that connects all the gold mines on a map at the lowest cost. Each "learner" in the figure '
                 'is one team of two. Sessions last up to about 36 minutes. Codes: Add track; Remove track; Review '
                 'past solutions (comparing or reloading earlier attempts); Ready to submit (one child signals that '
                 'the solution is ready); Submit blocked (pressing submit before the network connects every mine); '
                 'Team submits (both children submit a solution); Ask for help (pressing the help button); Robot '
                 'talks (the robot gives feedback or prompts). An episode lasts until the team\'s next event, at '
                 'most 60 seconds.')),
    'coauthor': dict(
        image='coauthor.png', title='CoAuthor: writing with AI suggestions',
        context=('Adults wrote short stories or argumentative essays in an editor that offers text suggestions from '
                 'an AI language model (GPT-3) on request. 1,435 writing sessions by about 60 writers; the figure '
                 'shows the first 15 minutes, by which 95% of sessions had ended. Each "learner" in the figure is one '
                 'writing session. Codes: Compose (typing their own text); Delete; Ask AI (requesting a suggestion, '
                 'waiting for it and reading it); Browse suggestions; Accept suggestion; Dismiss suggestion; Revise '
                 'AI text (editing text that came from the AI); Revise own text; Move cursor. An episode lasts until '
                 'the next different action, at most 60 seconds.')),
}

PROMPT_VERSION = 'v2'  # v1 asked for pattern, meaning and action as separate fields and got descriptions, not inferences
# The prompt exactly as run; the tool was then called the Temporal ONA builder.
SYSTEM = '\n'.join([
    'You help teachers draw inferences about learning from a learning-analytics figure. You see one image: a temporal '
    'ordered network made with the Temporal ONA builder from a coded log of what learners did during a session, with a '
    'short description of the activity.',
    '',
    'An inference connects what learners do with when they do it and what they do next, says what that suggests about '
    'their learning (a difficulty, a strategy, a habit), and ends with what the teacher could do and when. For example, '
    'for a maths homework session (not one of the activities you will see): "Students who open a hint in the first '
    '15 minutes tend to move straight on to the next problem rather than retry the one they asked about, which may mean '
    'they read hints as answers, so the teacher could ask them to retry each hinted problem during that first quarter '
    'of an hour." A description of one number ("Practice takes 30% of the time") is evidence, not an inference.',
    '',
    'Look for inferences about questions like these: Where do learners seem to struggle, and what do they do next? When '
    'in the session do they switch between activities, and does the switching look productive? When do they seek or '
    'get help, and what follows? What could the teacher do, and at what point in the session?',
    '',
    'How to read the figure:',
    '- Each behaviour is a disc; its area is the share of the session spent in it (mean per learner), printed beside it '
    'as minutes and %, with the busiest time slice ("peak").',
    '- The ring of bars around each disc shows when that time was spent: one bar per time slice, starting at the top '
    'and running clockwise like a clock; a longer bar means more of that slice was spent in the behaviour.',
    '- An arrow A → B means B started right after A in a learner\'s sequence; thicker or darker arrows are more '
    'frequent. Loops are a behaviour followed by itself. Only the strongest links are drawn; the footer says how many '
    'are hidden.',
    '- Along each arrow, swellings show when in the session that transition happened, coloured from violet (early) to '
    'amber (late) as in the colour bar at the top right.',
    '- The footer states the behaviour with most time, the strongest link and how much of the session is coded.',
    '',
    'Rules:',
    '- Write each inference as one or two plain sentences: which learners or which part of the session, what they tend '
    'to do and what follows, what it may mean for their learning, and what the teacher could do and when.',
    '- Every inference must link at least two of: how long, when in the session, what follows what, and when a switch '
    'happens. Do not give an inference that only restates time spent or one number.',
    '- Base each inference on what the figure shows, and list the evidence: the discs, rings, arrows or swellings you '
    'read and the numbers the figure prints. A missing arrow means that link is weaker than the ones drawn, not absent.',
    '- Use hedged words ("tend to", "may", "on average"). Do not claim causes, effects on learning, statistical '
    'significance or predictions about individual learners. Values are averages and can hide very different learners.',
    '- Put cautions about the data (uncoded time, hidden links, how episodes were cut) in the caution field, not in the '
    'inferences.',
    '- Use British spelling and the plain words a teacher would use.'])

FACETS = ['time spent', 'when in the session', 'what follows what', 'when a transition happens']
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['inferences', 'caution'], 'properties': {
    'inferences': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False,
        'required': ['inference', 'evidence', 'facets', 'alternative', 'confidence'],
        'properties': {
            'inference': {'type': 'string', 'description': 'One or two sentences: who or when, what they tend to do and '
                          'what follows, what it may mean, what the teacher could do and when'},
            'evidence': {'type': 'string', 'description': 'The figure parts read and the numbers it prints'},
            'facets': {'type': 'array', 'items': {'type': 'string', 'enum': FACETS}},
            'alternative': {'type': 'string', 'description': 'Another plausible reading of the same evidence'},
            'confidence': {'type': 'string', 'enum': ['low', 'medium', 'high']}}}},
    'caution': {'type': 'string', 'description': 'What the teacher should keep in mind about this figure as a whole'}}}


def prompt(ds):
    return ('About the data: %s\n\nGive exactly five inferences a teacher could act on, most useful first.' % ds['context'])


def image_b64(path, longest=1568):
    """The figure as base64 PNG, scaled so its longer side is at most 1568 px (the size the API reads at)."""
    from PIL import Image
    im = Image.open(path).convert('RGB')
    s = longest / max(im.size)
    if s < 1:
        im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return base64.b64encode(buf.getvalue()).decode(), im.size


def ask(a, ds, img):
    import anthropic
    r = anthropic.Anthropic().messages.create(
        model=a.model, max_tokens=16000, system=SYSTEM,
        messages=[{'role': 'user', 'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': img}},
            {'type': 'text', 'text': prompt(ds)}]}],
        output_config={'effort': a.effort, 'format': {'type': 'json_schema', 'schema': SCHEMA}})
    text = next((b.text for b in r.content if b.type == 'text'), '')
    return text, r.stop_reason, {'in': r.usage.input_tokens, 'out': r.usage.output_tokens}


def readable(runs):
    out = ['# Inferences from the figure images (%s, prompt %s)' % (', '.join(sorted({r['model'] for r in runs})), PROMPT_VERSION), '']
    for r in sorted(runs, key=lambda r: (list(DATASETS).index(r['dataset']), r['rep'])):
        out += ['## %s, run %d%s' % (DATASETS[r['dataset']]['title'], r['rep'] + 1, ' (rated by educators)' if r['rep'] == 0 else ''), '']
        for k, x in enumerate((r['answers'] or {}).get('inferences', []), 1):
            out += ['%d. **%s**' % (k, x['inference']), '   - Evidence: %s' % x['evidence'],
                    '   - Or: %s' % x['alternative'],
                    '   - Facets: %s; confidence %s' % (', '.join(x['facets']), x['confidence']), '']
        if r['answers']:
            out += ['Caution: %s' % r['answers'].get('caution', ''), '']
        else:
            out += ['(no answer: %s)' % (r.get('error') or r.get('stop')), '']
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='folder with the figure PNGs; outputs are written here too')
    ap.add_argument('--model', default='claude-sonnet-5-5')
    ap.add_argument('--effort', default='high')
    ap.add_argument('--reps', type=int, default=3)
    ap.add_argument('--only', nargs='*', choices=list(DATASETS))
    ap.add_argument('--dry-run', action='store_true', help='write the prompts and check the images, send nothing')
    a = ap.parse_args()
    names = a.only or list(DATASETS)
    imgs = {}
    for n in names:
        imgs[n], size = image_b64(os.path.join(a.out, DATASETS[n]['image']))
        open(os.path.join(a.out, 'prompt-%s.txt' % n), 'w', encoding='utf-8').write(
            'SYSTEM:\n%s\n\nUSER: [figure image %s, %d x %d px]\n%s\n' % (SYSTEM, DATASETS[n]['image'], *size, prompt(DATASETS[n])))
        print('%-9s image %d x %d px (about %d input tokens), prompt-%s.txt written' % (n, *size, size[0] * size[1] / 750, n))
    if a.dry_run:
        return
    log = os.path.join(a.out, 'runs-%s-%s.jsonl' % (a.model, PROMPT_VERSION))
    runs = [json.loads(l) for l in open(log, encoding='utf-8')] if os.path.exists(log) else []
    done = {(r['dataset'], r['rep']) for r in runs}
    for rep in range(a.reps):
        for n in names:
            if (n, rep) in done:
                continue
            t0, rec = time.time(), {'dataset': n, 'rep': rep, 'model': a.model, 'effort': a.effort, 'prompt': PROMPT_VERSION, 'answers': None,
                                    'date': time.strftime('%Y-%m-%d')}
            # A refusal or a cut-off answer is a result and is kept; a failed request is not, so a rerun retries it.
            try:
                text, stop, use = ask(a, DATASETS[n], imgs[n])
            except Exception as e:
                print('%s run %d not saved: %s: %s' % (n, rep + 1, type(e).__name__, e), flush=True)
                continue
            rec.update(raw=text, stop=stop, usage=use, secs=round(time.time() - t0, 1))
            try:
                rec['answers'] = json.loads(text) if stop not in ('refusal', 'max_tokens') else None
            except ValueError:
                rec['error'] = 'invalid JSON'
            runs.append(rec)
            open(log, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
            k = len((rec['answers'] or {}).get('inferences', []))
            print('%-9s run %d %5.0fs %s' % (n, rep + 1, rec['secs'], rec.get('error') or '%d inferences' % k), flush=True)
    md = os.path.join(a.out, 'inferences-%s-%s.md' % (a.model, PROMPT_VERSION))
    open(md, 'w', encoding='utf-8').write(readable(runs) + '\n')
    print('wrote', md)


if __name__ == '__main__':
    main()
