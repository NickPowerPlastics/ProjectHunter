# ProjectHunter
Sales intelligence platform for identifying, tracking, and winning data center infrastructure projects

## Multi-state intelligence platform

The application reads its complete portfolio from `data/intelligence.json`. States,
companies, metrics, and search results are derived at runtime, so adding a state or
project requires only a feed update—no application code changes.

- `/contacts` now shows prioritized electrical-contractor contacts with usable email links.
- Project research pages load saved contractor intelligence, confidence scores, evidence links, and matching contacts.
- The State Explorer groups the full feed into collapsible state portfolios.
- Mission Control highlights discoveries, high-confidence opportunities, research
  gaps, and recently updated projects.
- Company and project workspaces connect roles, contacts, evidence, timelines, and
  estimated revenue.
- Global search covers projects, companies, contacts, and states.
- The original placeholder-only research layout has been replaced with an actionable contractor and contact view.

Run locally:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

### Updating the intelligence feed

Open `http://127.0.0.1:5000/admin/intelligence` on the computer running Project Hunter.
The loopback-only admin page accepts an uploaded or pasted JSON feed, validates its
schema, and shows project, state, and contact counts before import. A confirmed import
creates a timestamped file under `data/backups/`, atomically replaces
`data/intelligence.json`, and reloads the in-memory intelligence store.

Mission Control warns when the feed is more than three days old. Set
`INTELLIGENCE_STALE_AFTER_DAYS` to change that threshold.


## v4 Opportunity Finder
- Connects saved Arizona project intelligence to real contractor contacts.
- Shows confidence, evidence, best contact, and recommended next action.
- Adds Arizona contractor campaigns for qualified contacts not yet tied to a confirmed award.
- Keeps the discovery feed clearly separated from outreach-ready intelligence.
