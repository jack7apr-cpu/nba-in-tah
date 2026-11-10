# Opus task: NBA "NBA in tah" replay + value model (design work only)

Read first: ../personal skills/NBA_HANDOFF.md and memory notes sleeper-nba-league, sleeper-lockin-playbook.
Repo: this folder (git repo, remote jack7apr-cpu/nba-in-tah, public). League 1410748359358099456, me = jackhill1617. Data already fetched in ./data/2026 (sleeper.py in ./engine).

## Do (design + validation only; leave the website/Actions/ntfy plumbing to Sonnet)
1. Replay: compare Sleeper per-game projections (api.sleeper.com/projections/nba/2026/<week>, one row per game) against actual weekly stats for weeks 1-3. Report corr, MAE, bias, by projection tier.
2. Add a risk model: games-missed haircut, back-to-backs, rest days, minutes trend, two injury sources (Sleeper + ESPN). Show it beats raw Sleeper in the replay.
3. Lock engine: optimal stopping per slot under Lock-In rules (only one game per starter counts; must lock before next game; unlocked = final game of week, 0 if he sat). Output lock thresholds + free-roll suggestions per the playbook. Backtest against weeks 1-3 real lock decisions.
4. Trade market: find an NBA player-value source, check it against this league's own past trades. Never fit a curve by "most balanced past trades".
5. Write results to engine/*.py plus a short engine/REPLAY.md. Scoring: PTS .5 REB 1 AST 1 STL 2 BLK 2 TO -1 DD 2 TD 3.5 3PM .5, 40+ +1, 50+ +2 (re-read league scoring_settings from the API).
Commit locally; do not push (token not stored yet). Explain findings in three registers: layman, fantasy, coding. Refer to managers by real names (Kyran, Maxi, David, Tony, Isaac, Lewis, Matt).
