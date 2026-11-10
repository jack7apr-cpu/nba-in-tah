#!/usr/bin/env python3
"""Export per-player weekly Lock-In values so the website can judge ANY trade between ANY two teams.

    export_values.py [--out site/data/values.json]

Every rostered player: owner, eligible positions, injury tag, market (ADP-scaled) and rest-of-season value, and
his expected Lock-In value for each remaining week (the same numbers value.py uses). The page runs the same
best-9-lineup search in JavaScript, so a trade's effect on each team's rest-of-season lineup is computed live.
"""
import argparse, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, value as V, lock as K


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/values.json")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    L = N.League()
    X = V.Values(L, a.today)
    vor, market, repl = X.table()
    ret = N.load(os.path.join(N.ROOT, "returns.json")) or {}
    players = []
    for pid, rid in X.rostered.items():
        info = L.pinfo.get(pid) or {}
        wk = {str(w): round(v, 1) for w, v in X.weekly(pid).items()}
        players.append({"id": pid, "name": L.pname(pid), "owner": L.name[rid], "team": info.get("team"), "pos": sorted(K.positions(L, pid)),
                        "inj": info.get("injury_status"), "back": ret.get(L.pname(pid)), "ours": round(vor.get(pid, 0)),
                        "market": round(market.get(pid, 0)), "weeks": wk, "ir": pid in (next(r for r in L.rosters if r["roster_id"] == rid).get("reserve") or [])})
    players.sort(key=lambda p: -p["ours"])
    json.dump({"today": a.today, "w0": X.w0, "pstart": X.pstart, "last": X.last, "pw": V.PLAYOFF_WEIGHT, "teams": sorted(set(L.name.values())), "players": players,
               "note": "Values are expected Lock-In points per remaining week. Trade effect = change in each team's best 9-slot lineup summed to the end of the season (playoff weeks x1.5)."},
              open(a.out, "w"), separators=(",", ":"))
    print(f"{len(players)} players, weeks {X.w0}-{X.last}")
    # reference total for Jack so JS can be checked against Python
    me = [p for p, o in X.rostered.items() if L.name[o] == "Jack"]
    print("Jack lineup total", round(X.lineup(me), 2))


if __name__ == "__main__":
    main()
