#!/usr/bin/env python3
"""Free-agent pickups and the week's matchup picture, for the website.

    export_fa.py [--team Jack] [--out site/data/fa.json]

fa: best add/drop moves by rest-of-season lineup gain (Lock-In value, playoff weeks x1.5) and by this
week's gain alone (streamers for idle nights). matchup: your expected week vs your opponent's, a win
probability, and a lock stance (protect a lead / chase a deficit), a heuristic on top of the model.
"""
import argparse, datetime as dt, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, value as V

WEEK_SD = 24.0   # a team's weekly total sd from weeks 1-3, see crystal_nba.py


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="Jack")
    ap.add_argument("--out", default="site/data/fa.json")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    L = N.League()
    X = V.Values(L, a.today)
    vor, market, repl = X.table()
    rid = {v: k for k, v in L.name.items()}
    me = rid[a.team]
    mine = [p for p, o in X.rostered.items() if o == me]
    res = next(r for r in L.rosters if r["roster_id"] == me)
    active = [p for p in mine if p not in (res.get("reserve") or [])]
    base_all = X.lineup(mine)
    w0 = X.w0
    wk_of = lambda ids: V.best9(L, {p: X.weekly(p).get(w0, 0.0) for p in ids})
    base_wk = wk_of(mine)
    fas = sorted((p for p in vor if p not in X.rostered), key=lambda p: -vor[p])[:30]
    drops = sorted(active, key=lambda p: vor.get(p, 0))[:7]
    moves = []
    for f in fas:
        best = None
        for d in drops:
            ids = [p for p in mine if p != d] + [f]
            g_all, g_wk = X.lineup(ids) - base_all, wk_of(ids) - base_wk
            if best is None or g_all > best[0]:
                best = (g_all, g_wk, d)
        if best and (best[0] > 3 or best[1] > 3):
            info = L.pinfo.get(f) or {}
            moves.append({"add": L.pname(f), "pos": info.get("fantasy_positions") or [], "team": info.get("team"), "drop": L.pname(best[2]),
                          "ros": round(best[0]), "week": round(best[1]), "value": round(vor[f])})
    moves.sort(key=lambda m: -(m["ros"] + m["week"]))
    # matchup: expected week totals from the lock-in values of the current best lineups
    mm = {m["roster_id"]: m["matchup_id"] for m in (N.load(f"{L.d}/matchups/week_{w0:02d}.json") or [])}
    opp = next((r for r, mid in mm.items() if mid == mm.get(me) and r != me), None)
    out = {"team": a.team, "today": a.today, "week": w0, "fa": moves[:12], "matchup": None}
    if opp:
        # season-to-date picture: expected locked totals from the lock plan (banked scores + what is left)
        plan = N.load(os.path.join(os.path.dirname(a.out), "plan.json")) or {}
        mine_w = (plan.get("teams", {}).get(a.team) or {}).get("total")
        their_w = (plan.get("teams", {}).get(L.name[opp]) or {}).get("total")
        if mine_w is None or their_w is None:
            theirs = [p for p, o in X.rostered.items() if o == opp]
            mine_w, their_w = base_wk, wk_of(theirs)
        p_win = phi((mine_w - their_w) / (WEEK_SD * math.sqrt(2)))
        stance = ("Protect the lead: lock a good score instead of chasing a better one." if p_win > 0.65
                  else "Underdog: hold for ceilings, a safe score won't catch him." if p_win < 0.35
                  else "Close: follow the thresholds, no need to gamble either way.")
        out["matchup"] = {"opp": L.name[opp], "mine": round(mine_w, 1), "theirs": round(their_w, 1), "p_win": round(p_win, 3), "stance": stance}
    json.dump(out, open(a.out, "w"), separators=(",", ":"))
    print(f"{len(moves)} moves; matchup {out['matchup']}")
    for m in out["fa"][:6]:
        print(f"  add {m['add']:22} drop {m['drop']:20} ros {m['ros']:+d} week {m['week']:+d}")


if __name__ == "__main__":
    main()
