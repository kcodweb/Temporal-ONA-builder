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

  await t('standalone exports trigger browser downloads', async () => {
    assert.strictEqual(d.querySelector('#exp-btns').hidden, false);
    let name = null;
    w.HTMLAnchorElement.prototype.click = function () { name = this.download; };
    d.querySelector('#dl-svg').click();
    await wait(80);
    assert(/^temporal-ona-.*\.svg$/.test(name), String(name));
  });

  await t('clear saved data returns to the upload step', async () => {
    d.querySelector('#clear').click();
    await wait(80);
    assert(/Saved data cleared/.test(d.querySelector('#toast').textContent));
    assert(shown('start'));
    assert.strictEqual(w.localStorage.getItem('tona-data'), null);
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
