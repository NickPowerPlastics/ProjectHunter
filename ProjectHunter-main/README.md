# ProjectHunter
Sales intelligence platform for identifying, tracking, and winning data center infrastructure projects

## Arizona intelligence release

This build adds an actionable Arizona outreach workflow:

- `/contacts` now shows prioritized electrical-contractor contacts with usable email links.
- Project research pages load saved contractor intelligence, confidence scores, evidence links, and matching contacts.
- Intelligence data is stored in `data/arizona_intelligence.json`.
- The original placeholder-only research layout has been replaced with an actionable contractor and contact view.

Run locally:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.


## v4 Opportunity Finder
- Connects saved Arizona project intelligence to real contractor contacts.
- Shows confidence, evidence, best contact, and recommended next action.
- Adds Arizona contractor campaigns for qualified contacts not yet tied to a confirmed award.
- Keeps the discovery feed clearly separated from outreach-ready intelligence.
