#!/usr/bin/env python3
"""Crystal Ball: Monte Carlo of the rest of the season. Playoff, seed and title odds for all teams.
    crystal.py [--sims N] [--team ID]
Team strength = blend of the engine's projected best lineup (healthy-adjusted) and points actually scored; weekly spread from each team's own history.
Schedule comes from Sleeper (future matchups are published); bracket shape follows Sleeper's: 1v8, 4v5, 2v7, 3v6 then a re-paired semi and final."""
import argparse, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(__file__))
import engine as e
import sleeper as S


def setup(c):
    """schedule, base records, and each team's weekly mean/sd (shared by the simulation and the almanac)."""
    lid = c.lg["league_id"]
    last_reg = c.playoff_start - 1
    reg_weeks = list(range(c.week, last_reg + 1))
    sched = {}
    for w in reg_weeks:
        m = S.load(f"{c.d}/matchups/week_{w:02d}.json") or S.api(f"/league/{lid}/matchups/{w}") or []
        g = {}
        for x in m:
            g.setdefault(x["matchup_id"], []).append(x["roster_id"])
        sched[w] = [tuple(v) for v in g.values() if len(v) == 2]
    ids = [r["roster_id"] for r in c.rosters]
    hist = {rid: [] for rid in ids}
    for w in range(1, c.week):
        for x in S.load(f"{c.d}/matchups/week_{w:02d}.json") or []:
            if x.get("points"):
                hist[x["roster_id"]].append(x["points"])
    base = {r["roster_id"]: (r["settings"].get("wins", 0), S.fpts(r["settings"])) for r in c.rosters}
    roster = {r["roster_id"]: r for r in c.rosters}
    mu, sd = {}, {}
    for rid in ids:
        h = hist[rid]
        avg = statistics.mean(h) if h else 100
        sd[rid] = max(15.0, statistics.pstdev(h)) if len(h) > 2 else 20.0
        for w in range(c.week, 18):
            proj = sum(x[2] for x in c.best_lineup(e.active(roster[rid]), w))
            mu[rid, w] = 0.5 * proj + 0.5 * avg if proj > 40 else avg  # no projection (bye-ish week) -> his average
    return reg_weeks, last_reg, sched, ids, base, mu, sd


def simulate(c, sims=20000, seed=7):
    reg_weeks, last_reg, sched, ids, base, mu, sd = setup(c)
    rng = random.Random(seed)
    seeds_n = c.lg["settings"].get("playoff_teams", 8)
    made = {rid: 0 for rid in ids}; title = dict(made); final = dict(made); seed_sum = dict(made)
    for _ in range(sims):
        wins = {rid: base[rid][0] for rid in ids}; pf = {rid: base[rid][1] for rid in ids}
        for w in reg_weeks:
            sc = {rid: rng.gauss(mu[rid, w], sd[rid]) for rid in ids}
            for a, b in sched[w]:
                wins[a if sc[a] > sc[b] else b] += 1
            for rid in ids:
                pf[rid] += sc[rid]
        order = sorted(ids, key=lambda r: (-wins[r], -pf[r]))[:seeds_n]
        for i, rid in enumerate(order):
            made[rid] += 1; seed_sum[rid] += i + 1
        def play(a, b, w):
            return a if rng.gauss(mu[a, w], sd[a]) > rng.gauss(mu[b, w], sd[b]) else b
        s = order
        w1 = [play(s[0], s[7], last_reg + 1), play(s[3], s[4], last_reg + 1), play(s[1], s[6], last_reg + 1), play(s[2], s[5], last_reg + 1)]
        w2 = [play(w1[0], w1[1], last_reg + 2), play(w1[2], w1[3], last_reg + 2)]
        champ = play(w2[0], w2[1], last_reg + 3)
        for rid in w2:
            final[rid] += 1
        title[champ] += 1
    return [{"id": rid, "team": c.owner[rid], "w": base[rid][0], "playoffs": made[rid] / sims, "avg_seed": seed_sum[rid] / made[rid] if made[rid] else None,
             "final": final[rid] / sims, "title": title[rid] / sims} for rid in ids]


def table(rows, me=None):
    out = [f"{'team':28} {'W':>2} {'playoffs':>9} {'avg seed':>8} {'final':>6} {'title':>6}"]
    for r in sorted(rows, key=lambda r: -r["title"] - r["playoffs"] * 0.01):
        mark = " <--" if me and r["id"] == me else ""
        out.append(f"{r['team'][:28]:28} {r['w']:>2} {r['playoffs']:>8.0%} {r['avg_seed'] or 0:>8.1f} {r['final']:>6.0%} {r['title']:>6.1%}{mark}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=20000)
    ap.add_argument("--team", default="10")
    ap.add_argument("--data", default="./data")
    a = ap.parse_args()
    c = e.Ctx(a.data)
    print(f"Crystal Ball, week {c.week}, {a.sims} simulations, top {c.lg['settings'].get('playoff_teams')} make it")
    print(table(simulate(c, a.sims), c.team(a.team)["roster_id"]))


if __name__ == "__main__":
    main()
