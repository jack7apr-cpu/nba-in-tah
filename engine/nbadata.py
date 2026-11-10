"""Shared NBA loader: league scoring, per-game Sleeper projections and actuals, team schedules.
Everything reads ./data/<season> (fetched by collect.py / sleeper.py); scoring always comes from league.json,
never hardcoded, because the commissioner has changed it mid-season before (40+/50+ bonuses, Oct 2026)."""
import datetime as dt, json, os
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
WEEK0 = dt.date(2026, 10, 19)  # Monday of week 1; Sleeper NBA weeks run Mon-Sun


def load(path):
    return json.load(open(path)) if os.path.exists(path) else None


def week_of(day):
    return (dt.date.fromisoformat(day) - WEEK0).days // 7 + 1


class League:
    def __init__(self, season="2026", data=ROOT):
        self.d = os.path.join(data, season)
        self.lg = load(f"{self.d}/league.json")
        self.sc = self.lg["scoring_settings"]
        self.rosters = load(f"{self.d}/rosters.json")
        users = {u["user_id"]: u["display_name"] for u in load(f"{self.d}/users.json")}
        self.user = {r["roster_id"]: users.get(r["owner_id"], "?") for r in self.rosters}
        self.name = {r["roster_id"]: REAL.get(self.user[r["roster_id"]], self.user[r["roster_id"]]) for r in self.rosters}
        self.proj, self.act, self.pinfo = {}, {}, {}
        self.team_dates = defaultdict(set)   # team -> {game dates} from both feeds
        for kind, store in (("projections", self.proj), ("stats", self.act)):
            for w in range(1, 26):
                rows = load(f"{self.d}/{kind}/week_{w:02d}.json")
                if not rows:
                    continue
                for r in rows:
                    pid = r.get("player_id")
                    if not pid:
                        continue
                    store[(pid, r["date"])] = r
                    if r.get("team"):
                        self.team_dates[r["team"]].add(r["date"])
                    if r.get("player"):
                        self.pinfo[pid] = r["player"]

    # ---- scoring -------------------------------------------------------
    def fp(self, s, expected=False):
        """Fantasy points for one game's stat line under this league's settings.
        Projections carry dd/td as probabilities, so the same formula gives expected bonus points."""
        if not s:
            return 0.0
        sc = self.sc
        v = sum(sc.get(k, 0) * s.get(k, 0) for k in ("pts", "reb", "ast", "stl", "blk", "to", "tpm", "tf", "ff"))
        if expected:
            v += sc.get("dd", 0) * s.get("dd", 0) + sc.get("td", 0) * s.get("td", 0)
        else:
            cats = sum(s.get(k, 0) >= 10 for k in ("pts", "reb", "ast", "stl", "blk"))
            v += sc.get("dd", 0) * (cats >= 2) + sc.get("td", 0) * (cats >= 3)
            v += sc.get("bonus_pt_40p", 0) * (s.get("pts", 0) >= 40) + sc.get("bonus_pt_50p", 0) * (s.get("pts", 0) >= 50)
        return round(v, 2)

    def played(self, pid, day):
        r = self.act.get((pid, day))
        return bool(r and r["stats"] and r["stats"].get("min", 0) > 0)

    def actual(self, pid, day):
        r = self.act.get((pid, day))
        return self.fp(r["stats"]) if r and r["stats"] else 0.0

    def projected(self, pid, day):
        r = self.proj.get((pid, day))
        return self.fp(r["stats"], expected=True) if r and r["stats"] else 0.0

    def proj_min(self, pid, day):
        r = self.proj.get((pid, day))
        return (r["stats"].get("sp", 0) / 60) if r and r["stats"] else 0.0

    def team_games(self, team, week=None):
        ds = sorted(self.team_dates.get(team, ()))
        return [d for d in ds if week is None or week_of(d) == week]

    def pname(self, pid):
        p = self.pinfo.get(pid) or {}
        return f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or pid


# Sleeper username -> real first name (Jack's naming rule)
REAL = {"KingBoo25": "Kyran", "maxcmaples": "Maxi", "vPiggZ": "David", "donghyuk101301": "Tony",
        "Idbh": "Isaac", "lmlewis": "Lewis", "Matttallguy": "Matt", "jackhill1617": "Jack"}


def corr(x, y):
    """Pearson r (statistics.correlation needs 3.10; local python is older)."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x) ** 0.5
    syy = sum((b - my) ** 2 for b in y) ** 0.5
    return sxy / (sxx * syy) if sxx and syy else 0.0
