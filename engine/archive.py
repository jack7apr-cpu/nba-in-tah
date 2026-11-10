#!/usr/bin/env python3
"""Daily snapshot of injury feeds and forward projections so the injury priors can be replayed later.

    archive.py --live site/data/live.json [--data data]

Writes data/injuries/YYYY-MM-DD_HH.json (ESPN + Sleeper tags for every rostered player) and
data/proj_snapshots/YYYY-MM-DD_HH.json (slim per-game projections for the current week).
"""
import argparse, datetime as dt, json, os

KEEP = ("pts", "reb", "ast", "stl", "blk", "to", "tpm", "dd", "td", "sp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="site/data/live.json")
    ap.add_argument("--data", default="data")
    a = ap.parse_args()
    d = json.load(open(a.live))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H")
    rostered = {p for r in d["rosters"] for p in (r.get("players") or [])}
    inj = {"at": d["updated"], "espn": d["espn_injuries"],
           "sleeper": {pid: {"name": p["name"], "team": p["team"], "status": p["inj"], "note": p["inj_note"]}
                       for pid, p in d["players"].items() if pid in rostered and p.get("inj")}}
    proj = [{"pid": r["pid"], "date": r["date"], "opp": r["opp"], **{k: r["stats"].get(k) for k in KEEP}} for r in d.get("proj", [])]
    for sub, obj in (("injuries", inj), ("proj_snapshots", {"at": d["updated"], "week": d["state"]["week"], "rows": proj})):
        os.makedirs(f"{a.data}/{sub}", exist_ok=True)
        json.dump(obj, open(f"{a.data}/{sub}/{stamp}.json", "w"), separators=(",", ":"))
    print(f"archived {stamp}: {len(inj['espn'])} ESPN tags, {len(inj['sleeper'])} Sleeper tags, {len(proj)} projection rows")


if __name__ == "__main__":
    main()
