#!/usr/bin/env python3
"""Collect everything the site needs into data/live.json (stdlib only, no logins).

    collect.py [--out data/live.json]

Sources: Sleeper (league, rosters, matchups, transactions, per-game projections, weekly stats),
ESPN (injuries, 7-day scoreboard schedule). Each source is fetched independently; a failure is
recorded under "errors" and the old value is kept, so the page can show a stale-data warning.
"""
import argparse, datetime as dt, json, os, sys, time, urllib.request

LEAGUE = os.environ.get("LEAGUE_ID", "1410748359358099456")
ME = "jackhill1617"
POS = "&".join(f"position[]={p}" for p in ("PG", "SG", "SF", "PF", "C"))
UA = {"User-Agent": "nba-in-tah/1.0"}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def slim_player(p):
    return {"name": p.get("full_name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
            "team": p.get("team"), "pos": p.get("fantasy_positions") or [p.get("position")],
            "inj": p.get("injury_status"), "inj_note": p.get("injury_notes")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/live.json")
    a = ap.parse_args()
    old = json.load(open(a.out)) if os.path.exists(a.out) else {}
    out, err = dict(old), {}

    def run(key, fn):
        try:
            out[key] = fn()
        except Exception as e:
            err[key] = f"{type(e).__name__}: {e}"

    run("state", lambda: get("https://api.sleeper.app/v1/state/nba"))
    week = (out.get("state") or {}).get("week", 1)
    run("league", lambda: get(f"https://api.sleeper.app/v1/league/{LEAGUE}"))
    run("users", lambda: get(f"https://api.sleeper.app/v1/league/{LEAGUE}/users"))
    run("rosters", lambda: get(f"https://api.sleeper.app/v1/league/{LEAGUE}/rosters"))
    run("matchups", lambda: {str(w): get(f"https://api.sleeper.app/v1/league/{LEAGUE}/matchups/{w}") for w in range(1, week + 1)})
    run("transactions", lambda: {str(w): get(f"https://api.sleeper.app/v1/league/{LEAGUE}/transactions/{w}") for w in range(1, week + 1)})
    run("trending", lambda: get("https://api.sleeper.app/v1/players/nba/trending/add?lookback_hours=24&limit=25"))

    run("proj", lambda: [{"pid": r["player_id"], "date": r["date"], "team": r.get("team"), "opp": r.get("opponent"), "stats": r["stats"]}
                         for r in get(f"https://api.sleeper.com/projections/nba/{out['state']['season']}/{week}?season_type=regular&{POS}")
                         if r.get("stats") and r.get("player_id")])
    # rebuild the players table from the freshest rosters + projections
    try:
        db = get("https://api.sleeper.app/v1/players/nba")
        need = {p for r in out.get("rosters", []) for p in (r.get("players") or [])}
        need |= {str(r["player_id"]) for r in out.get("trending", [])}
        need |= {str(r["pid"]) for r in out.get("proj", [])}
        out["players"] = {pid: slim_player(db[pid]) for pid in need if pid in db}
    except Exception as e:
        err["players"] = f"{type(e).__name__}: {e}"

    run("stats", lambda: {str(w): [{"pid": r["player_id"], "date": r["date"], "stats": r["stats"]}
                                   for r in get(f"https://api.sleeper.com/stats/nba/{out['state']['season']}/{w}?season_type=regular&{POS}")
                                   if r.get("stats") and r.get("player_id")]
                          for w in range(1, week + 1)})
    run("espn_injuries", lambda: [{"team": t["displayName"], "player": i["athlete"]["displayName"], "status": i["status"], "note": i.get("shortComment"), "date": i.get("date")}
                                  for t in get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries")["injuries"] for i in t["injuries"]])

    def schedule():
        today = dt.date.today()
        rows = []
        for d in range(0, 8):
            day = (today + dt.timedelta(days=d)).strftime("%Y%m%d")
            for ev in get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day}")["events"]:
                comp = ev["competitions"][0]
                rows.append({"date": ev["date"], "name": ev["name"], "status": ev["status"]["type"]["name"],
                             "teams": [c["team"]["abbreviation"] for c in comp["competitors"]]})
        return rows
    run("schedule", schedule)

    out["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["errors"] = err
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w"), separators=(",", ":"))
    print(f"wrote {a.out} ({os.path.getsize(a.out)//1024} KB), week {week}, errors: {err or 'none'}")
    return 1 if len(err) > 3 else 0


if __name__ == "__main__":
    sys.exit(main())
