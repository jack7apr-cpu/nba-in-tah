# NBA in tah: how-to guide

## Your daily routine (5 minutes)
- **Morning:** open the app. The **Do now** banner at the top of Home tells you if anything needs doing (a lock, a hurt starter, stale data).
- **Before the first tip (about 30 min before):** open **Lineup**, pick today, and set your Sleeper lineup to match: regulars where they play, a bench player in any slot whose regular is idle (a 🎲 free roll).
- **After games finish:** check the scores in Sleeper. If one beats its **lock if ≥** number, lock it in Sleeper, then tap **I locked** in the app so GitHub and Claude know.
- **Quiet phone = nothing to do.** You only get a ping when a starter is questionable before a game, or a finished score beats the rest of his week (LOCK).

## What each tab is for
- **Home:** Do-now banner, Bowel Index (talent + clean locking + results), Excel download.
- **Lineup:** the best 9 for each day with free rolls and lock thresholds.
- **Weeks:** official weekly scores, Isaac's recap and awards, the live week.
- **Managers / Lock Lab / Players / Waivers:** the almanac, rebuilt from Sleeper every 3 hours.
- **Live:** your lock plan for the whole week and roster injuries.
- **Moves:** your win chance this week, a lock stance (protect or chase), David's lineup, and the best free-agent adds.
- **Fun:** leaders, score lines, head to head, weekly review against the lock engine, Format Lab, Team Value, Lock Leaderboard, awards.
- **Odds:** the Crystal Ball, 20,000 simulated seasons.
- **Trades:** pick ANY two managers, tap players from each side to build a deal and see what it does to both lineups to season end (full model: weekly best lineup, injuries, return dates). 'Find deals that help both' searches 1-for-1, 2-for-1 and 1-for-2 swaps. Also a value board and win-win ideas for you.

## How locking works (Lock-In rules)
- Only **one game per starter** counts each week. You lock a game after it ends and before that player's next game starts. Locks can't be undone.
- If you never lock, Sleeper uses his team's **final game** of the week (0 if he sat it out).
- A bench player who already played can't be locked by moving him into a slot afterwards. Swap **before** the game.
- **Lock if ≥ X** means: his score beats what the rest of the week is worth on average. Below it, hold. With fewer games left the number drops.
- **Free roll:** on a night your regular doesn't play, put a bench player in his slot. It costs nothing while unlocked. Lock the free roller only if he beats the threshold.
- **Protect a lead / chase a deficit:** the Moves tab says which. Protect = take good scores. Chase = hold for ceilings.

## Your phone setup
- **Site:** open the site in Safari, tap Share, then **Add to Home Screen**. Use that icon from now on.
- **Sync key:** the first time you tap **I locked** it asks for your sync key. Paste it once (from the Home Screen icon, not Safari).
- **Alerts:** install the ntfy app, subscribe to your private topic, leave 'Use another server' off, allow notifications.
- **Widget:** install Scriptable, paste `widgets/nba-in-tah-widget.js` from the repo, then add a small Scriptable widget on your Home Screen and pick the script. It refreshes when iOS decides, usually 15 to 30 minutes.

## Every week
- **Monday:** official team totals and results appear by themselves. The weekly review and the safe model refit run automatically.
- **Optional:** send Claude the final matchup screenshots (every slot's counted score) and Isaac's recap. That updates Lock Lab, the Bowel Index and the debrief. Without them everything else still updates.
- **Trades:** check the Trades tab, then ask Claude before you offer anything.

## Words in the app
- **Ours / Market / Gap (Trades):** ours = our estimate of a player's points to season end above a free agent. Market = what Sleeper drafters paid (draft position) on the same scale. Gap = ours minus market. Positive = underpriced (buy). Negative = overpriced (sell).
- **Avg / L3 / Max / SD / GP (Players):** average points a game, average of his last 3, best game, how much his scores swing (lower = steadier), games played.
- **Locked / Missed / Low (Lock Lab):** the counted score, points left on the table (best game that week minus the score taken), and the lowest counted scores first.
- **Bowel Index:** Shit = talent, Poo = clean locking, Results = all-play win %. Weighted 30/30/40.
- **Hold value / worth:** the expected points of a slot if you keep waiting for the best chance this week.

## Asking Claude
- **'What now?'** gets a live lock check: lock X, hold Y, swap Z in before tip.
- **Tell Claude what you locked** if you didn't tap I locked. Claude can't see locks.
- **Trades:** ask before offering. Free agents: ask 'who should I pick up?'.
- **Tell Claude** if something on the site looks wrong or an alert was wrong.

## If something looks wrong
- **Stale data warning:** open the repo's Actions tab on GitHub. A red cross means a run failed, so tell Claude.
- **No pings:** check ntfy is subscribed to the right topic, notifications are allowed, and 'Use another server' is off.
- **I locked asks for the key every time:** you are probably in Safari, not the Home Screen icon. Enter it in the icon.
- **Giannis-style surprise:** the model uses team injury tags. If news changed after the last refresh, trust the news and tell Claude.
- **Limits:** Sleeper has no lock flags in its data, injury odds are priors until we have weeks of history, and early-season odds are wide.

