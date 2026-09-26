// Smoke tests: load index.html in jsdom, run the real page script, check parsing,
// rendering, modes, frames, bad input and standalone exports. Run: npm test
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function load() {
  const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/' });
  const w = dom.window;
  const errors = [];
  w.addEventListener('error', (e) => errors.push(e.message));
  w.URL.createObjectURL = () => 'blob:test';
  w.URL.revokeObjectURL = () => {};
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

  await t('loads sample without script errors', async () => {
    assert.deepStrictEqual(errors, []);
    assert(/episodes from 30 learners, 5 behaviours/.test(d.querySelector('#status').textContent));
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

  await t('rejects a log with missing columns', async () => {
    d.querySelector('#data').value = 'name,foo\na,b';
    d.querySelector('#build').click();
    assert(/Missing columns?: /.test(d.querySelector('#status').textContent));
  });

  await t('accepts a log without an end column (Q13 style)', async () => {
    d.querySelector('#data').value = 'student_id,activity,start_time\nS1,Reading,09:00:10\nS1,Question,09:02:15\nS1,Hint,09:02:50\nS1,Question,09:03:20';
    d.querySelector('#build').click();
    await wait(80);
    assert(/No end column/.test(d.querySelector('#status').textContent));
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

  await t('clear saved data restores the sample', async () => {
    d.querySelector('#clear').click();
    await wait(80);
    assert(/Saved data cleared/.test(d.querySelector('#status').textContent));
  });

  assert.deepStrictEqual(errors, []);
  console.log(`\n${passed} tests passed`);
  process.exit(0);
})().catch((e) => { console.error('FAIL', e.message); process.exit(1); });
