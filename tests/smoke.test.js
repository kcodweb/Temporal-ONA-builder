// Smoke tests: load index.html in jsdom, run the real page script, check the three steps
// (upload, check, explore), parsing, rendering, modes, frames, bad input and standalone exports. Run: npm test
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function load(saved) {
  const beforeParse = (win) => { if (saved) Object.entries(saved).forEach(([k, v]) => win.localStorage.setItem(k, JSON.stringify(v))); };
  const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/', beforeParse });
  const w = dom.window;
  const errors = [];
  w.addEventListener('error', (e) => errors.push(e.message));
  w.URL.createObjectURL = () => 'blob:test';
  w.URL.revokeObjectURL = () => {};
  w.scrollTo = () => {};
  return { w, d: w.document, errors };
}

const svgOk = (svg) => {
  const s = svg.innerHTML;
  assert(s.length > 5000, 'svg should have content');
  assert(!s.includes('NaN'), 'svg must not contain NaN');
  assert(!s.includes('Infinity'), 'svg must not contain Infinity');
};

(async () => {
  let passed = 0;
  const t = async (name, fn) => { await fn(); passed++; console.log('ok  ', name); };
  const { w, d, errors } = load();
  await wait(400);
  const svg = d.querySelector('#net');

  const shown = (id) => !d.querySelector('#stage-' + id).hidden;

  await t('first visit opens on the upload step', async () => {
    assert.deepStrictEqual(errors, []);
    assert(shown('start') && !shown('check') && !shown('explore'), 'only the upload step should be visible');
    assert.strictEqual(d.querySelector('.steps [data-go="explore"]').disabled, true);
  });

  await t('sample builds the figure without script errors', async () => {
    d.querySelector('#sample').click();
    await wait(120);
    assert.deepStrictEqual(errors, []);
    assert(shown('explore'), 'explore step expected after loading the sample');
    assert(/episodes from 30 learners, 5 behaviours/.test(d.querySelector('#summary').textContent));
    svgOk(svg);
  });

  await t('whole-session insights are stable for seed 610', async () => {
    const txt = [...svg.querySelectorAll('text')].map((n) => n.textContent).join(' | ');
    assert(txt.includes('Most time: Debugging (24.6 min per learner, 41% of the window).'), txt);
    assert(txt.includes('Coded behaviours cover 52.5 of 60.0 min per learner; 7.5 min uncoded.'), txt);
  });

  await t('timeline arrows are the default and colour mode switches', async () => {
    assert(svg.querySelectorAll('polyline').length > 0, 'timeline segments expected');
    d.querySelector('.arrows [data-e="colour"]').click();
    await wait(80);
    assert.strictEqual(svg.querySelectorAll('polyline').length, 0);
    svgOk(svg);
    d.querySelector('.arrows [data-e="swell"]').click();
    await wait(80);
  });

  await t('each 10-minute frame renders', async () => {
    for (let i = 0; i < 6; i++) {
      d.querySelector(`#frames [data-f="${i}"]`).click();
      await wait(60);
      svgOk(svg);
      assert(svg.querySelector('text').textContent.startsWith(`${i * 10}`));
    }
    d.querySelector('#frames [data-f="-1"]').click();
    await wait(60);
  });

  await t('frame buttons count the episodes that start in each frame', async () => {
    const counts = [...d.querySelectorAll('#frames [data-f] small')].map((n) => +n.textContent);
    assert.strictEqual(counts.length, 6);
    assert.strictEqual(counts.reduce((a, b) => a + b, 0), 799, String(counts));
  });

  await t('settings that re-derive keep the figure valid', async () => {
    for (const [id, val] of [['s-window', '4'], ['s-thick', 'min'], ['s-scope', 'sum'], ['s-slice', '2'], ['s-frame', '15']]) {
      const el = d.querySelector('#' + id);
      el.value = val;
      el.dispatchEvent(new w.Event('change'));
      await wait(60);
      svgOk(svg);
    }
    d.querySelector('#s-merge').checked = true;
    d.querySelector('#s-merge').dispatchEvent(new w.Event('change'));
    await wait(60);
    svgOk(svg);
  });

  await t('clicking a disc highlights its links and clicking again clears it', async () => {
    const disc = () => svg.querySelector('[data-b="2"]');
    disc().dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await wait(60);
    assert(/Highlighted: links of Debugging/.test(svg.textContent));
    assert(svg.querySelectorAll('g[opacity="0.08"]').length > 0, 'unrelated links should be faded');
    assert.strictEqual(disc().getAttribute('aria-pressed'), 'true');
    disc().dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    await wait(60);
    assert(!/Highlighted:/.test(svg.textContent));
    assert.strictEqual(svg.querySelectorAll('g[opacity="0.08"]').length, 0);
  });

  await t('copy caption writes the reporting details', async () => {
    let copied = null;
    Object.defineProperty(w.navigator, 'clipboard', { configurable: true, value: { writeText: (s) => { copied = s; return Promise.resolve(); } } });
    d.querySelector('#copy-cap').click();
    await wait(40);
    assert(/ONA-inspired, descriptive/.test(copied) && /30 learners/.test(copied) && /w = 4/.test(copied), String(copied));
    assert(/back-to-back repeats are merged/.test(copied) && /Coded behaviours cover/.test(copied), copied);
    assert(/Caption copied/.test(d.querySelector('#toast').textContent));
  });

  // A fake fetch that records the request and answers with a server-sent event stream.
  const sseResponse = (body, status = 200) => ({
    ok: status >= 200 && status < 300, status,
    headers: { get: () => (status === 200 ? 'text/event-stream' : 'application/json') },
    body: null, text: () => Promise.resolve(body),
  });
  const anthropicSSE = (txt) => [
    'event: message_start', 'data: {"type":"message_start","message":{"id":"m1"}}', '',
    ...txt.match(/[\s\S]{1,25}/g).map((p) => `event: content_block_delta\ndata: ${JSON.stringify({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: p } })}\n`),
    'event: message_delta', 'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"}}', '',
    'event: message_stop', 'data: {"type":"message_stop"}', ''].join('\n');
  const set = (sel, v) => { const el = d.querySelector(sel); if (el.type === 'checkbox') el.checked = v; else el.value = v; el.dispatchEvent(new w.Event(el.tagName === 'SELECT' || el.type === 'checkbox' ? 'change' : 'input')); el.dispatchEvent(new w.Event('change')); };

  await t('AI reading sends only the figure summary to Claude and renders the answer', async () => {
    d.querySelector('#tab-ai').click();
    assert(!d.querySelector('#pane-ai').hidden && d.querySelector('#pane-set').hidden);
    let req = null;
    w.fetch = (url, init) => { req = { url, init }; return Promise.resolve(sseResponse(anthropicSSE('### What the figure shows\nDebugging fills **41%** of the session.\n- first point\n- <script>alert(1)</script>\n'))); };
    set('#ai-prov', 'anthropic');
    set('#ai-key', 'test-key-not-real');
    set('#ai-remember', true);
    set('#ai-q', 'When does monitoring follow debugging?');
    d.querySelector('#ai-go').click();
    await wait(120);
    assert(req, 'a request should be sent');
    assert.strictEqual(req.url, 'https://api.anthropic.com/v1/messages');
    const h = req.init.headers, body = JSON.parse(req.init.body);
    assert.strictEqual(h['anthropic-dangerous-direct-browser-access'], 'true');
    assert.strictEqual(h['x-api-key'], 'test-key-not-real');
    assert.strictEqual(h['anthropic-version'], '2023-06-01');
    assert.strictEqual(body.model, 'claude-opus-5-5');
    assert.strictEqual(body.stream, true);
    assert(/ONA-inspired/.test(body.system));
    const msg = body.messages[0].content;
    assert(/BEHAVIOURS/.test(msg) && /LINKS/.test(msg) && /Debugging/.test(msg), msg);
    assert(/QUESTION FROM THE RESEARCHER: When does monitoring follow debugging\?/.test(msg));
    assert(!/\bS\d\d\b/.test(msg), 'learner IDs must never be sent');
    const out = d.querySelector('#ai-text');
    assert.strictEqual(out.querySelector('h4').textContent, 'What the figure shows');
    assert.strictEqual(out.querySelector('b').textContent, '41%');
    assert.strictEqual(out.querySelectorAll('script').length, 0, 'model output must not become live HTML');
    assert(/<script>/.test(out.textContent));
    assert(d.querySelector('#ai-stale').hidden, 'fresh reading is not stale');
    assert(JSON.parse(w.localStorage.getItem('tona-ai-key')).anthropic === 'test-key-not-real', 'remembered key is stored');
    d.querySelector('#frames [data-f="0"]').click();
    await wait(80);
    assert(!d.querySelector('#ai-stale').hidden, 'changing the window marks the reading as stale');
    d.querySelector('#frames [data-f="-1"]').click();
    await wait(80);
  });

  await t('AI reading explains a rejected key', async () => {
    w.fetch = () => Promise.resolve(sseResponse('{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}', 401));
    d.querySelector('#ai-go').click();
    await wait(80);
    assert(/did not accept the API key/.test(d.querySelector('#ai-err').textContent), d.querySelector('#ai-err').textContent);
    assert(!d.querySelector('#ai-go').hidden && d.querySelector('#ai-stop').hidden, 'controls reset after an error');
  });

  await t('local models use an OpenAI-compatible endpoint without a key', async () => {
    let req = null;
    w.fetch = (url, init) => { req = { url, init }; return Promise.resolve(sseResponse(['data: {"choices":[{"delta":{"content":"### Cautions\\n"}}]}', 'data: {"choices":[{"delta":{"content":"Few episodes."},"finish_reason":"stop"}]}', 'data: [DONE]', ''].join('\n\n'))); };
    set('#ai-prov', 'local');
    assert(d.querySelector('#ai-key-row').hidden, 'no key field for local models');
    assert(/nothing leaves your device/.test(d.querySelector('#ai-sendto').textContent));
    d.querySelector('#ai-go').click();
    await wait(40);
    assert(/model you have installed/.test(d.querySelector('#ai-err').textContent), 'asks for a model name first');
    set('#ai-model', 'llama3.1');
    d.querySelector('#ai-go').click();
    await wait(80);
    assert.strictEqual(req.url, 'http://localhost:11434/v1/chat/completions');
    assert(!('authorization' in req.init.headers));
    const body = JSON.parse(req.init.body);
    assert.strictEqual(body.model, 'llama3.1');
    assert.deepStrictEqual(body.messages.map((m) => m.role), ['system', 'user']);
    assert(/Few episodes\./.test(d.querySelector('#ai-text').textContent));
    set('#ai-prov', 'anthropic');
    assert.strictEqual(d.querySelector('#ai-key').value, 'test-key-not-real', 'each provider keeps its own key');
  });

  await t('clock rings carry minute numbers and every node names its peak slice', async () => {
    const txt = svg.textContent;
    ['15\u2032', '30\u2032', '45\u2032'].forEach((m) => assert(txt.includes(m), m));
    assert.strictEqual((txt.match(/peak \d/g) || []).length, 10, 'one peak label per behaviour (each drawn twice: halo + text)');
    assert(/Disc area = % of window/.test(txt) && /Clock ring = when/.test(txt), 'size and clock keys expected');
  });

  await t('check step shows columns, preview and behaviours', async () => {
    d.querySelector('#to-check').click();
    assert(shown('check'));
    assert.strictEqual(d.querySelector('#map-learner').value, '0');
    assert.strictEqual(d.querySelector('#map-end').value, '3');
    assert.strictEqual(d.querySelectorAll('#preview tbody tr').length, 8);
    assert.strictEqual(d.querySelectorAll('#chips .chip').length, 5);
    assert(/Every row could be read/.test(d.querySelector('#warns').textContent));
  });

  await t('rejects a log with missing columns', async () => {
    d.querySelector('#data').value = 'name,foo\na,b';
    d.querySelector('#build').click();
    assert(/Missing columns?: /.test(d.querySelector('#status').textContent));
    assert(shown('check'), 'stays on the check step');
  });

  await t('column mapping accepts unusual headers', async () => {
    d.querySelector('#data').value = 'who,what,when\nA,Plan,0\nA,Code,2.5\nB,Plan,0\nB,Test,4';
    d.querySelector('#build').click();
    assert(/Missing columns: learner, behaviour, start/.test(d.querySelector('#status').textContent));
    [['learner', '0'], ['behaviour', '1'], ['start', '2']].forEach(([k, v]) => {
      const el = d.querySelector('#map-' + k);
      el.value = v;
      el.dispatchEvent(new w.Event('change'));
    });
    assert(/Read 4 episodes from 2 learners, 3 behaviours/.test(d.querySelector('#status').textContent));
    d.querySelector('#build').click();
    await wait(80);
    assert(shown('explore'));
    assert.strictEqual(svg.querySelectorAll('[data-b]').length, 3);
    assert(!/NaN|Infinity/.test(svg.innerHTML));
  });

  await t('flags unreadable rows and mm:ss times', async () => {
    d.querySelector('#paste-toggle').click();
    d.querySelector('#data').value = 'learner,behaviour,start,end\nS1,Plan,09:12,09:14\nS1,Code,,\nS1,Test,09:15,09:20';
    d.querySelector('#check-paste').click();
    assert(shown('check'));
    const warns = d.querySelector('#warns').textContent;
    assert(/1 row can\u2019t be read/.test(warns), warns);
    assert(/read as minutes:seconds/.test(warns), warns);
    assert.strictEqual(d.querySelectorAll('#preview tr.bad').length, 1);
  });

  await t('accepts a log without an end column (Q13 style)', async () => {
    d.querySelector('#data').value = 'student_id,activity,start_time\nS1,Reading,09:00:10\nS1,Question,09:02:15\nS1,Hint,09:02:50\nS1,Question,09:03:20';
    d.querySelector('#build').click();
    await wait(80);
    assert(/No end column/.test(d.querySelector('#warns').textContent));
    assert(shown('explore'));
    assert(!svg.innerHTML.includes('NaN'));
  });

  // Logs that are not 60-minute SRL sessions: slices, frames and labels follow the session length.
  const rowsFor = (n, minutes, step, codes, fmt) => {
    const out = ['learner,behaviour,start,end'];
    for (let l = 1; l <= n; l++) for (let t = 0, k = l; t < minutes - 1e-9; t += step, k++) out.push(`L${l},${codes[k % codes.length]},${fmt(t)},${fmt(Math.min(minutes, t + step))}`);
    return out.join('\n');
  };
  const buildText = async (text) => {
    d.querySelector('#data').value = text;
    d.querySelector('#check-paste').click();
    await wait(30);
    d.querySelector('#build').click();
    await wait(100);
  };
  const figText = () => [...svg.querySelectorAll('text')].map((n) => n.textContent).join(' | ');

  await t('a short session gets small slices and no invented uncoded time', async () => {
    ['#s-slice', '#s-frame'].forEach((sel) => { const el = d.querySelector(sel); el.value = '0'; el.dispatchEvent(new w.Event('change')); });
    await buildText(rowsFor(4, 8, 0.5, ['Read', 'Infer', 'Question'], (m) => m));
    assert(shown('explore'));
    assert.strictEqual(d.querySelector('#s-slice').selectedOptions[0].textContent, 'Auto (1 min)');
    assert.strictEqual(d.querySelectorAll('#frames [data-f]').length, 5, 'whole session plus four 2-minute frames');
    assert(svg.querySelector('text').textContent.startsWith('0′ – 8′'));
    assert(/0\.0 min uncoded/.test(figText()), figText());
    svgOk(svg);
  });

  await t('a two-week log is read in days and hours, not thousands of minutes', async () => {
    const iso = (m) => new Date(Date.UTC(2026, 0, 5, 9) + m * 60000).toISOString().replace('.000Z', '');
    await buildText(rowsFor(3, 14 * 1440, 720, ['Video', 'Quiz', 'Forum', 'Idle'], iso));
    assert(shown('explore'));
    const frames = d.querySelectorAll('#frames [data-f]').length;
    assert(frames <= 9, 'frames: ' + frames);
    assert(svg.innerHTML.length < 200000, 'figure stays small: ' + svg.innerHTML.length);
    assert(/^0d – 14d/.test(svg.querySelector('text').textContent), svg.querySelector('text').textContent);
    assert(/ h (per learner|total)/.test(figText()) && /around day /.test(figText()) && /1 bar = 2-day slice/.test(figText()), figText());
    assert(/session 0–14d/.test(d.querySelector('#summary').textContent));
    svgOk(svg);
  });

  await t('time numbers can be seconds or Unix timestamps', async () => {
    d.querySelector('#data').value = rowsFor(2, 1.5, 0.25, ['Look', 'Click'], (m) => Math.round(m * 60)).replace('start,end', 'start_s,end_s');
    d.querySelector('#check-paste').click();
    await wait(30);
    assert(!d.querySelector('#unit-row').hidden && d.querySelector('#map-unit').value === 's', 'seconds guessed from the column name');
    assert(/read as seconds/.test(d.querySelector('#warns').textContent));
    d.querySelector('#build').click();
    await wait(100);
    assert(svg.querySelector('text').textContent.startsWith('0s – 90s'), svg.querySelector('text').textContent);
    d.querySelector('#data').value = rowsFor(2, 120, 10, ['Video', 'Quiz'], (m) => 1767600000 + m * 60);
    d.querySelector('#check-paste').click();
    await wait(30);
    assert.strictEqual(d.querySelector('#map-unit').value, 's', 'Unix seconds detected');
    assert(/Unix timestamps/.test(d.querySelector('#warns').textContent));
    const unit = d.querySelector('#map-unit');
    unit.value = 'ms';
    unit.dispatchEvent(new w.Event('change'));
    assert(/read as milliseconds/.test(d.querySelector('#warns').textContent), 'the user can override the guess');
    unit.value = 's';
    unit.dispatchEvent(new w.Event('change'));
    d.querySelector('#build').click();
    await wait(100);
    assert(/session 0–120′/.test(d.querySelector('#summary').textContent), d.querySelector('#summary').textContent);
  });

  await t('standalone exports trigger browser downloads', async () => {
    assert.strictEqual(d.querySelector('#exp-btns').hidden, false);
    let name = null;
    w.HTMLAnchorElement.prototype.click = function () { name = this.download; };
    d.querySelector('#dl-svg').click();
    await wait(80);
    assert(/^temporal-ona-.*\.svg$/.test(name), String(name));
  });

  await t('the downloaded tool is a working copy of the page', async () => {
    let name = null, blob = null;
    w.HTMLAnchorElement.prototype.click = function () { name = this.download; };
    w.URL.createObjectURL = (b) => { blob = b; return 'blob:test'; };
    d.querySelector('#dl-tool').click();
    await wait(80);
    assert.strictEqual(name, 'temporal-ona-builder.html');
    const text = await new Promise((res) => { const fr = new w.FileReader(); fr.onload = () => res(fr.result); fr.readAsText(blob); });
    assert(/^<!doctype html>/.test(text) && text.includes('Temporal ONA builder') && text.includes('function figureBrief'), 'full page expected');
    assert(text.includes('Build a network to see it here.'), 'the copy is the page as served, before any figure is drawn');
    const copy = new JSDOM(text, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'file:///C:/Users/me/temporal-ona-builder.html', beforeParse: (cw) => { cw.scrollTo = () => {}; } });
    const errs = [];
    copy.window.addEventListener('error', (e) => errs.push(e.message));
    await wait(200);
    copy.window.document.querySelector('#sample').click();
    await wait(150);
    assert.deepStrictEqual(errs, []);
    assert(!copy.window.document.querySelector('#stage-explore').hidden, 'the copy builds the sample figure');
    copy.window.close();
  });

  await t('clear saved data returns to the upload step', async () => {
    d.querySelector('#clear').click();
    await wait(80);
    assert(/Saved data cleared/.test(d.querySelector('#toast').textContent));
    assert(shown('start'));
    assert.strictEqual(w.localStorage.getItem('tona-data'), null);
    assert.strictEqual(w.localStorage.getItem('tona-ai-key'), null, 'a remembered AI key is cleared too');
    assert.strictEqual(d.querySelector('#ai-key').value, '');
  });

  assert.deepStrictEqual(errors, []);

  await t('returning visitor lands on their saved figure', async () => {
    const r = load({ 'tona-data': 'pupil,act,t\nA,Plan,0\nA,Code,3\nA,Plan,7', 'tona-name': 'lab.csv', 'tona-map': { learner: 'pupil', behaviour: 'act', start: 't' } });
    await wait(200);
    assert.deepStrictEqual(r.errors, []);
    assert(!r.d.querySelector('#stage-explore').hidden, 'explore step expected');
    assert.strictEqual(r.d.querySelector('#ds-name').textContent, 'lab.csv');
    assert(/3 episodes from 1 learner, 2 behaviours/.test(r.d.querySelector('#summary').textContent));
  });

  console.log(`\n${passed} tests passed`);
  process.exit(0);
})().catch((e) => { console.error('FAIL', e.message); process.exit(1); });
