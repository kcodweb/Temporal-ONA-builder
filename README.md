# Temporal ONA builder

A browser tool that turns a coded episode log into an ordered network showing, in one figure:

- **how long** learners spent in each behaviour (disc area = share of the time window),
- **when** each behaviour happened (a clock ring of bars around each disc: 0′ at the top, clockwise, with minute numbers at the quarter points and the peak slice written under each label),
- **what followed what** (directed arrows, ONA-style moving window),
- **when each link happened** (timeline arrows that swell in the minutes the link occurred, coloured early to late).

It was built for self-regulated learning (SRL) codes, but any coded episodes work: collaboration moves, clickstream events, think-aloud codes. Sessions can last seconds, minutes, hours or days; the figure picks its time slices, frames and units to suit.

Everything runs in the browser. No data is uploaded. You can also download the tool as one HTML file and use it offline.

![Example figure](preview.png)

## Use it

Open the site: **https://kcodweb.github.io/Temporal-ONA-builder/**

1. **Upload.** Drop a CSV, TSV or semicolon-separated file onto the page, choose it with **Choose file**, or paste rows. No data yet? Try the built-in sample of 30 synthetic learners, or download the template.
2. **Check.** See how each column was read, change the column choices if needed, and look over the first rows, the behaviours found and any warnings (unreadable rows, `09:12`-style times, a missing end column).
3. **Explore.** Build the network, step through time frames (each frame button shows how many episodes start in it) or drag the window, click a disc to highlight only its links and see its details, save the figure as PNG or SVG, and **Copy caption** for a figure caption that states the sample, window and settings.
4. **AI reading (optional, beta).** Ask a language model for a first reading of the figure. See [AI reading](#ai-reading) below.

The page remembers your last log on this device, so next time it opens straight on your figure. **Clear saved data** removes it.

Times can be plain numbers, `mm:ss` (`12:30`), clock time (`09:12:30`) or date-times (`2026-03-01T09:12:30`). Plain numbers are read as minutes unless the column name says otherwise (`start_s`, `time_ms`) or they look like Unix timestamps; you can switch between minutes, seconds, milliseconds and hours on the Check step. Without an `end` column, each episode lasts until that learner's next episode starts.

Clock-ring slices and frames are set automatically (about 12 bars and 6 frames, so 5 and 10 minutes for a one-hour session); pick other sizes under **Settings → Time**.

```csv
learner,behaviour,start,end
S01,Planning,09:00:00,09:02:40
S01,Monitoring,09:02:40,09:03:30
S01,Debugging,09:03:45,09:07:10
```

## Use it offline

Click **Download tool** in the top bar (or **Download tool (HTML)** on the upload page). You get `temporal-ona-builder.html`, the whole tool in one file. Open it in Chrome, Edge, Firefox or Safari; nothing needs installing and it works without an internet connection (the page then uses your system font instead of Source Sans 3). Logs you load in the downloaded copy are remembered by that browser on that computer only.

## AI reading

The **AI reading** tab sends a summary of the figure you are looking at to a language model and shows a short draft reading: what the figure shows, patterns worth a closer look (with alternative explanations), cautions, and checks to run next. You can add a question to keep it focused. It is a draft to check against the figure, not a finding.

**What is sent.** Only aggregated numbers behind the current figure (minutes and time profile per behaviour, link weights and timing, settings, coverage) and fixed instructions. Raw rows and learner IDs are never sent. **See exactly what will be sent** shows the full text before you press the button. Nothing is sent until you press **Read this figure**.

**Providers.**
- **Claude (Anthropic API):** paste your own API key from [console.anthropic.com](https://console.anthropic.com). The default model is `claude-opus-5-5`; you can type another. The page calls the API directly from your browser.
- **OpenAI-compatible API:** any service with a `/v1/chat/completions` endpoint (OpenAI, OpenRouter, Groq and others). Enter the base URL, model name and key. The service must accept requests from a browser.
- **Local model on this computer:** Ollama (`http://localhost:11434/v1`) or LM Studio (`http://localhost:1234/v1`). Nothing leaves your computer. Enter a model you have installed (`ollama list`). If the page cannot reach the server, allow the page's origin: for the website, start Ollama with `OLLAMA_ORIGINS=https://kcodweb.github.io`; in LM Studio, turn on CORS in the server settings.

Keys stay in the page's memory unless you tick **Remember the key on this device**, which keeps it in this browser's local storage. **Clear saved data** removes it.

## Put it online

The whole tool is one file, `index.html`, with no build step and no server code.

**GitHub Pages**
1. Create a public repository and upload `index.html`, `README.md` and `preview.png`.
2. Go to **Settings → Pages**, set **Source** to *Deploy from a branch*, choose `main` and `/ (root)`, and save.
3. The site appears at `https://<your-username>.github.io/<repository-name>/` within a minute or two.

**Netlify Drop**
Drag this folder onto https://app.netlify.com/drop to get a public link without an account setup step.

Any static host (Vercel, Cloudflare Pages, a university web space) works the same way: serve `index.html`.

## Develop

```
npm install
npm test          # smoke tests against the real page
npm run figures   # export figure SVGs to figures/
```

See `CLAUDE.md` for the code map, formulas, design rules and roadmap.

## Scope

The link logic is adapted from ordered network analysis (ONA): each episode is linked from the previous *w* − 1 episodes. This is a descriptive visualisation, not a full ONA. It does not normalise connection vectors, reduce dimensions or test differences between groups. Use ONA for statistical comparisons.

## Privacy

The page makes no network requests except to load Google Fonts and, only when you press **Read this figure**, to send the figure summary to the model provider you chose. The last pasted log, settings and (if you ask) your AI key are kept in the browser's local storage for convenience; **Clear saved data** removes them. Use pseudonymous learner IDs with real student data.

## Cite

Bansal, K. (2026). *Temporal ONA builder* [Web tool].

## Licence

The code is released under the [MIT licence](LICENSE). The white paper and other documents in `docs/` are released under [CC BY 4.0](docs/LICENSE.md).
