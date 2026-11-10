#!/usr/bin/env python3
"""Sleeper public API fetcher and offline query tool (standard library only, no login).

    sleeper.py fetch <league_id|username> [--sport nfl|nba] [--season YYYY]
    sleeper.py rules | standings | week N | roster TEAM | player NAME | transactions
    sleeper.py projections W | stats W        (needs `fetch` first; NFL)

Global options (before or after the command): --data DIR (default ./data), --season YYYY.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.sleeper.app/v1"
PROJ_API = "https://api.sleeper.com"
CACHE = os.path.expanduser("~/.cache/sleeper-api")
PLAYERS_TTL = 86400
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
MAX_WEEK = {"nfl": 18, "nba": 25}


class SleeperError(Exception):
    pass


# ---------- io ----------
def http_get(url, retries=4):
    """GET json. Returns None on 404; retries 429/5xx/network errors with backoff."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 sleeper-api-skill"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read() or "null")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504):
                raise SleeperError(f"HTTP {e.code} for {url}")
            last = e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
        time.sleep(2 ** i)
    raise SleeperError(f"giving up on {url}: {last}")


def api(path):
    return http_get(API + path)


def save(path, obj):
    """Atomic write: a crash mid-write never leaves a corrupt file."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def players_db(sport, refresh=False):
    p = os.path.join(CACHE, f"players_{sport}.json")
    stale = not os.path.exists(p) or time.time() - os.path.getmtime(p) > PLAYERS_TTL
    if refresh or stale:
        data = api(f"/players/{sport}")
        if not data:
            raise SleeperError("players download returned nothing")
        save(p, data)
    return load(p, {})


# ---------- pure helpers ----------
def norm(s):
    """lowercase, strip accents, punctuation and suffixes (Jr./III) for name matching."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", "", s)
    return " ".join(re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s).split())


def pname(p):
    return p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()


def match_players(db, query, limit=10):
    """Rank: exact name, then prefix, then substring; active players first."""
    q = norm(query)
    scored = []
    for pid, p in db.items():
        n = norm(pname(p))
        if not n:
            continue
        rank = 0 if n == q else 1 if n.startswith(q) or n.split()[-1:] == [q] else 2 if q in n else None
        if rank is not None:
            scored.append((rank, 0 if p.get("status") == "Active" else 1, n, pid))
    return [pid for *_, pid in sorted(scored)[:limit]]


def team_names(users, rosters):
    names = {u["user_id"]: (u.get("metadata") or {}).get("team_name") or u["display_name"] for u in users}
    return {r["roster_id"]: names.get(r["owner_id"], f"Roster {r['roster_id']}") for r in rosters}


def slot_counts(positions):
    out = {}
    for p in positions:
        out[p] = out.get(p, 0) + 1
    return out


def fpts(settings):
    return settings.get("fpts", 0) + settings.get("fpts_decimal", 0) / 100


WAIVER = {0: "rolling priority", 1: "reverse standings", 2: "FAAB"}
LEAGUE_TYPE = {0: "redraft", 1: "keeper", 2: "dynasty"}


def rules_rows(lg):
    s = lg["settings"]
    waiver = WAIVER.get(s.get("waiver_type"), s.get("waiver_type"))
    if s.get("waiver_type") == 2:
        waiver += f" ${s.get('waiver_budget')}"
    slots = slot_counts(lg["roster_positions"])
    return [
        ("League", f"{lg['name']} ({lg['season']}, {lg['status']})"),
        ("Teams", lg["total_rosters"]),
        ("Type", LEAGUE_TYPE.get(s.get("type"), s.get("type"))),
        ("Roster", ", ".join(f"{k}x{v}" for k, v in slots.items())),
        ("IR / Taxi", f"{s.get('reserve_slots')} IR, {s.get('taxi_slots')} taxi ({s.get('taxi_years')} yrs)"),
        ("Playoffs", f"{s.get('playoff_teams')} teams from week {s.get('playoff_week_start')}"),
        ("Waivers", f"{waiver}; clear day {s.get('waiver_day_of_week')}"),
        ("Trade deadline", f"week {s.get('trade_deadline')}"),
        ("Keepers/picks", f"max_keepers {s.get('max_keepers')}, pick trading {bool(s.get('pick_trading'))}"),
    ]


# ---------- fetch ----------
def resolve_league(ident, sport, season):
    if ident.isdigit() and len(ident) > 10:
        return ident
    user = api(f"/user/{ident}")
    if not user:
        raise SleeperError(f"no Sleeper user or league '{ident}'")
    season = season or api(f"/state/{sport}")["league_season"]
    leagues = api(f"/user/{user['user_id']}/leagues/{sport}/{season}") or []
    if len(leagues) != 1:
        lines = "\n".join(f"  {l['league_id']}  {l['name']} ({l['total_rosters']} teams)" for l in leagues)
        raise SleeperError(f"{ident} has {len(leagues)} {sport} leagues in {season}; re-run with a league_id:\n{lines}")
    return leagues[0]["league_id"]


def fetch_league(lid, data, state):
    lg = api(f"/league/{lid}")
    if not lg:
        raise SleeperError(f"league {lid} not found")
    sport, season = lg["sport"], lg["season"]
    d = os.path.join(data, season)
    save(f"{d}/league.json", lg)
    for name, path in [("users", "users"), ("rosters", "rosters"), ("winners_bracket", "winners_bracket"),
                       ("losers_bracket", "losers_bracket"), ("traded_picks", "traded_picks")]:
        save(f"{d}/{name}.json", api(f"/league/{lid}/{path}"))

    # every week that has started (or the whole past season); future weeks are empty
    cur_season, cur_week = state.get("league_season"), state.get("week") or 0
    last = MAX_WEEK[sport] if season != cur_season else min(MAX_WEEK[sport], max(cur_week, 1))
    weeks = range(1, last + 1)
    with ThreadPoolExecutor(8) as ex:
        matchups = list(ex.map(lambda w: api(f"/league/{lid}/matchups/{w}") or [], weeks))
        txns = list(ex.map(lambda w: api(f"/league/{lid}/transactions/{w}") or [], weeks))
    for w, m, t in zip(weeks, matchups, txns):
        if any(x.get("points") for x in m) or (m and season == cur_season and w == cur_week):
            save(f"{d}/matchups/week_{w:02d}.json", m)
        if t:
            save(f"{d}/transactions/week_{w:02d}.json", t)
    for dr in api(f"/league/{lid}/drafts") or []:
        save(f"{d}/drafts/{dr['draft_id']}.json", api(f"/draft/{dr['draft_id']}"))
        save(f"{d}/drafts/{dr['draft_id']}_picks.json", api(f"/draft/{dr['draft_id']}/picks"))
    print(f"saved {season} {lg['name']} -> {d}")
    return lg


def fetch_projections(data, season, cur_week, first=1, last=18):
    """NFL only: Sleeper's own weekly projections (remaining weeks) and stats (played weeks)."""
    pos = "&".join(f"position[]={p}" for p in POSITIONS)
    base = f"{PROJ_API}/%s/nfl/{season}/{{w}}?season_type=regular&{pos}"

    def one(kind, w):
        res = http_get(base.replace("%s", kind).format(w=w))
        if res:
            save(f"{data}/{season}/{kind}/week_{w:02d}.json", res)
    jobs = [("projections", w) for w in range(max(first, cur_week), last + 1)]
    jobs += [("stats", w) for w in range(first, cur_week + 1)]
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda j: one(*j), jobs))
    print(f"saved projections weeks {max(first, cur_week)}-{last}, stats weeks {first}-{cur_week}")


def cmd_fetch(a):
    sport = a.sport
    state = api(f"/state/{sport}")
    lid = resolve_league(a.target, sport, a.season)
    lg = fetch_league(lid, a.data, state)
    save(f"{a.data}/current.json", {"league_id": lid, "season": lg["season"], "sport": sport})
    save(f"{a.data}/state.json", state)
    players_db(sport)
    prev, seen = lg.get("previous_league_id"), {lid}
    while prev and prev != "0" and prev not in seen:
        seen.add(prev)
        prev = fetch_league(prev, a.data, state).get("previous_league_id")
    if sport == "nfl":
        fetch_projections(a.data, lg["season"], state.get("week") or 1)


# ---------- queries (offline) ----------
def ctx(a):
    cur = load(f"{a.data}/current.json")
    if not cur:
        raise SleeperError("no saved league: run `fetch` first")
    season = a.season or cur["season"]
    d = os.path.join(a.data, season)
    lg = load(f"{d}/league.json")
    if not lg:
        raise SleeperError(f"no saved data for season {season}")
    rosters = load(f"{d}/rosters.json")
    owner = team_names(load(f"{d}/users.json"), rosters)
    return d, lg, rosters, owner


def cmd_rules(a):
    _, lg, _, _ = ctx(a)
    for k, v in rules_rows(lg):
        print(f"{k:15} {v}")
    print("Scoring:", ", ".join(f"{k}={v}" for k, v in sorted(lg["scoring_settings"].items()) if v))


def cmd_standings(a):
    _, _, rosters, owner = ctx(a)
    for r in sorted(rosters, key=lambda r: (-r["settings"].get("wins", 0), -fpts(r["settings"]))):
        s = r["settings"]
        print(f"{owner[r['roster_id']][:26]:26} {s.get('wins', 0)}-{s.get('losses', 0)}-{s.get('ties', 0)}  PF {fpts(s):.2f}")


def cmd_week(a):
    d, _, _, owner = ctx(a)
    m = load(f"{d}/matchups/week_{a.n:02d}.json")
    if not m:
        raise SleeperError(f"no saved matchups for week {a.n}")
    games = {}
    for x in m:
        games.setdefault(x["matchup_id"], []).append(x)
    for g in games.values():
        print("  vs  ".join(f"{owner[x['roster_id']]} {x.get('points') or 0:.2f}" for x in g))


def cmd_roster(a):
    d, lg, rosters, owner = ctx(a)
    db = players_db(lg["sport"])
    q = a.team.lower()
    hits = [r for r in rosters if str(r["roster_id"]) == q] if q.isdigit() else [r for r in rosters if q in owner[r["roster_id"]].lower()]
    if len(hits) != 1:
        raise SleeperError("matches: " + (", ".join(owner[r["roster_id"]] for r in hits) or "none; teams: " + ", ".join(owner.values())))
    r = hits[0]
    groups = (("starters", r.get("starters")), ("bench", [p for p in r.get("players") or [] if p not in (r.get("starters") or []) and p not in (r.get("reserve") or []) and p not in (r.get("taxi") or [])]),
              ("IR", r.get("reserve")), ("taxi", r.get("taxi")))
    print(owner[r["roster_id"]])
    for label, ids in groups:
        for pid in ids or []:
            p = db.get(pid, {})
            print(f"  {label:8} {pname(p) or pid:24} {p.get('position', '?'):4} {p.get('team') or 'FA':4} age {p.get('age')} {p.get('injury_status') or ''}")


def cmd_player(a):
    _, lg, rosters, owner = ctx(a)
    db = players_db(lg["sport"])
    holder = {pid: owner[r["roster_id"]] for r in rosters for pid in r.get("players") or []}
    for pid in match_players(db, a.name):
        p = db[pid]
        print(f"{pname(p)} [{pid}] {p.get('position')} {p.get('team')} age {p.get('age')} inj={p.get('injury_status')} -> {holder.get(pid, 'free agent')}")


def cmd_transactions(a):
    d, lg, _, owner = ctx(a)
    db = players_db(lg["sport"])
    nm = lambda pid: pname(db.get(pid, {})) or pid
    tdir = f"{d}/transactions"
    for f in sorted(os.listdir(tdir)) if os.path.isdir(tdir) else []:
        for t in sorted(load(f"{tdir}/{f}"), key=lambda t: t["created"]):
            if t["status"] != "complete":
                continue
            adds = ", ".join(f"+{nm(p)}->{owner.get(r)}" for p, r in (t.get("adds") or {}).items())
            drops = ", ".join(f"-{nm(p)}" for p in (t.get("drops") or {}))
            bid = (t.get("settings") or {}).get("waiver_bid")
            line = " ".join(x for x in (adds, drops, f"${bid}" if bid is not None else "") if x)
            print(f"wk{t['leg']:>2} {t['type']:10} {line}")


def cmd_weekly_file(kind):
    def run(a):
        d, lg, _, _ = ctx(a)
        data = load(f"{d}/{kind}/week_{a.n:02d}.json")
        if data is None:
            raise SleeperError(f"no saved {kind} for week {a.n}; run `fetch`")
        db = players_db(lg["sport"])
        rows = sorted(data, key=lambda r: -(r.get("stats", {}).get("pts_ppr") or 0))[:25]
        for r in rows:
            p = db.get(r["player_id"], {})
            print(f"{pname(p) or r['player_id']:24} {p.get('position', '?'):4} {p.get('team') or 'FA':4} ppr {r.get('stats', {}).get('pts_ppr')}")
    return run


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data", default=argparse.SUPPRESS, help="data folder (default ./data)")
    common.add_argument("--season", default=argparse.SUPPRESS)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, parents=[common])
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fetch", parents=[common])
    f.add_argument("target")
    f.add_argument("--sport", default="nfl", choices=["nfl", "nba"])
    for c in ("rules", "standings", "transactions"):
        sp.add_parser(c, parents=[common])
    for c in ("week", "projections", "stats"):
        sp.add_parser(c, parents=[common]).add_argument("n", type=int)
    sp.add_parser("roster", parents=[common]).add_argument("team")
    sp.add_parser("player", parents=[common]).add_argument("name", nargs="+")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    a.data = getattr(a, "data", "./data")
    a.season = getattr(a, "season", None)
    if a.cmd == "player":
        a.name = " ".join(a.name)
    handlers = {"fetch": cmd_fetch, "rules": cmd_rules, "standings": cmd_standings, "week": cmd_week,
                "roster": cmd_roster, "player": cmd_player, "transactions": cmd_transactions,
                "projections": cmd_weekly_file("projections"), "stats": cmd_weekly_file("stats")}
    try:
        handlers[a.cmd](a)
    except SleeperError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
