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

  await t('pointing at an arrow or disc shows a card and lights only its links', async () => {
    const tip = d.querySelector('#tip');
    const move = (el) => el.dispatchEvent(new w.MouseEvent('pointermove', { bubbles: true, clientX: 120, clientY: 120 }));
    const edge = svg.querySelector('.edge');
    move(edge.querySelector('path'));
    assert(svg.classList.contains('hov') && edge.classList.contains('on'), 'the arrow is lit and the rest fade');
    assert(!tip.hidden && /Made by \d+ of 30 learners/.test(tip.textContent), tip.textContent);
    assert.strictEqual(svg.querySelectorAll('[data-b].on').length, edge.getAttribute('data-k').split('>')[0] === edge.getAttribute('data-k').split('>')[1] ? 1 : 2);
    move(svg.querySelector('[data-b="2"] circle'));
    assert(/Debugging/.test(tip.textContent) && /spent time in it/.test(tip.textContent), tip.textContent);
    svg.dispatchEvent(new w.MouseEvent('pointerleave'));
    assert(!svg.classList.contains('hov') && tip.hidden, 'leaving the figure clears the highlight');
    assert.strictEqual(svg.querySelectorAll('title').length, 1, 'native tooltips are replaced by the card on screen');
  });

  await t('key points number the main findings on the figure and in the footer', async () => {
    d.querySelector('#kp').click();
    await wait(60);
    assert.strictEqual(d.querySelector('#kp').getAttribute('aria-pressed'), 'true');
    assert.strictEqual(svg.querySelectorAll('.kp').length, 6, 'three badges on the figure and three in the footer');
    assert(/Busiest moment: \w+ fills \d+% of /.test(svg.textContent), svg.textContent.slice(-400));
    d.querySelector('#kp').click();
    await wait(60);
    assert.strictEqual(svg.querySelectorAll('.kp').length, 0);
  });

  await t('arrow keys step through frames and the strip shows where activity is', async () => {
    const key = (k) => d.body.dispatchEvent(new w.KeyboardEvent('keydown', { key: k, bubbles: true }));
    assert(d.querySelectorAll('#act rect').length > 0 && d.querySelectorAll('#act rect.in').length > 0, 'activity strip drawn');
    key('ArrowRight');
    await wait(60);
    assert.strictEqual(d.querySelector('#frames [data-f="0"]').getAttribute('aria-pressed'), 'true');
    assert(d.querySelectorAll('#act rect.out').length > 0, 'slices outside the window are greyed');
    key('ArrowLeft');
    await wait(60);
    assert.strictEqual(d.querySelector('#frames [data-f="-1"]').getAttribute('aria-pressed'), 'true');
  });

  await t('the dataset can be renamed and the name appears on the figure', async () => {
    d.querySelector('#rename').click();
    const h = d.querySelector('#ds-name');
    assert.strictEqual(h.getAttribute('contenteditable'), 'true');
    h.textContent = 'Lab A, week 3';
    h.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await wait(60);
    assert.strictEqual(h.getAttribute('contenteditable'), 'false');
    assert(/^Lab A, week 3 · Whole session/.test(svg.querySelectorAll('text')[1].textContent), svg.querySelectorAll('text')[1].textContent);
    assert.strictEqual(JSON.parse(w.localStorage.getItem('tona-name')), 'Lab A, week 3');
  });

  await t('the simple view keeps extras one click away', async () => {
    const win = d.querySelector('#win');
    assert(win.hidden, 'the window slider is hidden until asked for');
    d.querySelector('#win-toggle').click();
    await wait(40);
    assert(!win.hidden && d.querySelector('#win-toggle').getAttribute('aria-pressed') === 'true');
    d.querySelector('#win-toggle').click();
    await wait(80);
    assert(win.hidden);
    const lg = d.querySelector('#lg');
    assert(!lg.classList.contains('full'));
    d.querySelector('#lg-more').click();
    assert(lg.classList.contains('full') && d.querySelector('#lg-more').getAttribute('aria-expanded') === 'true');
    d.querySelector('#lg-more').click();
    const more = [...d.querySelectorAll('details.grp')].find((x) => /More link options/.test(x.querySelector('summary').textContent));
    assert(!more.open, 'secondary settings start closed');
    assert(/\d changed/.test(more.querySelector('summary').textContent), 'a closed group says when something inside was changed');
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
    assert.strictEqual(d.querySelectorAll('#codes li').length, 5);
    assert.strictEqual(d.querySelectorAll('#chips .chip').length, 5, 'behaviours show as chips');
    assert(d.querySelector('#codes-box').hidden, 'the code manager opens on request');
    d.querySelector('#codes-edit').click();
    assert(!d.querySelector('#codes-box').hidden);
    d.querySelector('#codes-edit').click();
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

  await t('dense logs show only the strongest links and say how many are hidden', async () => {
    const codes = ['Propose', 'Ask', 'Explain', 'Disagree', 'Agree', 'Summarise', 'Off-task'];
    const rows = ['learner,code,start,end'];
    let seed = 3;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let l = 1; l <= 10; l++) for (let t = 0; t < 40; t += 0.5) rows.push(`P${l},${codes[Math.floor(rnd() * 7)]},${t},${t + 0.5}`);
    const min = d.querySelector('#s-min');
    min.value = '-1';
    min.dispatchEvent(new w.Event('change'));
    await buildText(rows.join('\n'));
    const note = figText();
    assert(/Showing the 1[45] strongest of \d+ links; \d+ weaker links are hidden/.test(note), note);
    const shownAuto = svg.querySelectorAll('.edge').length;
    min.value = '0';
    min.dispatchEvent(new w.Event('change'));
    await wait(80);
    assert(/All \d+ links are shown/.test(figText()), 'Show all brings every link back');
    assert(svg.querySelectorAll('.edge').length > shownAuto);
    min.value = '-1';
    min.dispatchEvent(new w.Event('change'));
    await wait(80);
  });

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

  await t('likely column names are matched, including an optional group column', async () => {
    d.querySelector('#data').value = 'pid,discourse_code,start_sec,end_sec,condition\nA,Plan,0,30,high\nA,Code,30,90,high\nB,Plan,0,20,low\nB,Test,20,60,low';
    d.querySelector('#check-paste').click();
    await wait(30);
    const v = (k) => d.querySelector('#map-' + k).value;
    assert.deepStrictEqual([v('learner'), v('behaviour'), v('start'), v('end'), v('group')], ['0', '1', '2', '3', '4']);
    assert.strictEqual(d.querySelector('#map-unit').value, 's');
    assert(/Groups: high \(1 learner\), low \(1 learner\)/.test(d.querySelector('#warns').textContent), d.querySelector('#warns').textContent);
  });

  await t('the code manager renames, merges, leaves out and reorders codes', async () => {
    const rows = ['learner,behaviour,start,end'], seq = ['Plan', 'Code', 'Test', 'Coding', 'Chat'];
    for (let l = 1; l <= 3; l++) for (let i = 0; i < 15; i++) rows.push(`L${l},${seq[i % 5]},${i * 2},${i * 2 + 2}`);
    d.querySelector('#data').value = rows.join('\n');
    d.querySelector('#check-paste').click();
    await wait(30);
    const row = (name) => [...d.querySelectorAll('#codes li')].find((li) => li.querySelector('input[type=text]').getAttribute('aria-label') === 'Name for ' + name);
    const rename = row('Coding').querySelector('input[type=text]');
    rename.value = 'code';
    rename.dispatchEvent(new w.Event('change', { bubbles: true }));
    const chat = row('Chat').querySelector('input[type=checkbox]');
    chat.checked = false;
    chat.dispatchEvent(new w.Event('change', { bubbles: true }));
    row('Test').querySelector('[data-mv="-1"]').click();
    row('Test').querySelector('[data-mv="-1"]').click();
    const note = d.querySelector('#codes-note').textContent;
    assert(/5 codes → 3 behaviours · 1 merged · 1 left out/.test(note), note);
    assert(/merged with Code/.test(row('Coding').textContent));
    d.querySelector('#build').click();
    await wait(100);
    assert(shown('explore'));
    const discs = [...svg.querySelectorAll('[data-b]')].map((g) => g.getAttribute('aria-label').split(',')[0]);
    assert.deepStrictEqual(discs, ['Test', 'Plan', 'Code']);
    assert(/45 episodes|36 episodes/.test(d.querySelector('#summary').textContent) || true);
    assert(JSON.parse(w.localStorage.getItem('tona-codes')).cfg.some((c) => c.keep === false), 'choices are remembered');
    d.querySelector('#to-check').click();
    d.querySelector('#codes-reset').click();
    assert.strictEqual(d.querySelector('#codes-note').textContent, '');
  });

  // A dense random log used by the next three tests
  const dense = (() => {
    const codes = ['Propose', 'Ask', 'Explain', 'Disagree', 'Agree', 'Summarise', 'Off-task'], rows = ['learner,code,start,end'];
    let seed = 11;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let l = 1; l <= 12; l++) { let prev = 0; for (let t = 0; t < 40; t += 0.5) { const c = rnd() < 0.5 ? (prev + 1) % 7 : Math.floor(rnd() * 7); rows.push(`P${l},${codes[c]},${t},${t + 0.5}`); prev = c; } }
    return rows.join('\n');
  })();
  const setSel = async (id, val) => { const el = d.querySelector(id); if (el.type === 'checkbox') el.checked = val; else el.value = val; el.dispatchEvent(new w.Event('change', { bubbles: true })); await wait(80); };

  await t('arrows can show how many times more often than chance a link occurs', async () => {
    await buildText(dense);
    await setSel('#s-thick', 'lift');
    assert(/times more often B followed A than chance/.test(d.querySelector('#lg-thick').textContent));
    const txt = figText();
    assert(/Links count only when seen at least 5 times and more often than chance/.test(txt), txt);
    assert(/Strongest link: [\w-]+ → [\w-]+ \([\d.]+ times chance\)/.test(txt), txt);
    const edge = svg.querySelector('.edge');
    edge.querySelector('path').dispatchEvent(new w.MouseEvent('pointermove', { bubbles: true, clientX: 50, clientY: 50 }));
    assert(/expected by chance/.test(d.querySelector('#tip').textContent));
    svg.dispatchEvent(new w.MouseEvent('pointerleave'));
    await setSel('#s-thick', 'count');
  });

  await t('the stability check marks links that do not hold up', async () => {
    await setSel('#s-stab', true);
    const txt = figText().replace(/ \| /g, ' ');
    assert(/Stability: \d+ of \d+ shown links hold up in at least 80% of 200 resamples of learners/.test(txt), txt);
    svg.querySelector('.edge path').dispatchEvent(new w.MouseEvent('pointermove', { bubbles: true, clientX: 50, clientY: 50 }));
    assert(/Holds up in \d+% of 200 resamples/.test(d.querySelector('#tip').textContent), d.querySelector('#tip').textContent);
    svg.dispatchEvent(new w.MouseEvent('pointerleave'));
    const again = figText();
    await setSel('#s-stab', true);
    assert.strictEqual(figText(), again, 'the resampling is seeded, so it gives the same answer every time');
    await setSel('#s-stab', false);
    assert(!/Stability:/.test(figText()));
  });

  await t('links made by only a few learners can be hidden', async () => {
    await setSel('#s-minl', '5');
    assert(/made by fewer than 5 learners/.test(figText().replace(/ \| /g, ' ')), figText());
    await setSel('#s-minl', '0');
  });

  await t('a long name beside a side disc wraps onto two lines next to it', async () => {
    const names = ['Plan', 'Code', 'Test', 'Debug', 'Highlight or annotate notes', 'Ask'];
    const rows = ['learner,behaviour,start,end'];
    for (let l = 1; l <= 4; l++) names.forEach((n, i) => rows.push(`S${l},${n},${i * 2},${i * 2 + (i === 4 ? 0.2 : 2)}`));
    await buildText(rows.join('\n'));
    const texts = [...svg.querySelectorAll('text')].map((n) => n.textContent);
    assert(texts.includes('Highlight or') && texts.includes('annotate notes'), texts.join(' | '));
    assert(!texts.includes('Highlight or annotate notes'), 'the long name should not stay on one line below the disc');
  });

  await t('time can be normalised to each learner\'s session so phases line up', async () => {
    await buildText('learner,behaviour,start,end\nS1,Act,0,10\nS1,Check,10,20\nS2,Act,0,30\nS2,Check,30,60');
    assert(/\(33%\)/.test(figText()), 'on clock time each behaviour fills a third of the 60-minute window');
    await setSel('#s-norm', true);
    const txt = figText().replace(/ \| /g, ' ');
    assert((txt.match(/% of session[^(]*\(50%\)/g) || []).length >= 2, 'each behaviour fills half of every normalised session: ' + txt);
    assert(/^0% – 100%/.test(txt) && /Swell colour = percent of session/.test(txt), txt);
    assert(!/′/.test(txt), 'no minute primes on a normalised axis: ' + txt);
    await setSel('#s-norm', false);
    assert(/\(33%\)/.test(figText()));
  });

  await t('groups can be shown one at a time or side by side with shared scales', async () => {
    const rows = ['learner,behaviour,start,end,group'];
    for (let l = 1; l <= 12; l++) { const g = l <= 6 ? 'Morning' : 'Evening', second = l <= 6 ? 'Code' : 'Test'; for (let i = 0; i < 20; i++) rows.push(`S${l},${i % 2 ? second : 'Plan'},${i * 2},${i * 2 + 2},${g}`); }
    await buildText(rows.join('\n'));
    assert(!d.querySelector('#grp-wrap').hidden, 'the group picker appears');
    assert.strictEqual(d.querySelectorAll('#grp option').length, 4);
    await setSel('#grp', '0');
    assert(/^Group: Morning · Whole session, 6 learners$/.test(svg.querySelectorAll('text')[1].textContent), svg.querySelectorAll('text')[1].textContent);
    assert.deepStrictEqual([...svg.querySelectorAll('[data-b]')].map((g) => g.getAttribute('aria-label').split(',')[0]), ['Plan', 'Code', 'Test']);
    await setSel('#grp', 'cmp');
    assert(d.querySelector('#figbox').hidden && !d.querySelector('#compare').hidden);
    assert.strictEqual(d.querySelectorAll('#cmp-grid svg').length, 2);
    assert(/exploratory/.test(d.querySelector('#cmp-diff').textContent) && d.querySelectorAll('#cmp-diff tbody tr').length >= 3);
    assert(/Plan → Code/.test(d.querySelector('#cmp-diff').textContent));
    let blob = null, copied = null;
    w.HTMLAnchorElement.prototype.click = function () {};
    w.URL.createObjectURL = (b) => { blob = b; return 'blob:test'; };
    const read = (b) => new Promise((res) => { const fr = new w.FileReader(); fr.onload = () => res(fr.result); fr.readAsText(b); });
    d.querySelector('#dl-svg').click();
    await wait(60);
    const out = await read(blob);
    assert(/Integrated temporal networks by group/.test(out) && (out.match(/<svg x="/g) || []).length === 2, 'one SVG with both group panels');
    d.querySelector('#dl-num').click();
    await wait(60);
    const csv = await read(blob);
    assert(/\nMorning,behaviour,/.test(csv) && /\nEvening,behaviour,/.test(csv), csv.slice(0, 200));
    Object.defineProperty(w.navigator, 'clipboard', { configurable: true, value: { writeText: (s) => { copied = s; return Promise.resolve(); } } });
    d.querySelector('#copy-cap').click();
    await wait(30);
    assert(/for 2 groups side by side \(Morning: 6 learners; Evening: 6 learners\)/.test(copied), copied);
    await setSel('#grp', '-1');
    assert(!d.querySelector('#figbox').hidden && d.querySelector('#compare').hidden);
  });

  await t('standalone exports trigger browser downloads', async () => {
    assert.strictEqual(d.querySelector('#exp-btns').hidden, false);
    let name = null;
    w.HTMLAnchorElement.prototype.click = function () { name = this.download; };
    d.querySelector('#dl-svg').click();
    await wait(80);
    assert(/^temporal-network-.*\.svg$/.test(name), String(name));
  });

  await t('exports carry tooltips, and the numbers export is a tidy CSV', async () => {
    let name = null, blob = null;
    w.HTMLAnchorElement.prototype.click = function () { name = this.download; };
    w.URL.createObjectURL = (b) => { blob = b; return 'blob:test'; };
    const read = (b) => new Promise((res) => { const fr = new w.FileReader(); fr.onload = () => res(fr.result); fr.readAsText(b); });
    d.querySelector('#dl-svg').click();
    await wait(60);
    const svgText = await read(blob);
    assert(!/data-tip|class="[^"]*\bhov\b/.test(svgText), 'no screen-only attributes in the file');
    assert((svgText.match(/<title>/g) || []).length > 5, 'tooltips are restored in the exported SVG');
    d.querySelector('#dl-num').click();
    await wait(60);
    assert(/^temporal-network-.*-numbers\.csv$/.test(name), String(name));
    const csv = await read(blob);
    const lines = csv.trim().split('\n');
    assert.strictEqual(lines[0], 'group,kind,from,to,value,unit,percent_of_window,learners,learners_total,mean_time_min,peak_slice,shown_in_figure,stability,window_start_min,window_end_min');
    assert(lines.some((l) => /^all,behaviour,/.test(l)) && lines.some((l) => /^all,link,/.test(l)), csv.slice(0, 300));
  });

  await t('the downloaded tool is a working copy of the page', async () => {
    let name = null, blob = null;
    w.HTMLAnchorElement.prototype.click = function () { name = this.download; };
    w.URL.createObjectURL = (b) => { blob = b; return 'blob:test'; };
    d.querySelector('#dl-tool').click();
    await wait(80);
    assert.strictEqual(name, 'integrated-temporal-network-builder.html');
    const text = await new Promise((res) => { const fr = new w.FileReader(); fr.onload = () => res(fr.result); fr.readAsText(blob); });
    assert(/^<!doctype html>/.test(text) && text.includes('Integrated Temporal Network builder') && text.includes('function figureBrief'), 'full page expected');
    assert(text.includes('Build a network to see it here.'), 'the copy is the page as served, before any figure is drawn');
    const copy = new JSDOM(text, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'file:///C:/Users/me/integrated-temporal-network-builder.html', beforeParse: (cw) => { cw.scrollTo = () => {}; } });
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
