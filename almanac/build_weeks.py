#!/usr/bin/env python3
"""Turn Sleeper matchups in live.json into site/data/weeks_auto.json (no screenshots needed).

    build_weeks.py --live site/data/live.json --out site/data/weeks_auto.json

Per week: matchups with counted totals, slot-by-slot counted scores (starters_points in
lineup-slot order), and a status of 'final' for past weeks or 'live' for the current week.
Curated weeks in league_data.json (with Isaac's recap and awards) take priority on the site;
this fills in every other week and the live week automatically.
"""
import argparse, json, sys

NAMES = {"jackhill1617": "Jack", "kingboo25": "Kyran", "idbh": "Isaac", "lmlewis": "Lewis", "matttallguy": "Matt",
         "maxcmaples": "Maxi", "vpiggz": "David", "donghyuk101301": "Tony"}
SLOTS = ["PG", "SG", "G", "SF", "PF", "F", "C", "UTIL", "UTIL"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="site/data/live.json")
    ap.add_argument("--out", default="site/data/weeks_auto.json")
    a = ap.parse_args()
    d = json.load(open(a.live))
    uname = {u["user_id"]: NAMES.get(u["display_name"].lower(), u["display_name"]) for u in d["users"]}
    rname = {r["roster_id"]: uname.get(r["owner_id"], f"Team {r['roster_id']}") for r in d["rosters"]}
    cur = d["state"]["week"]
    out = {}
    for w, rows in d["matchups"].items():
        games = {}
        for r in rows:
            games.setdefault(r["matchup_id"], []).append(r)
        ms = []
        for pair in games.values():
            if len(pair) != 2:
                continue
            side = lambda r: {"mgr": rname[r["roster_id"]], "pts": round(sum(r["starters_points"] or []), 1),
                              "slots": [[SLOTS[i] if i < 9 else "BN", d["players"].get(p, {}).get("name", p), s]
                                        for i, (p, s) in enumerate(zip(r["starters"], r["starters_points"]))]}
            ms.append([side(pair[0]), side(pair[1])])
        out[w] = {"status": "live" if int(w) >= cur else "final", "matchups": ms}
    json.dump(out, open(a.out, "w"), separators=(",", ":"))
    L = json.load(open("site/data/league_data.json"))["weeks"]
    bad = 0
    for w, cw in L.items():
        for a1, pa, b1, pb in cw["matchups"]:
            for ms in out.get(w, {}).get("matchups", []):
                got = {m["mgr"]: m["pts"] for m in ms}
                if a1 in got and abs(got[a1] - pa) > 0.5:
                    bad += 1
                    print(f"week {w} {a1}: curated {pa} vs Sleeper {got[a1]}")
    print(f"wrote {a.out}: weeks {sorted(out)}; mismatches vs curated: {bad}")


if __name__ == "__main__":
    sys.exit(main())
