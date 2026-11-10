#!/usr/bin/env python3
"""League-agnostic NFL engine: projections -> THIS league's scoring -> best lineup, waiver and roster value.
Reads everything from ./data (saved by sleeper-api). Nothing about the league is hardcoded.

    engine.py lineup TEAM [--week W]     best legal lineup + bench for the week
    engine.py waivers TEAM [--top N]     free agents ranked by rest-of-season lineup gain (playoff weeks weighted)
    engine.py board [--top N]            best rest-of-season players by position
"""
import argparse, os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/sleeper-api"))
import sleeper as S

FLEX_ELIGIBLE = {"FLEX": {"RB", "WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"}, "REC_FLEX": {"WR", "TE"}}
NON_STARTING = {"BN", "IR", "TAXI"}
INJURY_FACTOR = {"Injured Reserve": 0, "Out": 0, "IR": 0, "Doubtful": 0.25, "Questionable": 0.85, "Suspended": 0, "PUP": 0, "NA": 0, "COV": 0}
# Sleeper projections bucket long FGs as *_50p; leagues score 50_59 / 60p separately
ALIASES = {"fgm_50p": "fgm_50_59", "fgmiss_50p": "fgmiss_50_59"}
PLAYOFF_WEIGHT = 1.5


class Ctx:
    def __init__(self, data="./data", season=None):
        cur = S.load(f"{data}/current.json") or sys.exit("run sleeper-api fetch first")
        self.season = season or cur["season"]
        d = f"{data}/{self.season}"
        self.d = d
        self.lg = S.load(f"{d}/league.json")
        self.rosters = S.load(f"{d}/rosters.json")
        self.owner = S.team_names(S.load(f"{d}/users.json"), self.rosters)
        self.manager = {int(k): v for k, v in (S.load(f"{data}/names.json") or {}).items()}  # roster_id -> real first name
        self.db = S.players_db(self.lg["sport"])
        self.scoring = self.lg["scoring_settings"]
        self.positions = self.lg["roster_positions"]
        self.week = (S.load(f"{data}/state.json") or {}).get("week", 1)
        st = self.lg["settings"]
        self.playoff_start = st.get("playoff_week_start") or 15
        self.proj, self._bye, self._pts = {}, {}, {}
        pdir = f"{d}/projections"
        for f in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
            w = int(f[5:7])
            self.proj[w] = {r["player_id"]: r for r in S.load(f"{pdir}/{f}") if r.get("player_id")}
        self.stats = {}
        sdir = f"{d}/stats"
        for f in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
            self.stats[int(f[5:7])] = {r["player_id"]: r for r in S.load(f"{sdir}/{f}") if r.get("player_id")}
        self.espn = {}
        for team in (S.load(f"{d}/espn_injuries.json") or {}).get("injuries", []):
            for i in team.get("injuries", []):
                hit = S.match_players(self.db, i["athlete"]["displayName"], 1)
                if hit and S.norm(S.pname(self.db[hit[0]])) == S.norm(i["athlete"]["displayName"]):
                    self.espn[hit[0]] = i["status"]
        self.use_history = True
        self.rostered = {p for r in self.rosters for p in (r.get("players") or [])}

    def team(self, q):
        hits = [r for r in self.rosters if str(r["roster_id"]) == q] if q.isdigit() else [r for r in self.rosters if q.lower() in self.owner[r["roster_id"]].lower()]
        if len(hits) != 1:
            sys.exit("team must match exactly one of: " + ", ".join(f"{r['roster_id']}={self.owner[r['roster_id']]}" for r in self.rosters))
        return hits[0]

    def pts(self, pid, week):
        key = (pid, week)
        if key not in self._pts:
            self._pts[key] = self._pts_uncached(pid, week)
        return self._pts[key]

    def status(self, pid):
        """Worst of Sleeper's and ESPN's current status."""
        s = [x for x in ((self.db.get(pid) or {}).get("injury_status"), self.espn.get(pid)) if x and x != "Active"]
        return min(s, key=lambda x: INJURY_FACTOR.get(x, 1.0)) if s else None

    def play_rate(self, pid, before):
        """Share of his team's games he actually played before `before` (prior of 3 games played, so small samples shrink to 1)."""
        team = (self.db.get(pid) or {}).get("team")
        played = total = 0
        for w in self.stats:
            if w >= before or sum(1 for q in self.stats[w] if (self.db.get(q) or {}).get("team") == team) < 5:
                continue
            total += 1
            played += 1 if self.raw(self.stats[w].get(pid) or {}) > 0 else 0
        return min(1.0, (played + 3) / (total + 3))

    def _pts_uncached(self, pid, week):
        """Projected points in THIS league's scoring, adjusted for injury status. 0 on bye / no projection."""
        status = self.status(pid)
        if INJURY_FACTOR.get(status, 1.0) == 0:
            return 0.0
        miss = self.play_rate(pid, self.week) if self.use_history else 1.0  # games-missed risk haircut
        row = self.proj.get(week, {}).get(pid)
        if not row or self.raw(row) <= 0.5:  # empty projection row = Sleeper has no number for him
            team = (self.db.get(pid) or {}).get("team")
            if not team or self.on_bye(team, week):
                return 0.0
            known = [x for x in (self.raw(self.proj[w][pid]) for w in self.proj if pid in self.proj[w]) if x > 0.5]
            if not known:  # no projection (often a hurt star): fall back to games he actually played
                known = [x for x in (self.raw(self.stats[w][pid]) for w in self.stats if pid in self.stats[w]) if x > 0]
            return (sum(known) / len(known) if known else 0.0) * INJURY_FACTOR.get(status, 1.0) * miss
        return self.raw(row) * INJURY_FACTOR.get(status, 1.0) * miss

    def raw(self, row):
        return sum(v * self.scoring.get(ALIASES.get(k, k), 0) for k, v in (row.get("stats") or {}).items())

    def on_bye(self, team, week):
        """A team is on bye when almost none of its players have a projection that week."""
        key = (team, week)
        if key not in self._bye:
            n = sum(1 for pid in self.proj.get(week, {}) if (self.db.get(pid) or {}).get("team") == team)
            self._bye[key] = n < 5
        return self._bye[key]

    def rules(self):
        """data/protected.json: list = no-drop names, or {"no_drop": [], "no_trade": [], "premium": {name: min value ratio}}."""
        r = S.load("./data/protected.json", {})
        return {"no_drop": r, "no_trade": [], "premium": {}} if isinstance(r, list) else {"no_drop": [], "no_trade": [], "premium": {}, **r}

    def _ids(self, names):
        return {pid for n in names for pid in S.match_players(self.db, n, 1)}

    def protected(self):
        """Never suggested as drops: no_drop + no_trade + premium players."""
        r = self.rules()
        return self._ids(r["no_drop"] + r["no_trade"] + list(r["premium"]))

    def no_trade(self):
        return self._ids(self.rules()["no_trade"])

    def premium(self):
        """{player_id: min (received value / given value)} for players only tradable for a clearly better return."""
        return {pid: ratio for n, ratio in self.rules()["premium"].items() for pid in S.match_players(self.db, n, 1)}

    def pos(self, pid):
        return (self.db.get(pid) or {}).get("position")

    def name(self, pid):
        return S.pname(self.db.get(pid) or {}) or pid

    def weight(self, week):
        return PLAYOFF_WEIGHT if self.playoff_start <= week <= 17 else 1.0

    def weeks_left(self):
        return [w for w in sorted(self.proj) if w >= self.week and w <= 17]

    def best_lineup(self, pids, week):
        """Optimal legal lineup: fixed positions first, then flex slots from what's left."""
        slots = [p for p in self.positions if p not in NON_STARTING]
        pool = sorted(((self.pts(p, week), p) for p in pids if self.pos(p)), reverse=True)
        used, lineup = set(), []
        for slot in [s for s in slots if s not in FLEX_ELIGIBLE] + [s for s in slots if s in FLEX_ELIGIBLE]:
            ok = FLEX_ELIGIBLE.get(slot, {slot})
            pick = next(((pt, p) for pt, p in pool if p not in used and self.pos(p) in ok), None)
            if pick:
                used.add(pick[1])
                lineup.append((slot, pick[1], pick[0]))
        return lineup

    def ros_value(self, pids):
        return sum(self.weight(w) * sum(pt for _, _, pt in self.best_lineup(pids, w)) for w in self.weeks_left())


def cmd_lineup(c, a):
    r = c.team(a.team)
    w = a.week or c.week
    mine = r.get("players") or []
    lu = c.best_lineup([p for p in mine if p not in (r.get("reserve") or []) and p not in (r.get("taxi") or [])], w)
    print(f"{c.owner[r['roster_id']]} week {w}: {sum(x[2] for x in lu):.1f} projected")
    for slot, pid, pt in lu:
        print(f"  {slot:5} {c.name(pid):24} {c.pos(pid):3} {pt:5.1f} {c.db[pid].get('injury_status') or ''}")
    started = {x[1] for x in lu}
    for pid in sorted((p for p in mine if p not in started), key=lambda p: -c.pts(p, w)):
        tag = "IR" if pid in (r.get("reserve") or []) else "taxi" if pid in (r.get("taxi") or []) else "bench"
        print(f"  {tag:5} {c.name(pid):24} {c.pos(pid) or '?':3} {c.pts(pid, w):5.1f} {c.db.get(pid, {}).get('injury_status') or ''}")


def free_agents(c, per_pos=25):
    ros = {}
    for pid in c.proj.get(c.week, {}):
        if pid in c.rostered or c.pos(pid) not in {"QB", "RB", "WR", "TE", "K", "DEF"}:
            continue
        ros[pid] = sum(c.pts(pid, w) for w in c.weeks_left())
    out = {}
    for pid, v in sorted(ros.items(), key=lambda kv: -kv[1]):
        if len(out.setdefault(c.pos(pid), [])) < per_pos:
            out[c.pos(pid)].append(pid)
    return [p for ps in out.values() for p in ps]


def cmd_waivers(c, a):
    r = c.team(a.team)
    mine = [p for p in r.get("players") or [] if p not in (r.get("reserve") or []) and p not in (r.get("taxi") or [])]
    base = c.ros_value(mine)
    keep = c.protected()
    rows = []
    for fa in free_agents(c):
        best = max(((c.ros_value([p for p in mine if p != drop] + [fa]), drop) for drop in mine if drop not in keep and (c.pos(drop) != "DEF" or c.pos(fa) == "DEF")), default=(base, None))
        if best[0] - base > 0.5:
            rows.append((best[0] - base, fa, best[1]))
    print(f"{c.owner[r['roster_id']]}: add/drop by weighted rest-of-season lineup gain (injured high-upside players: review manually before dropping)")
    for gain, fa, drop in sorted(rows, reverse=True)[:a.top]:
        print(f"  +{gain:6.1f}  add {c.name(fa):22} {c.pos(fa):3} drop {c.name(drop)}")


def cmd_board(c, a):
    for pos in ("QB", "RB", "WR", "TE", "K", "DEF"):
        ids = sorted((p for p in c.proj.get(c.week, {}) if c.pos(p) == pos), key=lambda p: -sum(c.pts(p, w) for w in c.weeks_left()))[:a.top]
        print(pos, "; ".join(f"{c.name(p)} {sum(c.pts(p, w) for w in c.weeks_left()):.0f}" for p in ids))


def age_factor(pos, age):
    """Heuristic share of production kept per year; transparent and tunable (not a forecast)."""
    if not age:
        return 0.8
    cliff, slope = {"RB": (26, 0.2), "WR": (28, 0.12), "TE": (29, 0.12), "QB": (34, 0.1)}.get(pos, (30, 0.15))
    return max(0.0, 1 - slope * max(0, age - cliff))


def future_value(c, pid, years=3):
    """Per-week rest-of-season level x age curve summed over the next `years` seasons (weeks/yr = 17)."""
    wk = c.weeks_left()
    base = sum(c.pts(pid, w) for w in wk) / max(len(wk), 1)
    age = (c.db.get(pid) or {}).get("age")
    return sum(base * 17 * age_factor(c.pos(pid), (age or 0) + y if age else None) for y in range(1, years + 1))


def modes(c):
    """contender = top half of standings by wins then points; weights (now, future) per mode."""
    rank = sorted(c.rosters, key=lambda r: (-r["settings"].get("wins", 0), -S.fpts(r["settings"])))
    return {r["roster_id"]: ((1.0, 0.2) if i < len(rank) // 2 else (0.3, 1.0)) for i, r in enumerate(rank)}


def active(r):
    return [p for p in r.get("players") or [] if p not in (r.get("reserve") or []) and p not in (r.get("taxi") or [])]


def combos(items, sizes=(1, 2)):
    import itertools
    return [list(x) for n in sizes for x in itertools.combinations(items, n)]


def cmd_refresh(c, a):
    """Pull ESPN's current injury report (second source next to Sleeper's status)."""
    j = S.http_get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries")
    S.save(f"{c.d}/espn_injuries.json", j)
    c = Ctx(a.data)
    r = c.team(a.team)
    print("ESPN/Sleeper status for his players:")
    for p in r.get("players") or []:
        if c.status(p):
            print(f"  {c.name(p):24} {c.pos(p) or '?':3} {c.status(p)} (sleeper {c.db[p].get('injury_status')}, espn {c.espn.get(p)}) play-rate {c.play_rate(p, c.week):.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="./data")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("lineup", "waivers"):
        p = sp.add_parser(name); p.add_argument("team"); p.add_argument("--week", type=int); p.add_argument("--top", type=int, default=15)
    rp = sp.add_parser("refresh"); rp.add_argument("team", nargs="?", default="10")
    sp.add_parser("board").add_argument("--top", type=int, default=8)
    a = ap.parse_args()
    {"lineup": cmd_lineup, "waivers": cmd_waivers, "board": cmd_board, "refresh": cmd_refresh}[a.cmd](Ctx(a.data), a)


if __name__ == "__main__":
    main()
