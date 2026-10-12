# SA eTender Pro

Finds open **IT tenders** on South Africa's eTenders portal, and helps you prepare and track bids for them.

**Live site:** https://kagiso933.github.io/etender-pro/ (after GitHub Pages is enabled)

## How it works

```
eTenders OCDS API ──► GitHub Action (every 6h) ──► data/tenders.json ──► website (GitHub Pages)
(National Treasury)    etender_scraper.py                                  index.html
```

- **Data source:** National Treasury's official open-data API, https://ocds-api.etenders.gov.za. The tool reads this API instead of scraping web pages, so it doesn't break when the portal's HTML changes.
- **Fetcher:** `etender_scraper.py` uses only the Python standard library.
  - It reads the last 60 days of published tenders.
  - It keeps the ones that are still open (closing date in the future).
  - It sorts them into IT categories: Software & Systems, Network & Infrastructure, Cloud, Cybersecurity, End-User Computing, Telecoms, and IT Services & Support.
  - It records each tender's briefing session (date, compulsory or not, venue) and whether it can be attended online (Teams, Zoom, virtual or a join link). It reads eTenders' briefing fields first and falls back to the tender description.
- **Refresh:** `.github/workflows/update-tenders.yml` runs the fetcher every 6 hours and commits the result. You can also run it any time from **Actions → Update tender data → Run workflow**.
- **Website:** `index.html` is a single static page with no build step. It has three tabs:
  - **Discover:** search and filter open tenders, see closing dates, and open the tender PDFs directly.
  - **AI analysis:** paste text from the tender PDF and get a go/no-go view, the mandatory requirements, what to source and where, a cost build-up, and an action plan.
  - **Bid builder:** a checklist of standard South African bid requirements, each with where to get it (CSD, SARS, CIPC, B-BBEE, SBD forms and so on).
    - AI can pull the tender-specific requirements out of the pasted document text.
    - It saves your progress and notes, and can draft a bid response.
    - Progress is saved in your browser.

## Ryno-Tec hub integration

- **Briefing filter:** Discover has a *Briefing* filter. Choose *Online briefing* to see only tenders you can brief on remotely.
- **Export for Ryno-Tec hub:** downloads the filtered tenders as JSON. In the hub, go to Tenders → *Import file*. The hub keeps the IT tenders with an online briefing and updates ones it already has without touching your bid status or notes.
- **Daily sync:** a scheduled Claude task reads `data/tenders.json` each morning and adds new online-briefing tenders to the hub.
- **Deep links:** `#tender=<ocid>&tab=bid` (or `tab=analysis`) opens a tender straight in the Bid builder. The hub's *Build bid in eTender Pro* button uses this.

## Setup

1. **GitHub Pages:** go to Settings → Pages, set Source to *Deploy from a branch*, choose `main` and `/ (root)`, then Save.
2. **Data:** the first data run starts automatically after the push. To run it again, use Actions → *Update tender data* → *Run workflow*.
3. **AI features:** click **API key** in the app and paste a key from https://console.anthropic.com.
   - The key is stored only in your browser's localStorage. It is never committed to the repo.
   - Calls go straight from your browser to Anthropic and are billed to your key.

## Run locally

```bash
python3 etender_scraper.py            # writes data/tenders.json
python3 -m http.server 8000           # then open http://localhost:8000
```

Fetcher options: `--days 90` looks further back, `--all` keeps non-IT tenders, and `--out path.json` changes the output file.

## Optional API server

`server.js` serves the same data as a REST API (`/api/tenders`, `/api/stats`, `/health`) and refreshes it every 6 hours. It needs Node 18+ and Python 3:

```bash
npm install && npm start
```

You don't need it for the website.

## Limits

- Only tenders that departments publish to eTenders appear. Many municipalities and SOEs advertise elsewhere too.
- The **tender value is usually not published** and shows as "Not disclosed".
- The detailed requirements are inside the tender PDFs. Paste the PDF text into the app so the AI can extract them.
- IT detection is keyword-based, so the occasional non-IT tender may slip in or out. You can tune the patterns in `CATEGORIES` and `EXCLUDE` in `etender_scraper.py`.
- Always confirm requirements against the official documents before you submit.
