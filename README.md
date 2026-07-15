# Bristol Job Market Tracker

A live-updating dashboard of Bristol / South West job vacancies, sectors, salaries
and top hiring companies, built on the free Adzuna API. Runs itself daily via
GitHub Actions, no server required.

## How it works

- `fetch_data.py` calls the Adzuna API and writes a snapshot to `data/`
- A GitHub Actions workflow (`.github/workflows/update-data.yml`) runs that script
  once a day and commits the result
- `index.html` is a static dashboard that reads `data/latest.json` and
  `data/history.csv` and renders it with Chart.js
- GitHub Pages serves `index.html` as a public URL, no hosting to manage

## Setup (about 15 minutes)

1. **Get API keys.** Register free at [developer.adzuna.com](https://developer.adzuna.com/).
   You'll get an `app_id` and `app_key`.

2. **Push this folder to a new GitHub repo** (e.g. `bristol-job-tracker`).

3. **Add your keys as repo secrets.**
   Repo → Settings → Secrets and variables → Actions → New repository secret
   - `ADZUNA_APP_ID`
   - `ADZUNA_APP_KEY`

4. **Run the workflow once manually** to seed the data files.
   Repo → Actions → "Update job market data" → Run workflow.
   Check the log, if any API call errors out, the response body is printed,
   compare it against the [Adzuna API docs](https://developer.adzuna.com/docs)
   and adjust the relevant line in `fetch_data.py`. I wrote this against their
   published docs but couldn't test live calls while building it, so this
   first run is the real test.

5. **Turn on GitHub Pages.**
   Repo → Settings → Pages → Source: "Deploy from a branch" → Branch: `main`, folder `/ (root)`.
   You'll get a URL like `https://<your-username>.github.io/bristol-job-tracker/`.
   That's your live, linkable dashboard.

6. **Test locally before pushing (optional).**
   ```bash
   cd bristol-job-tracker
   python3 -m http.server
   ```
   Then open `http://localhost:8000`. Opening `index.html` directly as a file
   (double-click) won't work, browsers block `fetch()` for local files, and
   it'll just fall back to showing sample data.

## Notes

- **API limits.** Adzuna's free tier has a call quota, check current limits
  on their site. This script makes roughly one call per category per location
  per day (~60 calls). If you hit the limit, either trim the `LOCATIONS` dict
  in `fetch_data.py` down to just Bristol, or change the cron schedule in the
  workflow file from daily to weekly.
- **Trend chart** only gets interesting after it's been running a few days,
  `history.csv` grows one row per location per day.
- **"Applications per vacancy"** (a genuine measure of competition) isn't
  exposed in Adzuna's free public API as far as I could find, that data
  seems to sit behind their paid "Adzuna Intelligence" product. If you want
  that metric later, it's worth a proper look before building around it.
- Rebrand freely, colours are all CSS variables at the top of `index.html`.
