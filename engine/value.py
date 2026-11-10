#!/usr/bin/env python3
"""Player values for trades, Lock-In aware. No curve is fitted to trades (this league has made none, and fitting
to "the most balanced past trades" gives a flat, useless curve).

Two numbers per player:
  ours   = rest-of-season Lock-In value over replacement: each week's optimal-stopping value from the risk model
           (lock.chain over that week's games), playoff weeks x1.5, minus the best free agents' value.
  market = Sleeper ADP (adp_std, the price Sleeper's drafters paid), mapped rank-for-rank onto our scale,
           so "market" means "what a player drafted at that slot is worth on our scale".
A trade is judged by each team's best-lineup change summed over the remaining weeks (depth beyond the lineup
is worth little, so 2-for-1s are priced correctly without a package discount).

    value.py check                    ADP vs this league's own draft and vs results so far
    value.py board [--top N]          ours vs market, biggest gaps on rosters (buy-low / sell-high)
    value.py trade "A,B" "C"          Jack gives A,B and gets C (names, comma-separated); either team's view
"""
import argparse, datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N
import risk as R
import lock as K

PLAYOFF_WEIGHT = 1.5
DEFAULT_OUT_DAYS = 14   # an "Out" player with no known return date; set real dates in data/returns.json


def spearman(x, y):
    rk = lambda v: {i: r for r, i in enumerate(sorted(range(len(v)), key=lambda i: v[i]))}
    a, b = rk(x), rk(y)
    return N.corr([a[i] for i in range(len(x))], [b[i] for i in range(len(y))])


class Values:
    def __init__(self, L, today=None):
        self.L, self.today = L, today or dt.date.today().isoformat()
        self.M = R.Model(L, R.load_params())
        self.Rq = K.ratios(L, self.M, self.today)
        self.w0 = N.week_of(self.today)
        st = L.lg["settings"]
        self.last = st.get("playoff_week_start", 22) + 2
        self.pstart = st.get("playoff_week_start", 22)
        sched = N.load(f"{L.d}/schedule.json") or {}
        self.gw = {}   # (team, week) -> games left (current week: only from today)
        for d, teams in sched.items():
            if d < self.today:
                continue
            for t in teams:
                k = (t, N.week_of(d))
                self.gw[k] = self.gw.get(k, 0) + 1
        sp = N.load(f"{L.d}/season_projections.json") or []
        self.adp = {r["player_id"]: r["stats"]["adp_std"] for r in sp if (r.get("stats") or {}).get("adp_std", 999) < 400}
        self.season = {r["player_id"]: r["stats"] for r in sp if r.get("stats")}
        self.sp_team = {r["player_id"]: r.get("team") for r in sp}
        self.rostered = {p: r["roster_id"] for r in L.rosters for p in (r.get("players") or [])}
        # {"Anthony Edwards": "2026-11-24", ...} from injury news (nba-player-intel); beats the 14-day default
        ret = N.load(os.path.join(N.ROOT, "returns.json")) or {}
        self.returns = {pid: ret[L.pname(pid)] for pid in L.pinfo if L.pname(pid) in ret}
        self._wk = {}

    def weekly(self, pid):
        """{week: lock-in value} for the rest of the season"""
        if pid in self._wk:
            return self._wk[pid]
        L = self.L
        gl = self.M.games.get(pid)
        team = (L.pinfo.get(pid) or {}).get("team") or (gl[-1][1] if gl else None) or self.sp_team.get(pid)
        out = {}
        nxt = [d for d, _ in (gl or []) if d >= self.today]
        f = self.M.forecast(pid, self.today, nxt[0] if nxt else self.today, team,
                            (L.pinfo.get(pid) or {}).get("injury_status")) if gl else None
        if not f and pid in self.season:            # never projected this season (e.g. out since opening night):
            sf = L.fp(self.season[pid], expected=True)   # Sleeper's preseason per-game line, scaled like the model
            if sf > 0:
                f = (0.0, 0.0, sf * self.M.p.cal, sf)
        if f:
            # long-run availability: miss rate WITHOUT the current absence (an injury streak says when he is out,
            # not how often he misses once back), shrunk to the league prior
            h = self.M.history(pid, self.today) if gl else []
            streak = 0
            while streak < len(h) and not h[-1 - streak][4]:
                streak += 1
            hh = h[:len(h) - streak]
            p = self.M.p
            far = 1 - (sum(1 for x in hh if not x[4]) + p.a * p.prior) / (len(hh) + p.a)
            back = self.returns.get(pid)
            if not back and (L.pinfo.get(pid) or {}).get("injury_status") in ("Out", "IR") and streak:
                back = (dt.date.fromisoformat(self.today) + dt.timedelta(days=DEFAULT_OUT_DAYS)).isoformat()
            for w in range(self.w0, self.last + 1):
                n = self.gw.get((team, w), 0)
                if back and K.week_dates(w)[-1] < back:
                    continue
                if n:
                    q = f[1] if w == self.w0 and not back else far
                    out[w] = K.chain([(q, f[2])] * n, self.Rq)[1]
        self._wk[pid] = out
        return out

    def ros(self, pid):
        return sum(v * (PLAYOFF_WEIGHT if w >= self.pstart else 1) for w, v in self.weekly(pid).items())

    def lineup(self, ids):
        """sum over weeks of the best 9-slot lineup (each slot one Lock-In chance chain)"""
        tot = 0.0
        for w in range(self.w0, self.last + 1):
            vals = {p: self.weekly(p).get(w, 0.0) for p in ids}
            tot += best9(self.L, vals) * (PLAYOFF_WEIGHT if w >= self.pstart else 1)
        return tot

    def table(self):
        pool = [p for p in self.M.games if self.L.projected(p, max(d for d, _ in self.M.games[p])) > 0 or p in self.rostered]
        ours = {p: self.ros(p) for p in pool}
        fa = sorted((v for p, v in ours.items() if p not in self.rostered), reverse=True)
        repl = sum(fa[:3]) / 3 if len(fa) >= 3 else 0.0
        vor = {p: v - repl for p, v in ours.items()}
        order = sorted(vor.values(), reverse=True)
        mk = sorted((a, p) for p, a in self.adp.items())
        market = {p: order[i] if i < len(order) else order[-1] for i, (a, p) in enumerate(mk)}
        return vor, market, repl


def best9(L, vals):
    slots = ["C", "PG", "SG", "SF", "PF", "G", "F", "UTIL", "UTIL"]
    pl = sorted((p for p in vals if vals[p] > 0), key=lambda p: -vals[p])[:14]
    pos = {p: K.positions(L, p) for p in pl}
    best = [0.0]

    def dfs(k, used, s):
        if k == 9 or not pl:
            best[0] = max(best[0], s)
            return
        left = sorted((vals[p] for p in pl if p not in used), reverse=True)[:9 - k]
        if s + sum(left) <= best[0]:
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
    return best[0]


def find(L, name):
    name = name.strip().lower()
    hits = [p for p in L.pinfo if name in L.pname(p).lower()]
    if not hits:
        sys.exit(f"no player matching {name!r}")
    return min(hits, key=lambda p: len(L.pname(p)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "board", "trade"])
    ap.add_argument("give", nargs="?")
    ap.add_argument("get", nargs="?")
    ap.add_argument("--team", default="Jack")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    L = N.League()
    V = Values(L, a.today)
    if a.cmd == "check":
        picks = N.load(f"{L.d}/drafts/" + [f for f in os.listdir(f"{L.d}/drafts") if f.endswith("_picks.json")][0])
        both = [(x["pick_no"], V.adp[x["player_id"]]) for x in picks if x["player_id"] in V.adp]
        print(f"1. Sleeper ADP vs this league's own draft ({len(both)} picks): Spearman {spearman(*zip(*both)):.3f}")
        dev = sorted(((x["pick_no"] - V.adp[x["player_id"]], L.pname(x["player_id"]), L.name[x["roster_id"]], x["pick_no"], V.adp[x["player_id"]])
                      for x in picks if x["player_id"] in V.adp))
        print("   reached for (picked well before ADP):", "; ".join(f"{n} by {m} pick {p} (ADP {d:.0f})" for _, n, m, p, d in dev[:5]))
        print("   fell (picked well after ADP):", "; ".join(f"{n} to {m} pick {p} (ADP {d:.0f})" for _, n, m, p, d in dev[-5:][::-1]))
        # does the market (ADP) or our engine rank results so far better? per-game avg fantasy points to date
        avg = {}
        for (pid, d), r in L.act.items():
            if d < a.today and L.played(pid, d):
                avg.setdefault(pid, []).append(L.actual(pid, d))
        drafted = [x["player_id"] for x in picks if x["player_id"] in V.adp and len(avg.get(x["player_id"], [])) >= 5]
        res = [sum(avg[p]) / len(avg[p]) for p in drafted]
        print(f"2. drafted players with 5+ games ({len(drafted)}): rank agreement with points-per-game so far")
        print(f"   Sleeper ADP {spearman([-V.adp[p] for p in drafted], res):.3f}   this league's draft slot "
              f"{spearman([-[x['pick_no'] for x in picks if x['player_id'] == p][0] for p in drafted], res):.3f}")
        print("   (ADP is a preseason price, so it can't see this season's role changes; our engine values use them.)")
        adds = [t for w in range(1, 26) for t in (N.load(f"{L.d}/transactions/week_{w:02d}.json") or []) if t["status"] == "complete"]
        trades = [t for t in adds if t["type"] == "trade"]
        print(f"3. league trades so far: {len(trades)} -> nothing to calibrate on; values are not fitted to trades.")
        return
    vor, market, repl = V.table()
    if a.cmd == "board":
        print(f"replacement level (best 3 free agents) = {repl:.0f} rest-of-season lock-in points\n")
        print(f"{'player':24} {'team':6} {'ours':>6} {'market':>7} {'gap':>6}")
        drafted = {p for p, a in V.adp.items() if a <= 8 * 14 + 30}   # priced in drafts like this league's (8 x 14)
        rows = [(vor[p] - market[p], p) for p in vor if p in V.rostered and p in drafted]
        for title, sel in (("BUY (we value above market price)", sorted(rows, reverse=True)),
                           ("SELL (market pays more than we value)", sorted(rows))):
            print(title)
            for g, p in sel[:a.top]:
                inj = (L.pinfo.get(p) or {}).get("injury_status") or ""
                print(f"  {L.pname(p):24} {L.name[V.rostered[p]]:6} {vor[p]:6.0f} {market[p]:7.0f} {g:+6.0f}  {inj}")
        return
    me = [r for r in L.rosters if L.name[r["roster_id"]].lower() == a.team.lower()][0]
    give = [find(L, x) for x in a.give.split(",")]
    get = [find(L, x) for x in a.get.split(",")]
    them = {V.rostered.get(p) for p in get} - {None}
    mine = [p for p in me["players"] if p not in (me.get("reserve") or [])]
    d_me = V.lineup([p for p in mine if p not in give] + get) - V.lineup(mine)
    print(f"{a.team} gives {', '.join(map(L.pname, give))}  gets {', '.join(map(L.pname, get))}")
    print(f"  {a.team}: rest-of-season lineup {d_me:+.0f} pts")
    for rid in them:
        r = [x for x in L.rosters if x["roster_id"] == rid][0]
        ids = [p for p in r["players"] if p not in (r.get("reserve") or [])]
        d = V.lineup([p for p in ids if p not in get] + give) - V.lineup(ids)
        print(f"  {L.name[rid]}: rest-of-season lineup {d:+.0f} pts")
    print("  single-player values (ours / market):", ", ".join(f"{L.pname(p)} {vor.get(p, 0):.0f}/{market.get(p, 0):.0f}" for p in give + get))


if __name__ == "__main__":
    main()
