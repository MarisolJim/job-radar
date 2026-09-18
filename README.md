# job-radar

A personal, self-hosted job tracker built to make you an **early applicant**.
It polls company career feeds directly (not slow aggregators), filters to the
roles you care about, and emails you: an **instant alert** when a priority
company posts, plus a **daily digest** of everything new.

## How it works

```
companies.yaml  →  ATS pollers (Greenhouse / Lever / Ashby)
                        ↓  normalize to a common Job record
filters.yaml    →  keep only YOUR roles (title/location/remote rules)
                        ↓
data/seen.json  →  remember what we've seen (→ what's NEW)
                        ↓
Gmail (SMTP)    →  instant alert (priority cos) + daily digest
```

Because it hits each company's **ATS feed** (the same data their careers page
loads), you see a posting the moment HR publishes it — not hours later when an
aggregator re-scrapes it.

## Files you edit

- **`companies.yaml`** — your watchlist. Each entry is an ATS + slug + priority.
  Find the slug in the careers URL: `boards.greenhouse.io/SLUG`,
  `jobs.lever.co/SLUG`, or `jobs.ashbyhq.com/SLUG`.
  `priority: 2` = instant alert; `1`/`0` = daily digest only.
- **`filters.yaml`** — keyword/location/remote rules that define your shortlist.

## Run it locally

```bash
pip install -r requirements.txt
python src/main.py poll      # fetch, filter, record new, alert on priority
python src/main.py digest    # email a summary of the last 24h
```

Email is optional locally: without `SMTP_*` env vars, polling still fetches,
filters, and records — it just skips sending.

## Run it on GitHub Actions (recommended)

1. Push this folder to a **new private GitHub repo**.
2. Create a Gmail **App Password** (Google Account → Security → 2-Step
   Verification → App passwords). This is required; your normal password won't
   work over SMTP.
3. In the repo: **Settings → Secrets and variables → Actions**, add:
   - `SMTP_USER` — your Gmail address
   - `SMTP_PASS` — the 16-char App Password
   - `DIGEST_TO` — where to send (usually your Gmail address)
4. The workflows run automatically:
   - `poll.yml` — every ~30 min, sends instant alerts.
   - `digest.yml` — daily at 13:00 UTC (edit the cron for your timezone).

State (`data/seen.json`) is committed back to the repo after each poll, so the
tool remembers what it has already seen between runs.

### Notes

- **First run** records everything currently open as "new" and may send one
  large instant alert for your priority companies. It settles after that.
- GitHub can delay scheduled runs a few minutes on low-traffic repos; ~30 min
  is the practical floor for free cron. For tighter polling, run `poll` from
  Windows Task Scheduler on an always-on machine.

## Adding more sources

New company ATS types or social-impact job boards plug in as a new module in
`src/sources/` that returns `Job` objects — nothing downstream changes.
Planned next: The Impact Job, FFWD, NTEN, Tech Jobs for Good, and the
Responsible Tech Job Board.
