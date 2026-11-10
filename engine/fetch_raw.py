#!/usr/bin/env python3
"""Refresh the raw Sleeper files the Opus engine reads (data/<season>/...), stdlib only.

    fetch_raw.py [--data data]

Writes league, users, rosters, matchups (all weeks so far) and projections + stats for the current
and previous week (older weeks are final and stay as committed). Rows keep Sleeper's raw shape.
"""
import argparse, json, os, sys, time, urllib.request

LEAGUE = os.environ.get("LEAGUE_ID", "1410748359358099456")
POS = "&".join(f"position[]={p}" for p in ("PG", "SG", "SF", "PF", "C"))


def get(url):
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nba-in-tah/1.0"}), timeout=60))
        except Exception:
            if i == 2:
                raise
            time.sleep(3 * (i + 1))


def put(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    a = ap.parse_args()
    st = get("https://api.sleeper.app/v1/state/nba")
    season, week = st["season"], st["week"]
    d = f"{a.data}/{season}"
    put(f"{a.data}/state.json", st)
    put(f"{d}/league.json", get(f"https://api.sleeper.app/v1/league/{LEAGUE}"))
    put(f"{d}/users.json", get(f"https://api.sleeper.app/v1/league/{LEAGUE}/users"))
    put(f"{d}/rosters.json", get(f"https://api.sleeper.app/v1/league/{LEAGUE}/rosters"))
    for w in range(1, week + 1):
        put(f"{d}/matchups/week_{w:02d}.json", get(f"https://api.sleeper.app/v1/league/{LEAGUE}/matchups/{w}"))
    for w in sorted({max(1, week - 1), week}):
        for kind in ("projections", "stats"):
            rows = get(f"https://api.sleeper.com/{kind}/nba/{season}/{w}?season_type=regular&{POS}")
            put(f"{d}/{kind}/week_{w:02d}.json", rows)
    print(f"refreshed {season} week {week}")


if __name__ == "__main__":
    sys.exit(main())
