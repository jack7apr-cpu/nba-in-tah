# NBA in tah: replay, risk model, lock engine, trade values

Built 10 Nov 2026 from weeks 1–3, plus Monday of week 4. Data: Sleeper per-game projections and box stats (`data/2026/projections`, `data/2026/stats`). Scoring is read from `league.json`, and the formula reproduces all 216 counted starter scores from weeks 1–3 exactly.

| file | what it does |
|---|---|
| `nbadata.py` | loader: league scoring, per-game projections and actuals, team game dates |
| `replay.py` | task 1: Sleeper game-day projections vs actuals |
| `risk.py` | task 2: lock-time forecast (P(plays) × points if he plays); `risk.py fit` refits and replays |
| `risk_params.json` | fitted parameters (refit weekly with `risk.py fit`) |
| `lock.py` | task 3: `plan` = this week's lock thresholds and free rolls; `backtest` = engine vs real locks |
| `value.py` | task 4: `check`, `board` (buy/sell), `trade "A,B" "C"` |

`engine.py`, `market.py`, `crystal.py` and `trade_check.py` are still NFL copies; the NBA versions are the files above.

## 1. Replay: Sleeper projections vs what happened

Sleeper keeps one projection row per game and overwrites it until tip-off. The stored numbers are therefore **game-day** projections: a player ruled out shows a blank row.

| projected | games | r | MAE | bias (actual − proj) | sat out |
|---|---|---|---|---|---|
| all > 0 | 3092 | 0.730 | 5.15 | −1.14 | 5.7% |
| 0–10 | 903 | 0.403 | 3.75 | −0.20 | 18.1% |
| 10–20 | 1407 | 0.402 | 5.33 | −1.53 | 0.8% |
| 20–30 | 723 | 0.261 | 6.24 | −1.64 | 0.1% |
| 30+ | 59 | 0.236 | 8.70 | +0.07 | 0.0% |

Weeks 1, 2 and 3 are all similar (r 0.72–0.74). Sleeper runs about 1.5 points too high for 10–30 projected players, even counting only games they played.

**The catch:** you make lock decisions days before the game, when the game-day snapshot doesn't exist yet. So task 2 replays at **lock time**: from each game date in a week, forecast each of the player's remaining games that week, using only what was known before that date. The "raw Sleeper" baseline is the latest projection known then, with the assumption that he plays.

## 2. Risk model (`risk.py`): beats raw Sleeper out of sample

Forecast = **P(plays) × points if he plays**
- points if he plays = calibration (0.91) × blend of the latest Sleeper projection with his own last 10 games (form gets 50% weight after 10 games) × minutes trend (last 3 games' minutes vs projected, weight 0.25)
- P(plays) = shrunk miss rate (4% prior, 80-game prior weight). If he missed his latest game, P(misses again) = 95% (the games-missed haircut). Live, it also uses the Sleeper and ESPN injury tags, taking whichever is more pessimistic, and the tag's effect fades for later games.

Parameters were fitted on weeks 1–2 and **tested on weeks 3–4**:

| test wk 3–4 (2591 forecasts) | MAE | r | bias | Brier (plays?) |
|---|---|---|---|---|
| raw Sleeper | 7.56 | 0.465 | −4.16 | 0.146 |
| risk model | **6.10** | **0.560** | **+0.67** | **0.108** |

The improvement holds in every tier (22–30 projected: MAE 9.68 → 6.82) and at every horizon (same day 7.42 → 5.75, 3–6 days ahead 7.72 → 6.50).

Ablation on the test weeks (MAE): availability alone 7.56 → 6.45 (most of the gain). Form, calibration and minutes add the rest (6.10). **Back-to-backs and rest days fit to zero**: once form and availability are in, they added nothing in these 3 weeks, so their weights are 0. Refit as the sample grows.

Not replayable: the injury tags. Sleeper and ESPN only publish *current* status, so there's no history to test against. Those weights (Questionable 60%, Doubtful 20%, Out 0%, fading 0.7/day) are priors. **collect.py should archive both injury feeds daily** so they can be validated later.

## 3. Lock engine (`lock.py`)

Each lineup slot is a sequence of chances: the regular's games, plus free rolls from the bench on nights he's idle. The last chance is forced (his team's final game, 0 if he sits). Backward induction gives "lock if ≥ X" after every chance. The score spread is the real right-skewed one (actual ÷ forecast: 10th pct 0.45, median 1.00, 90th pct 1.65), not a normal curve.

Quick table (95% to play):

| expected if plays | 1 game left | 2 left | 3 left |
|---|---|---|---|
| 20 | lock ≥ 19 | 23.5 | 26 |
| 25 | 24 | 29 | 32.5 |
| 30 | 28.5 | 35 | 39 |
| 35 | 33 | 41 | 45.5 |

**Backtest vs real locks, weeks 1–3.** Same starters, same games, engine deciding with only what it knew then:

| manager | actual | engine | gain | share of possible gain captured (actual → engine) |
|---|---|---|---|---|
| Maxi | 640.0 | 737.5 | +97.5 | 50% → 82% |
| Tony | 672.5 | 716.5 | +44.0 | 40% → 74% |
| Isaac | 713.0 | 751.5 | +38.5 | 37% → 52% |
| Lewis | 730.5 | 767.5 | +37.0 | 60% → 74% |
| Matt | 615.5 | 650.5 | +35.0 | 68% → 80% |
| Kyran | 746.0 | 777.0 | +31.0 | 76% → 89% |
| David | 690.5 | 704.5 | +14.0 | 68% → 74% |
| **Jack** | **794.5** | 788.5 | −6.0 | 65% → 63% |

League total: managers 5602.5, **engine + risk model 5893.5**, engine + raw Sleeper 5810.5, never locking 4454.0, perfect hindsight 6409.5. In week 3 (out of sample for the risk model), the engine with the risk model scores 1989.5 vs 1924.0 with raw Sleeper.

Biggest misses by managers: Isaac rode Luka's 49 into a DNP (0, week 3). Maxi did the same with Flagg's 27.5 (week 1). Tony gave up LaVine's 25 for a 4.5 final game (week 2).
Biggest engine miss: Haliburton week 2 (31, then DNP×3). Matt locked the 31. The engine held because it had no injury feed in the replay. Live, an "Out" tag before game 2 would make it lock.

Caveats: the API only shows final week-end starters, not lineup history, so free-roll locks and mid-week swaps can't be replayed exactly. Treat the gains as indicative. Jack already locks better than the engine on his own players.

`lock.py plan Jack` for week 4 from 10 Nov: **lock Jamal Murray's 30.5 now**. Hold Kessler 26.5 (rest of week worth 29.5), Jerome 21.0 (25.6), Jalen Johnson 18.5 (31.7) and Dejounte Murray 8.0 (25.1). Giannis is GTD (60% today, 86–90% later in the week), so his slot is worth holding at ~38.7.

## 4. Trade values (`value.py`)

- **No free NBA trade market exists.** FantasyCalc, KTC and Dynasty Dealer are football-only, and the old FantasyPros/CBS NBA charts are dead. The best free price is **Sleeper's own ADP** (`adp_std` in the season projections), i.e. what Sleeper drafters paid.
- **Checked against this league:** the league has made **0 trades** (weeks 1–4), so nothing can be checked against trades and nothing is fitted to them. Instead, ADP vs this league's own draft gives Spearman **0.893**, so Sleeper ADP describes how these 8 price players. Biggest reaches: Queta (David, pick 72 vs ADP 143), Dejounte Murray (Jack, 55 vs 113), Clingan (Jack, 39 vs 93). Biggest fallers: Morant (David, 89 vs 48), Fox (Tony, 93 vs 52), Bane (Jack, 71 vs 45).
- ADP is a preseason price. Its rank agreement with points per game so far is 0.716, about the same as this league's draft order (0.712).
- **Our value** = rest-of-season Lock-In value over replacement (best 3 free agents). It is built from each week's optimal-stopping value with playoff weeks ×1.5. **Market** = ADP mapped rank-for-rank onto the same scale. A trade is judged by each team's best-lineup change over the remaining weeks, so a 2-for-1 is priced correctly without a fitted package discount.
- Injured players: "Out" with no known return date = back in 14 days. Put real dates in `data/returns.json` (`{"Anthony Edwards": "2026-11-24"}`) from news before trusting a sell signal on an injured star.
- Example: Jack gives Jerome + Dejounte Murray for Morant (Out): Jack −58, Isaac +35. No.

## Three registers

**Layman.** Sleeper's guesses look good on the day of a game because by then they already know who's sitting. Days earlier, when you actually decide whether to lock, they're about 4 points too optimistic, mostly because they don't plan for players missing games. The new model fixes that. A lock calculator built on it would have beaten 7 of 8 managers' real decisions. Jack is the exception: he already locks better than the calculator. There's no reliable NBA trade-price website, and nobody in this league has traded, so prices come from Sleeper's draft data plus the model's own rest-of-season value.

**Fantasy.** Biggest edge: don't ride a hot early game into an uncertain final game. Luka 49 → DNP, Flagg 27.5 → DNP and LaVine 25 → 4.5 were the league's costliest misses. Lock rules of thumb: with 1 game left, lock anything at or above his average. With 2 left, lock above ~1.17× average. With 3 left, above ~1.3×. Buy-low on the board: Sabonis, Giannis, Kessler, Clingan. Market overpays for Zubac, DeRozan, Ware and Coby White. Injured-star sells (Edwards, Morant, Jalen Williams) depend on return dates, so check news before acting.

**Coding.** The replay is walk-forward: every forecast uses only rows dated before its vantage date. Params were fitted by coordinate search on wk 1–2 (objective: MAE of expected points) and tested on wk 3–4. Lock values come from backward induction, `V = (1−q)·V' + q·E[max(m·R, V')]` with the final chance forced (`q·m`), where R is an empirical ratio sample (215 quantiles). Values: weekly `chain()` per player → 9-slot DFS best lineup per week → summed with playoff weight. Market mapping is a monotone rank-to-rank transform, with no curve fitting. Stdlib only. Local is Python 3.9 (so a custom `corr`); Actions uses 3.12.

## For Sonnet (plumbing)
- `collect.py`: write per-game projections and stats to `data/<season>/projections|stats/week_NN.json` (the format this code reads). Archive Sleeper + ESPN injury snapshots daily (`data/<season>/injuries/YYYY-MM-DD.json`), so the injury priors can be replayed. Also archive future-game projections daily, so a true days-ahead Sleeper baseline exists.
- Site: show `lock.py plan` per team (the LOCK NOW / HOLD lines first), and `value.py board`.
- Weekly: run `risk.py fit` after each week's stats land.
