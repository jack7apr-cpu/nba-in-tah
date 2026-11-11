#!/usr/bin/env python3
"""Bootstrap simulation of add/drop moves under Lock-In scoring, using each player's OWN game log.

    sim_adds.py [--reps 150] [--adds "Wendell Carter,Kyshawn George,..."] [--drops "Jarrett Allen,Ace Bailey,..."]

For each replicate every player's game log is resampled; a player's weekly value with n games is the expected
best-of-n counted score from optimal stopping on that sample (so ceiling and number of chances matter, steady
players are not rewarded), with a 4% chance any game is a DNP. Each week's team value is the best 9-slot lineup;
the season total sums the remaining weeks (playoff weeks x1.5). A move's gain = total after - total before, measured
on the SAME resample, so the intervals reflect how much the answer depends on small samples.
Free rolls are not simulated (they would add value for players with games on idle nights).
"""
import argparse, datetime as dt, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, value as V, lock as K

DNP = 0.04


def log(L, p):
    return [L.actual(p, d) for (pid, d), r in L.act.items() if pid == p and r.get("stats") and r["stats"].get("min", 0) > 0]


def table(xs, nmax=5, dnp=DNP):
    """expected optimal-stopping value for n = 1..nmax chances; dnp = chance a game is missed (injury/rest)"""
    out, v = [0.0], sum(xs) / len(xs) * (1 - dnp)
    out.append(v)
    for _ in range(nmax - 1):
        v = sum(max(x, v) for x in xs) / len(xs) * (1 - dnp) + dnp * v
        out.append(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=150)
    ap.add_argument("--adds", default="Wendell Carter,Kyshawn George,Jalen Smith,Davion Mitchell,Nickeil Alexander,Brandin Podziemski,Day'Ron Sharpe")
    ap.add_argument("--drops", default="Jarrett Allen,Ace Bailey,Josh Giddey,Cedric Coward,P.J. Washington,Dejounte Murray")
    ap.add_argument("--team", default="Jack")
    ap.add_argument("--forecast", action="store_true", help="rescale each player's game log so its mean equals the engine's forward forecast (Sleeper projection blended with form)")
    ap.add_argument("--dnp", default="", help="per-player miss chance, e.g. \"Jalen Smith=0.08,Jarrett Allen=0.15\" (default 0.04 each)")
    ap.add_argument("--pairs", action="store_true", help="also test two adds + two drops at once")
    a = ap.parse_args()
    L = N.League()
    today = dt.date.today().isoformat()
    X = V.Values(L, today)
    rng = random.Random(11)
    find = lambda n: next(p for p in L.pinfo if n.lower() in L.pname(p).lower())
    me = next(k for k, v in L.name.items() if v == a.team)
    roster = [p for p, o in X.rostered.items() if o == me]
    adds, drops = [find(n) for n in a.adds.split(",")], [find(n) for n in a.drops.split(",")]
    pool = set(roster) | set(adds)
    miss = {find(k.split('=')[0]): float(k.split('=')[1]) for k in a.dnp.split(',') if '=' in k}
    logs = {p: log(L, p) for p in pool}
    if a.forecast:
        import risk as R
        Mo = R.Model(L, R.load_params())
        for p in pool:
            nxt = [d for d, _ in Mo.games.get(p, ()) if d >= today][:4]
            fc = [Mo.forecast(p, today, d, (L.pinfo.get(p) or {}).get("team"), (L.pinfo.get(p) or {}).get("injury_status")) for d in nxt]
            fc = [f[2] for f in fc if f and f[2] > 0]
            if fc and logs[p] and sum(logs[p]) > 0:
                k = (sum(fc) / len(fc)) / (sum(logs[p]) / len(logs[p]))
                logs[p] = [x * k for x in logs[p]]
    team = {p: (L.pinfo.get(p) or {}).get("team") for p in pool}
    pos = {p: K.positions(L, p) for p in pool}
    weeks = list(range(X.w0, X.last + 1))
    wt = {w: (V.PLAYOFF_WEIGHT if w >= X.pstart else 1.0) for w in weeks}
    scen = {"now": roster}
    for f in adds:
        for d in drops:
            scen[(f, d)] = [p for p in roster if p != d] + [f]
    if a.pairs:
        import itertools
        dl = [d for d in drops if L.pname(d) in ("Jarrett Allen", "Ace Bailey", "Josh Giddey", "Cedric Coward")]
        for f1, f2 in itertools.combinations(adds, 2):
            for d1, d2 in itertools.permutations(dl, 2):
                scen[((f1, f2), (d1, d2))] = [p for p in roster if p not in (d1, d2)] + [f1, f2]
    gains = {k: [] for k in scen if k != "now"}
    wk_gain = {k: [] for k in scen if k != "now"}
    for _ in range(a.reps):
        tabs = {p: table([rng.choice(logs[p]) for _ in logs[p]] if len(logs[p]) >= 4 else [20.0], 5, miss.get(p, DNP)) for p in pool}
        tot = {}
        for k, ids in scen.items():
            t = w0 = 0.0
            for w in weeks:
                vals = {p: tabs[p][min(X.gw.get((team[p], w), 0), 4)] for p in ids}
                b = V.best9(L, vals) if False else best(L, vals, pos)
                t += b * wt[w]
                if w == X.w0:
                    w0 = b
            tot[k] = (t, w0)
        for k in gains:
            gains[k].append(tot[k][0] - tot["now"][0])
            wk_gain[k].append(tot[k][1] - tot["now"][1])
    rows = []
    for k, g in gains.items():
        g.sort()
        nm = lambda x: " + ".join(L.pname(i) for i in x) if isinstance(x, tuple) else L.pname(x)
        rows.append((statistics.mean(g), g[int(.05 * len(g))], g[int(.95 * len(g))], sum(x > 0 for x in g) / len(g), statistics.mean(wk_gain[k]), nm(k[0]), nm(k[1]), statistics.median(g)))
    rows.sort(reverse=True)
    print(f"{a.reps} resamples, week {X.w0}-{X.last}; gain = points to season end vs the current roster\n")
    print(f"{'ADD':34}{'DROP':30}{'mean':>7}{'5%':>7}{'95%':>7}{'P(>0)':>8}{'this wk':>9}")
    for m, lo, hi, p, wk, fa, dr, med in rows[:18]:
        print(f"{fa:34}{dr:30}{m:7.1f}{lo:7.1f}{hi:7.1f}{p:8.0%}{wk:9.1f}  median {med:5.1f}")
    print("\nbest drop for each add:")
    seen = set()
    for m, lo, hi, p, wk, fa, dr, med in rows:
        if fa not in seen and " + " not in fa:
            seen.add(fa)
            print(f"  {fa:24} drop {dr:18} {m:+6.1f}  ({lo:+.0f} to {hi:+.0f}, {p:.0%} positive)")


def best(L, vals, pos):
    slots = ["C", "PG", "SG", "SF", "PF", "G", "F", "UTIL", "UTIL"]
    pl = sorted((p for p in vals if vals[p] > 0), key=lambda p: -vals[p])[:14]
    top = [0.0]

    def dfs(k, used, s):
        if k == 9 or not pl:
            top[0] = max(top[0], s)
            return
        left = sorted((vals[p] for p in pl if p not in used), reverse=True)[:9 - k]
        if s + sum(left) <= top[0]:
            return
        placed = False
        for p in pl:
            if p not in used and pos[p] & K.OK[slots[k]]:
                placed = True
                used.add(p)
                dfs(k + 1, used, s + vals[p])
                used.discard(p)
        if not placed:
            dfs(k + 1, used, s)
    dfs(0, set(), 0.0)
    return top[0]


if __name__ == "__main__":
    main()
