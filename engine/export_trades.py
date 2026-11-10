#!/usr/bin/env python3
"""Export the trade board and win-win trade ideas for the website.

    export_trades.py [--team Jack] [--out site/data/trades.json]

board: every rostered player (+ best free agents) with our rest-of-season value over replacement,
the market value (Sleeper ADP mapped onto the same scale) and the gap.
ideas: 1-for-1, 2-for-1 and 1-for-2 swaps where BOTH lineups improve over the remaining weeks
(that is our proxy for "the other manager would say yes"), ranked by the user's gain.
"""
import argparse, datetime as dt, itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, value as V


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="Jack")
    ap.add_argument("--out", default="site/data/trades.json")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    L = N.League()
    X = V.Values(L, a.today)
    vor, market, repl = X.table()
    rid = {v: k for k, v in L.name.items()}
    me = rid[a.team]
    roster = {r: [p for p, o in X.rostered.items() if o == r] for r in L.name}
    board = []
    for p in vor:
        owner = L.name.get(X.rostered.get(p), "FA")
        if owner == "FA" and vor[p] < 40:
            continue
        info = L.pinfo.get(p) or {}
        board.append({"id": p, "name": L.pname(p), "owner": owner, "pos": info.get("fantasy_positions") or [], "team": info.get("team"),
                      "inj": info.get("injury_status"), "ours": round(vor[p]), "market": round(market.get(p, 0)), "gap": round(vor[p] - market.get(p, 0))})
    board.sort(key=lambda b: -b["ours"])
    base = {r: X.lineup(ids) for r, ids in roster.items()}
    ideas = []
    for other, theirs in roster.items():
        if other == me:
            continue
        for ng, nt in ((1, 1), (2, 1), (1, 2)):
            for give in itertools.combinations(roster[me], ng):
                for get in itertools.combinations(theirs, nt):
                    gv, tv = sum(vor.get(p, 0) for p in give), sum(vor.get(p, 0) for p in get)
                    if tv < 0.6 * gv and ng == nt or tv < 30:
                        continue
                    mine = X.lineup([p for p in roster[me] if p not in give] + list(get)) - base[me]
                    if mine < 15:
                        continue
                    their = X.lineup([p for p in theirs if p not in get] + list(give)) - base[other]
                    if their <= 0:
                        continue
                    ideas.append({"with": L.name[other], "give": [L.pname(p) for p in give], "get": [L.pname(p) for p in get],
                                  "me": round(mine), "them": round(their)})
    ideas.sort(key=lambda i: -i["me"])
    per, top = {}, []
    for i in ideas:
        if per.get(i["with"], 0) < 4:
            per[i["with"]] = per.get(i["with"], 0) + 1
            top.append(i)
    needs = {}
    for r, ids in roster.items():
        c = [p for p in ids if "C" in (L.pinfo.get(p) or {}).get("fantasy_positions", [])]
        needs[L.name[r]] = {"centers": len(c)}
    json.dump({"team": a.team, "today": a.today, "replacement": round(repl), "board": board[:150], "ideas": top[:40], "needs": needs,
               "note": "Values are rest-of-season Lock-In points above a free-agent replacement, playoff weeks x1.5. Market = Sleeper ADP mapped onto the same scale. The league has made no trades yet, so nothing is fitted to trades."},
              open(a.out, "w"), separators=(",", ":"))
    print(f"board {len(board)}, ideas {len(ideas)} (kept {len(top)})")
    for i in top[:6]:
        print(f"  with {i['with']:6} give {', '.join(i['give'])} get {', '.join(i['get'])}  me {i['me']:+d} them {i['them']:+d}")


if __name__ == "__main__":
    main()
