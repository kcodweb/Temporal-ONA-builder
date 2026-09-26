// Export figure SVGs from the real page (sample data or a CSV you pass in).
// Usage: node scripts/export-figures.js [path/to/log.csv] [--sample-only]
// Writes figures/*.svg. Convert to PNG with e.g. `python -m cairosvg figures/whole-timeline.svg -o whole.png -W 1600`.
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const args = process.argv.slice(2);
const sampleOnly = args.includes('--sample-only');
const csvPath = args.find((a) => !a.startsWith('--'));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/' });
  const w = dom.window, d = w.document;
  w.scrollTo = () => {};
  await wait(400);
  d.querySelector('#sample').click(); // the page opens on the upload step
  await wait(200);
  if (sampleOnly) {
    fs.mkdirSync(path.join(root, 'samples'), { recursive: true });
    fs.writeFileSync(path.join(root, 'samples', 'sample-srl-log.csv'), d.querySelector('#data').value + '\n');
    console.log('wrote samples/sample-srl-log.csv');
    process.exit(0);
  }
  if (csvPath) {
    d.querySelector('#data').value = fs.readFileSync(csvPath, 'utf8');
    d.querySelector('#build').click();
    await wait(200);
  }
  const out = path.join(root, 'figures');
  fs.mkdirSync(out, { recursive: true });
  const svg = d.querySelector('#net');
  const save = (name) => fs.writeFileSync(path.join(out, name + '.svg'),
    svg.outerHTML.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg" width="800"'));
  const mode = async (m) => { d.querySelector(`.arrows [data-e="${m}"]`).click(); await wait(100); };

  await mode('swell'); save('whole-timeline');
  await mode('colour'); save('whole-colour');
  const frames = d.querySelectorAll('#frames [data-f]');
  for (const b of frames) {
    if (b.dataset.f === '-1') continue;
    b.click(); await wait(80); save('frame-' + (+b.dataset.f + 1));
  }
  console.log('wrote', fs.readdirSync(out).length, 'SVGs to figures/');
  process.exit(0);
})();
