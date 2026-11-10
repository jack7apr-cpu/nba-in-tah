#!/usr/bin/env python3
"""Crystal Ball: Monte Carlo of the rest of the regular season and the playoffs for NBA in tah.

    crystal_nba.py [--live site/data/live.json] [--facts site/data/factfile.json] [--runs 20000] [--out site/data/crystal.json]

Inputs: official results for finished weeks (factfile MU, else Sleeper totals), the real future
schedule (Sleeper matchup_ids, weeks up to the playoff start), each team's weekly score mean
(shrunk toward the league mean, since only a few weeks exist) and a pooled weekly sd.
Seeding: wins then points-for. Playoffs: 6 teams from week `playoff_week_start`, seeds 1-2 get byes
(round 1 3v6, 4v5; round 2 seed 1 vs lowest left, seed 2 vs the other; then the final).
Assumptions are written into the output so the page can show them.
"""
import argparse, json, math, random, sys

NAMES = {"jackhill1617": "Jack", "kingboo25": "Kyran", "idbh": "Isaac", "lmlewis": "Lewis", "matttallguy": "Matt",
         "maxcmaples": "Maxi", "vpiggz": "David", "donghyuk101301": "Tony"}
SHRINK = 4.0   # pseudo-weeks of league-average prior


def build(live, facts):
    users = {u["user_id"]: NAMES.get(u["display_name"].lower(), u["display_name"]) for u in live["users"]}
    rname = {r["roster_id"]: users[r["owner_id"]] for r in live["rosters"]}
    cur, st = live["state"]["week"], live["league"]["settings"]
    po_start, n_po = st.get("playoff_week_start", 22), st.get("playoff_teams", 6)
    mu = {int(w): ms for w, ms in (facts.get("MU") or {}).items()}
    mu = {w: [(a.replace(" (GPT)", ""), pa, b.replace(" (GPT)", ""), pb) for a, pa, b, pb in ms] for w, ms in mu.items()}
    played, future = {}, {}
    for w_s, rows in sorted(live["matchups"].items(), key=lambda x: int(x[0])):
        w = int(w_s)
        pairs = {}
        for r in rows:
            pairs.setdefault(r["matchup_id"], []).append(r)
        ms = [(rname[p[0]["roster_id"]], rname[p[1]["roster_id"]], p[0], p[1]) for p in pairs.values() if len(p) == 2]
        if w in mu:
            played[w] = [(a, pa, b, pb) for a, pa, b, pb in mu[w]]
        elif w < cur:
            played[w] = [(a, round(sum(x["starters_points"] or []), 1), b, round(sum(y["starters_points"] or []), 1)) for a, b, x, y in ms]
        else:
            future[w] = [(a, b) for a, b, _, _ in ms]
    return rname, played, future, cur, po_start, n_po


def schedule_future(future_api, live_league_id, cur, po_start):
    import urllib.request
    out = dict(future_api)
    for w in range(cur, po_start):
        if w in out:
            continue
        try:
            rows = json.load(urllib.request.urlopen(urllib.request.Request(
                f"https://api.sleeper.app/v1/league/{live_league_id}/matchups/{w}", headers={"User-Agent": "nba-in-tah/1.0"}), timeout=40))
        except Exception:
            continue
        yield_rows = {}
        for r in rows:
            yield_rows.setdefault(r["matchup_id"], []).append(r["roster_id"])
        out[w] = [tuple(v) for v in yield_rows.values() if len(v) == 2]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="site/data/live.json")
    ap.add_argument("--facts", default="site/data/factfile.json")
    ap.add_argument("--runs", type=int, default=20000)
    ap.add_argument("--out", default="site/data/crystal.json")
    a = ap.parse_args()
    live, facts = json.load(open(a.live)), json.load(open(a.facts))
    rname, played, future, cur, po_start, n_po = build(live, facts)
    lid = live["league"]["league_id"]
    # future weeks beyond the ones stored in live.json: pull straight from Sleeper, mapped to names
    fut = {w: ms for w, ms in future.items()}
    for w in range(cur, po_start):
        if w in fut:
            continue
        try:
            import urllib.request
            rows = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.sleeper.app/v1/league/{lid}/matchups/{w}", headers={"User-Agent": "nba-in-tah/1.0"}), timeout=40))
            g = {}
            for r in rows:
                g.setdefault(r["matchup_id"], []).append(rname[r["roster_id"]])
            fut[w] = [tuple(v) for v in g.values() if len(v) == 2]
        except Exception as e:
            print("schedule fetch failed", w, e, file=sys.stderr)
    teams = sorted(rname.values())
    sc = {t: [] for t in teams}
    wins0 = {t: 0 for t in teams}
    pf0 = {t: 0.0 for t in teams}
    for w, ms in played.items():
        for x, px, y, py in ms:
            sc[x].append(px); sc[y].append(py); pf0[x] += px; pf0[y] += py
            if px != py:
                wins0[x if px > py else y] += 1
    allv = [v for t in teams for v in sc[t]]
    lg_mu = sum(allv) / len(allv)
    resid = [v - sum(sc[t]) / len(sc[t]) for t in teams for v in sc[t]]
    sd = max(20.0, math.sqrt(sum(r * r for r in resid) / max(1, len(resid) - len(teams))))
    mu = {t: (sum(sc[t]) + SHRINK * lg_mu) / (len(sc[t]) + SHRINK) for t in teams}
    rng = random.Random(7)
    res = {t: {"playoffs": 0, "bye": 0, "title": 0, "seed1": 0, "wins": 0, "dist": {}} for t in teams}
    me = "Jack"
    cond = {"win": [0, 0, 0, 0], "loss": [0, 0, 0, 0]}   # Jack given this week's result: [runs, playoffs, bye, title]
    weeks = sorted(fut)
    this_wk = fut.get(cur, [])
    for _ in range(a.runs):
        wins, pf = dict(wins0), dict(pf0)
        jack_res = None
        for w in weeks:
            for x, y in fut[w]:
                px, py = rng.gauss(mu[x], sd), rng.gauss(mu[y], sd)
                pf[x] += px; pf[y] += py
                win = x if px > py else y
                wins[win] += 1
                if w == cur and me in (x, y):
                    jack_res = "win" if win == me else "loss"
        order = sorted(teams, key=lambda t: (wins[t], pf[t]), reverse=True)
        top = order[:n_po]
        for i, t in enumerate(order):
            res[t]["wins"] += wins[t]
            res[t]["dist"][wins[t]] = res[t]["dist"].get(wins[t], 0) + 1
        for t in top:
            res[t]["playoffs"] += 1
        res[order[0]]["seed1"] += 1
        for t in top[:2]:
            res[t]["bye"] += 1
        # playoffs (single-game weeks)
        game = lambda x, y: x if rng.gauss(mu[x], sd) > rng.gauss(mu[y], sd) else y
        w1 = [game(top[2], top[5]), game(top[3], top[4])]
        rest = sorted(w1, key=lambda t: top.index(t))
        s1 = game(top[0], rest[1]); s2 = game(top[1], rest[0])
        champ = game(s1, s2)
        res[champ]["title"] += 1
        if jack_res:
            c = cond[jack_res]
            c[0] += 1; c[1] += me in top; c[2] += me in top[:2]; c[3] += champ == me
    n = a.runs
    out = {"runs": n, "week": cur, "playoff_start": po_start, "n_playoff": n_po, "sd": round(sd, 1), "lg_mean": round(lg_mu, 1),
           "assumptions": [f"Each team's weekly score is drawn from a normal curve: mean = its past average shrunk {SHRINK:.0f} weeks toward the league average ({lg_mu:.0f}), sd {sd:.0f}.",
                           "Real future schedule from Sleeper. Seeding = wins then points for.",
                           f"Top {n_po} make it. Seeds 1-2 get a bye, then single-week knockouts.",
                           "Ignores injuries and trades until more weeks exist; early-season odds are wide."],
           "teams": {t: {"mu": round(mu[t], 1), "w": wins0[t], "l": len(sc[t]) - wins0[t], "pf": round(pf0[t], 1),
                         "playoffs": res[t]["playoffs"] / n, "bye": res[t]["bye"] / n, "title": res[t]["title"] / n, "seed1": res[t]["seed1"] / n,
                         "exp_wins": res[t]["wins"] / n, "dist": {k: v / n for k, v in sorted(res[t]["dist"].items())}} for t in teams},
           "jack_if": {k: ({"playoffs": v[1] / v[0], "bye": v[2] / v[0], "title": v[3] / v[0]} if v[0] else None) for k, v in cond.items()}, "jack_opp": next(((y if x == me else x) for x, y in this_wk if me in (x, y)), None)}
    json.dump(out, open(a.out, "w"), separators=(",", ":"))
    for t in sorted(teams, key=lambda t: -out["teams"][t]["playoffs"]):
        o = out["teams"][t]
        print(f"{t:6} {o['w']}-{o['l']}  playoffs {o['playoffs']:.0%}  bye {o['bye']:.0%}  title {o['title']:.0%}  exp wins {o['exp_wins']:.1f}")
    print("Jack vs", out["jack_opp"], {k: ({a: f"{b:.0%}" for a, b in v.items()} if v else None) for k, v in out["jack_if"].items()})


if __name__ == "__main__":
    main()
