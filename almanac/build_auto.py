#!/usr/bin/env python3
"""Rebuild the data-driven almanac tabs from fresh Sleeper data (no screenshots needed).

    build_auto.py --live site/data/live.json --facts site/data/factfile.json --out site/data/auto.json

players: every rostered player's season line (games, avg, last 3, best, worst, sd, 30+/15- rates) in this
league's scoring, with owner, injury tag and the lock stats carried over from the curated factfile.
fa: every completed add (waiver or free agent) with what the player scored since, vs the player dropped.
Lock-level detail (what each manager locked, points left on the bench) still comes from the weekly screenshots.
"""
import argparse, datetime as dt, json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import nbadata as N

NAMES = {"jackhill1617": "Jack", "kingboo25": "Kyran", "idbh": "Isaac", "lmlewis": "Lewis", "matttallguy": "Matt",
         "maxcmaples": "Maxi", "vpiggz": "David", "donghyuk101301": "Tony"}


def tier(avg, sd):
    base = "Superstar" if avg >= 30 else "Star" if avg >= 24 else "Solid starter" if avg >= 19 else "Depth"
    return base + (" · steady" if sd <= 7 else " · boom/bust" if sd >= 11 else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="site/data/live.json")
    ap.add_argument("--facts", default="site/data/factfile.json")
    ap.add_argument("--out", default="site/data/auto.json")
    a = ap.parse_args()
    live, facts = json.load(open(a.live)), json.load(open(a.facts))
    L = N.League()
    users = {u["user_id"]: NAMES.get(u["display_name"].lower(), u["display_name"]) for u in live["users"]}
    rname = {r["roster_id"]: users[r["owner_id"]] for r in live["rosters"]}
    inj = {i["player"].lower(): i for i in live["espn_injuries"]}
    carry = {l["player"].lower(): [] for l in facts["locks"]}
    for l in facts["locks"]:
        carry[l["player"].lower()].append(l["locked"])
    games = {}
    for (pid, d), r in L.act.items():
        if r.get("stats") and r["stats"].get("min", 0) > 0:
            games.setdefault(pid, []).append((d, L.fp(r["stats"])))
    for g in games.values():
        g.sort()
    pl = []
    for r in live["rosters"]:
        for pid in r["players"]:
            g = [x[1] for x in games.get(pid, [])]
            if not g:
                continue
            info = live["players"].get(pid, {})
            avg = sum(g) / len(g)
            sd = math.sqrt(sum((x - avg) ** 2 for x in g) / max(1, len(g) - 1))
            name = L.pname(pid)
            lk = carry.get(name.lower(), [])
            e = inj.get(name.lower())
            tag = (e or {}).get("status") or info.get("inj") or ""
            pl.append({"owner": rname[r["roster_id"]], "player": name, "pos": "/".join(info.get("pos") or []), "team": info.get("team"),
                       "gp": len(g), "avg": round(avg, 1), "sd": round(sd, 1), "max": max(g), "min": min(g),
                       "l3": round(sum(g[-3:]) / len(g[-3:]), 1), "p30": round(100 * sum(x >= 30 for x in g) / len(g)),
                       "p15": round(100 * sum(x < 15 for x in g) / len(g)), "nlocks": len(lk),
                       "lockavg": round(sum(lk) / len(lk), 1) if lk else 0, "ir": pid in (r.get("reserve") or []),
                       "inj": (tag + " — " + (e or {}).get("note", "")) if e else (tag or ""), "tier": tier(avg, sd)})
    pl.sort(key=lambda x: -x["avg"])
    fa = []
    for w, txs in sorted(live["transactions"].items(), key=lambda x: int(x[0])):
        for t in txs:
            if t.get("status") != "complete" or t["type"] not in ("waiver", "free_agent"):
                continue
            day = dt.datetime.fromtimestamp(t["created"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
            for pid, rid in (t.get("adds") or {}).items():
                since = [p for d, p in games.get(pid, []) if d >= day]
                drop = next((d for d, r2 in (t.get("drops") or {}).items() if r2 == rid), None)
                dsince = [p for d, p in games.get(drop, []) if d >= day] if drop else []
                av = round(sum(since) / len(since), 1) if since else None
                dv = round(sum(dsince) / len(dsince), 1) if dsince else None
                fa.append({"wk": int(w), "date": day.replace("-", ""), "mgr": rname.get(rid, "?"), "add": L.pname(pid), "addavg": av or 0,
                           "addgp": len(since), "addmax": max(since) if since else None, "drop": L.pname(drop) if drop else "",
                           "dropavg": dv, "gain": round(av - dv, 1) if av is not None and dv is not None else None})
    json.dump({"updated": live["updated"], "players": pl, "fa": fa}, open(a.out, "w"), separators=(",", ":"))
    print(f"players {len(pl)}, adds {len(fa)}")


if __name__ == "__main__":
    main()
