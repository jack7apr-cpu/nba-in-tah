#!/usr/bin/env python3
"""Official weekly totals from Sleeper's cumulative season points (roster fpts).

    official_weeks.py --live /tmp/live.json --facts site/data/factfile.json --out site/data/official.json

Sleeper's matchup endpoint does not give Lock-In counted scores, but each roster's season total (fpts)
matches the official numbers exactly (checked against weeks 1-3). It only moves when a week settles, so
week K's official team total = fpts after K games minus the official totals of weeks 1..K-1.
Seeded from the curated weeks in factfile.json (screenshots); extended automatically after each week.
"""
import argparse, json, os, sys

NAMES = {"jackhill1617": "Jack", "kingboo25": "Kyran", "idbh": "Isaac", "lmlewis": "Lewis", "matttallguy": "Matt",
         "maxcmaples": "Maxi", "vpiggz": "David", "donghyuk101301": "Tony"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="/tmp/live.json")
    ap.add_argument("--facts", default="site/data/factfile.json")
    ap.add_argument("--out", default="site/data/official.json")
    a = ap.parse_args()
    live = json.load(open(a.live))
    users = {u["user_id"]: NAMES.get(u["display_name"].lower(), u["display_name"]) for u in live["users"]}
    cur, plays = {}, set()
    for r in live["rosters"]:
        s = r["settings"]
        cur[users[r["owner_id"]]] = s["fpts"] + s.get("fpts_decimal", 0) / 100
        plays.add(s["wins"] + s["losses"] + s.get("ties", 0))
    K = min(plays)
    out = json.load(open(a.out)) if os.path.exists(a.out) else {"weeks": {}}
    if not out["weeks"]:
        for w, ms in json.load(open(a.facts))["MU"].items():
            out["weeks"][w] = {}
            for x, px, y, py in ms:
                out["weeks"][w][x.replace(" (GPT)", "")] = px
                out["weeks"][w][y.replace(" (GPT)", "")] = py
    new = []
    for w in range(1, K + 1):
        if str(w) in out["weeks"]:
            continue
        if w != K or not all(str(i) in out["weeks"] for i in range(1, w)):
            print(f"cannot separate week {w} (settled weeks {K}); needs a manual entry", file=sys.stderr)
            continue
        prior = {m: sum(out["weeks"][str(i)].get(m, 0) for i in range(1, w)) for m in cur}
        out["weeks"][str(w)] = {m: round(cur[m] - prior[m], 1) for m in cur}
        new.append(w)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"settled weeks {K}; recorded {sorted(map(int, out['weeks']))}; new {new}")


if __name__ == "__main__":
    main()
