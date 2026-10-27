// Draw an episode log with the real page (jsdom) and save the figure as SVG: the whole session, or groups side by side.
//   node scripts/eval/export_tool_figure.js <log.csv> <out.svg> --label "Name" [--order "A|B|C"] [--norm] [--groups] [--slice 10] [--brief brief.txt]
// --brief also saves the data part of the AI reading request (figureBrief), exactly as the page would send it.
const fs = require('fs');
const path = require('path');
const { JSDOM } = require(path.join(__dirname, '..', '..', 'node_modules', 'jsdom'));

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const [csvPath, outPath] = args;
const html = fs.readFileSync(path.join(__dirname, '..', '..', 'index.html'), 'utf8');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const text = fs.readFileSync(csvPath, 'utf8');

// Optional fixed circle order, saved the way the Check step's code manager saves a reordering.
let beforeParse = () => {};
if (opt('--order')) {
  const order = opt('--order').split('|'), names = [], seen = {};
  text.trim().split(/\r?\n/).slice(1).forEach((l) => { const b = l.split(',')[1]; if (!(b.toLowerCase() in seen)) { seen[b.toLowerCase()] = 1; names.push(b); } });
  const cfg = order.filter((n) => names.includes(n)).map((n) => ({ o: names.indexOf(n), label: n, keep: true }));
  if (cfg.length !== names.length) throw new Error('order misses some of: ' + names.join(', '));
  beforeParse = (win) => win.localStorage.setItem('tona-codes', JSON.stringify({ names, cfg }));
}

(async () => {
  const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/', beforeParse });
  const w = dom.window, d = w.document, errors = [];
  w.addEventListener('error', (e) => errors.push(e.message));
  let blob = null;
  w.URL.createObjectURL = (b) => { blob = b; return 'blob:x'; }; w.URL.revokeObjectURL = () => {}; w.scrollTo = () => {};
  w.HTMLAnchorElement.prototype.click = function () {};
  const read = (b) => new Promise((res) => { const fr = new w.FileReader(); fr.onload = () => res(fr.result); fr.readAsText(b); });
  const set = async (id, val) => { const el = d.querySelector(id); if (el.type === 'checkbox') el.checked = val; else el.value = val; el.dispatchEvent(new w.Event('change', { bubbles: true })); await wait(400); };
  await wait(300);
  d.querySelector('#data').value = text;
  d.querySelector('#check-paste').click(); await wait(300);
  d.querySelector('#build').click(); await wait(800);
  await set('#s-theme', 'light');
  if (args.includes('--norm')) await set('#s-norm', true);
  if (opt('--slice')) await set('#s-slice', opt('--slice'));
  if (opt('--label')) {
    d.querySelector('[aria-label="Rename this dataset"]').click();
    const h = d.querySelector('#ds-name'); h.textContent = opt('--label');
    h.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await wait(300);
  }
  if (args.includes('--groups')) await set('#grp', 'cmp');
  d.querySelector('#dl-svg').click(); await wait(300);
  // jsdom's serialiser repeats xmlns on the root, and the bare font name needs quotes outside the page's CSS.
  const svg = (await read(blob))
    .replace(/(<svg\b[^>]*?) xmlns="http:\/\/www\.w3\.org\/2000\/svg"([^>]*?) xmlns="http:\/\/www\.w3\.org\/2000\/svg"/, '$1$2 xmlns="http://www.w3.org/2000/svg"')
    .replace(/font-family="Source Sans 3,/g, "font-family=\"'Source Sans 3',");
  fs.writeFileSync(outPath, svg);
  if (opt('--brief')) {
    const peek = d.querySelector('#ai-peek'); peek.open = true; peek.dispatchEvent(new w.Event('toggle'));
    fs.writeFileSync(opt('--brief'), d.querySelector('#ai-preview').textContent.split('DATA (sent as the message):\n')[1]);
  }
  const t =[...d.querySelectorAll('#net text')].map((n) => n.textContent).join(' | ');
  console.log(path.basename(outPath), '|', t.slice(t.indexOf('Most time'), t.indexOf('Disc area')).replace(/ \| /g, ' '));
  if (errors.length) console.log('errors', errors);
})();
