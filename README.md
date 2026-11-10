# NBA in tah

Auto-updating toolkit for the Sleeper league "NBA in tah" (8 teams, points scoring, Lock-In mode).
Site: https://jack7apr-cpu.github.io/nba-in-tah/ (rebuilt every 3 hours by GitHub Actions, no computer needed).

## What it does
| Tab | What you get |
|---|---|
| Home | "Do now" banner, Bowel Index, quadrant chart, Excel download |
| Lineup | the best 9 for each day with free rolls, lock thresholds, "I locked" buttons |
| Weeks | official weekly totals, Isaac's recap and awards, live week scoreboard |
| Managers / Lock Lab / Players / Waivers | the almanac, rebuilt daily from Sleeper |
| Live | lock plan for the week, roster, trending adds |
| Moves | win probability, lock stance, opponent lineup, best free-agent adds |
| Fun | leaders, weekly score lines, head to head, weekly review vs the lock engine, Format Lab, Team Value, Lock Leaderboard, awards tally |
| Odds | Crystal Ball: 20,000 simulated seasons and playoffs |
| Trades | value board (ours vs market), win-win ideas, quick calculator |

## How it runs
- `.github/workflows/update.yml`: every 3 h, collects data, builds every JSON file, deploys Pages.
- `alerts.yml`: every 20 min during tip-off hours. Applies phone lock taps, then sends a short ntfy ping only if a starter is questionable/out (pre-game) or a finished score beats the rest of the week's value (LOCK).
- `archive.yml`: twice a day, saves injury and projection snapshots and extends the official weekly totals.
- `weekly.yml`: Mondays, reviews locks vs the engine and refits the risk model only if it is clearly better.
- `tests.yml`: runs the test suite on every push.

Secrets (repo Settings, Secrets and variables, Actions): `NTFY_TOPIC` (alert topic) and `NTFY_CMD_TOPIC` (private channel the site's "I locked" button posts to). Never commit their values.

## Code map
- `engine/`: Sleeper client, collector (`collect.py`, `fetch_raw.py`), risk model (`risk.py`), lock engine (`lock.py`), value/trades (`value.py`), exporters (`export_*.py`), Crystal Ball (`crystal_nba.py`), weekly review. Method notes in `engine/REPLAY.md`.
- `almanac/`: official weekly totals, daily almanac data, live weeks, Excel export.
- `alerts/`: ntfy pings and phone lock sync.
- `site/`: the web app (`app.js`, `style.css`, `data/`).
- `widgets/`: Scriptable iPhone widget.

## Tests
```
python3 -m unittest discover -s tests
```
(needs `site/data/live.json` and `site/data/plan.json`; run `python3 engine/collect.py --out site/data/live.json`, `python3 engine/fetch_raw.py`, `python3 engine/export_plan.py --out site/data/plan.json` first, as CI does).

## Known limits
- Sleeper's API has no lock flags: locks are tracked in `site/data/locked.json` (phone taps or ask Claude).
- Slot-level lock detail and the points left on the bench need the manager's week-end screenshots; team totals come from Sleeper season points automatically.
- Injury probabilities are priors (no injury history yet; archived daily so they can be validated later).
- Past-week matchup files are frozen on first save because Sleeper's numbers drift.
