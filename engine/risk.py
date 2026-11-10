#!/usr/bin/env python3
"""Risk model: forecast a player's fantasy points for a future game from a vantage date, using only what was
known before that date. This is what a Lock-In decision needs (you decide days before the game), so it is
replayed at lock time, not against Sleeper's game-day snapshot.

    risk.py fit        fit params on weeks 1-2, test on 3-4, print the lock-time replay table
    risk.py PLAYER     current forecast for each remaining game this week

Forecast = P(plays) x E[points | plays]
  E[points | plays] = cal x blend(latest Sleeper projection, own form) x minutes-trend x (B2B second-leg factor)
  P(plays)          = shrunk missed-game rate, raised when he missed his last game (games-missed haircut) or the
                      game is the second night of a back-to-back, and set from the injury feeds when live.
Injury feeds (Sleeper status + ESPN) only exist as live snapshots, so they are used live but cannot be replayed;
collect.py should archive them daily so they can be tested later."""
import datetime as dt, json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N

D = dt.date.fromisoformat


class Params:
    """k: games of own form worth as much as Sleeper's projection; mt: weight on minutes trend; cal: overall calibration;
    a: prior strength (games) on the missed-game rate; streak: P(misses again) after missing his last game;
    bb: extra DNP risk on a back-to-back second leg; bpen: points haircut on a B2B second leg;
    rest: points uplift with 3+ days off; prior: league miss rate for a player with no history."""
    def __init__(self, k=6.0, mt=0.5, cal=0.95, a=12.0, streak=0.55, bb=0.03, bpen=0.04, prior=0.04, rest=0.0):
        self.k, self.mt, self.cal, self.a, self.streak, self.bb, self.bpen, self.prior, self.rest = k, mt, cal, a, streak, bb, bpen, prior, rest

    def as_dict(self):
        return dict(vars(self))


# injury status -> P(plays). Sleeper and ESPN use the same words; when they disagree take the more pessimistic.
STATUS_PLAY = {"Out": 0.0, "IR": 0.0, "Injured Reserve": 0.0, "Suspension": 0.0, "Doubtful": 0.2,
               "Questionable": 0.6, "Day-To-Day": 0.75, "Probable": 0.93, "GTD": 0.6}
STATUS_FADE, STATUS_FADE_OUT = 0.7, 0.85   # per day ahead; an "Out" tag lingers longer than a GTD


def refine(status, note):
    """ESPN files most players as Day-To-Day; the note says how likely he is to play (probable/questionable/doubtful)"""
    n = (note or "").lower()
    if status == "Day-To-Day":
        for word, tag in (("probable", "Probable"), ("doubtful", "Doubtful"), ("questionable", "Questionable")):
            if word in n:
                return tag
    return status


def espn_status(L, live=None):
    """second injury source: ESPN's league injury report -> {pid: status}. Reads collect.py's live.json if given,
    else fetches the public endpoint. Name match is exact after accent folding, so a miss means no ESPN status."""
    import unicodedata, urllib.request
    fold = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(".", "").strip()
    rows = []
    if live and os.path.exists(live):
        rows = [(r["player"], refine(r["status"], r.get("note"))) for r in (N.load(live).get("espn_injuries") or [])]
    if not rows:
        try:
            req = urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
                                         headers={"User-Agent": "nba-in-tah/1.0"})
            j = json.load(urllib.request.urlopen(req, timeout=30))
            rows = [(i["athlete"]["displayName"], refine(i["status"], i.get("shortComment"))) for t in j["injuries"] for i in t["injuries"]]
        except Exception:
            return {}
    by = {}
    for pid in L.pinfo:
        by.setdefault(fold(L.pname(pid)), pid)
    return {by[fold(n)]: st for n, st in rows if fold(n) in by}


class Model:
    def __init__(self, L, p=None):
        self.L, self.p = L, p or Params()
        g = defaultdict(dict)  # pid -> date -> row tuple
        for (pid, d), r in L.proj.items():
            g[pid][d] = r.get("team")
        for (pid, d), r in L.act.items():
            g[pid].setdefault(d, r.get("team"))
        self.games = {pid: sorted(v.items()) for pid, v in g.items()}

    def history(self, pid, t):
        """games strictly before vantage date t: [(date, team, proj, actual, played, minutes, proj_minutes)]"""
        L, out = self.L, []
        for d, team in self.games.get(pid, ()):
            if d >= t:
                break
            r = L.act.get((pid, d))
            out.append((d, team, L.projected(pid, d), L.actual(pid, d), L.played(pid, d),
                        (r["stats"].get("min", 0) if r and r["stats"] else 0), L.proj_min(pid, d)))
        return out

    def forecast(self, pid, t, d, team=None, status=None):
        """returns (expected points, P(plays), points if he plays, raw Sleeper baseline) for game day d seen from t"""
        p, L, h = self.p, self.L, self.history(pid, t)
        proj = [x for x in h if x[2] > 0]
        if not proj:
            return None
        base = proj[-1][2]                                   # latest Sleeper projection known at t
        pm = proj[-1][6]
        played = [x for x in h if x[4]]
        form = [x[3] for x in played[-10:]]
        wf = len(form) / (len(form) + p.k) if form else 0.0
        cond = (1 - wf) * base + wf * (sum(form) / len(form) if form else base)
        recent = played[-3:]
        if recent and pm > 0:
            ratio = sum(x[5] for x in recent) / len(recent) / max(1.0, sum(x[6] or pm for x in recent) / len(recent))
            cond *= 1 + p.mt * (min(1.5, max(0.5, ratio)) - 1)
        team = team or (h[-1][1] if h else None)
        tg = L.team_games(team)
        prev = [x for x in tg if x < d]
        b2b = bool(prev) and (D(d) - D(prev[-1])).days == 1
        if b2b:
            cond *= 1 - p.bpen
        elif prev and (D(d) - D(prev[-1])).days >= 4:            # 3+ full days off
            cond *= 1 + p.rest
        cond *= p.cal
        # availability: games he has been around for (rows exist), missed = no minutes
        n = len(h)
        miss = sum(1 for x in h if not x[4])
        q = (miss + p.a * p.prior) / (n + p.a)               # shrunk miss rate
        if h and not h[-1][4] and base >= 8:                 # missed his latest game: ongoing absence
            q = max(q, p.streak)
        if b2b:
            q = min(1.0, q + p.bb)
        play = 1 - q
        sts = list(status) if isinstance(status, (list, tuple)) else [status]
        if "Probable" in sts and all(x in (None, "Probable", "GTD", "Day-To-Day") for x in sts):
            sts = ["Probable"]   # the team's explicit "probable" beats Sleeper's generic GTD tag
        for st in sts:
            if st in STATUS_PLAY:   # today's tag fades for later games (unvalidated prior: no injury history to replay)
                miss = (1 - STATUS_PLAY[st]) * (STATUS_FADE_OUT if STATUS_PLAY[st] == 0 else STATUS_FADE) ** (D(d) - D(t)).days
                play = min(play, 1 - miss)
        return play * cond, play, cond, base


def targets(L, weeks, min_base=8.0):
    """every (vantage t, game d) pair inside a week: t = each game date of the week, d = his games on/after t."""
    M = Model(L)
    out = []
    for pid, gl in M.games.items():
        for w in weeks:
            ds = [(d, team) for d, team in gl if N.week_of(d) == w and d < "2026-11-10"]
            for i, (t, _) in enumerate(ds):
                for d, team in ds[i:]:
                    if L.act.get((pid, d)) is None and L.proj.get((pid, d)) is None:
                        continue
                    out.append((pid, t, d, team))
    return out


def evaluate(L, p, pairs, min_base=8.0):
    M = Model(L, p)
    rows = []
    for pid, t, d, team in pairs:
        f = M.forecast(pid, t, d, team)
        if not f or f[3] < min_base:
            continue
        rows.append((f[0], f[3], L.actual(pid, d), f[1], L.played(pid, d), (D(d) - D(t)).days))
    return rows


def score(rows):
    if not rows:
        return {}
    E, B, A = [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]
    mae = lambda X: sum(abs(a - x) for a, x in zip(A, X)) / len(A)
    bias = lambda X: sum(a - x for a, x in zip(A, X)) / len(A)
    brier_m = sum((r[3] - r[4]) ** 2 for r in rows) / len(rows)
    brier_r = sum((1 - r[4]) ** 2 for r in rows) / len(rows)
    return {"n": len(rows), "raw_mae": mae(B), "model_mae": mae(E), "raw_r": N.corr(B, A), "model_r": N.corr(E, A),
            "raw_bias": bias(B), "model_bias": bias(E), "raw_brier": brier_r, "model_brier": brier_m,
            "dnp": 1 - sum(r[4] for r in rows) / len(rows)}


def fit(L, train):
    """coordinate search, few passes, objective = MAE of expected points on the training pairs"""
    p = Params()
    grid = {"k": [2, 4, 6, 10, 16, 30], "mt": [0, 0.25, 0.5, 0.75, 1.0], "cal": [0.88, 0.91, 0.94, 0.97, 1.0],
            "a": [4, 8, 12, 20, 40, 80], "streak": [0.3, 0.45, 0.6, 0.75, 0.9, 0.95], "bb": [0, 0.02, 0.05, 0.1],
            "bpen": [-0.03, 0, 0.03, 0.06, 0.1], "rest": [-0.05, 0, 0.03, 0.06], "prior": [0.02, 0.04, 0.07, 0.1]}
    best = score(evaluate(L, p, train))["model_mae"]
    for _ in range(2):
        for k, vals in grid.items():
            for v in vals:
                old = getattr(p, k)
                setattr(p, k, v)
                m = score(evaluate(L, p, train))["model_mae"]
                if m < best - 1e-6:
                    best = m
                else:
                    setattr(p, k, old)
    return p, best


PARAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "risk_params.json")


def load_params():
    raw = N.load(PARAMS_FILE)
    return Params(**raw) if raw else Params()


def main():
    L = N.League()
    if sys.argv[1:2] == ["fit"]:
        # league-wide miss rate among relevant players, from training weeks only
        train, test = targets(L, (1, 2)), targets(L, (3, 4))
        p, m = fit(L, train)
        print("fitted:", {k: round(v, 3) for k, v in p.as_dict().items()}, f"train MAE {m:.3f}")
        json.dump(p.as_dict(), open(PARAMS_FILE, "w"), indent=1)
        for lab, pr in (("train wk1-2", train), ("TEST wk3-4", test)):
            rs = evaluate(L, p, pr)
            s = score(rs)
            print(f"\n{lab}: n={s['n']}  DNP rate {s['dnp']:.1%}")
            print(f"  raw Sleeper  MAE {s['raw_mae']:.2f}  r {s['raw_r']:.3f}  bias {s['raw_bias']:+.2f}  Brier(plays) {s['raw_brier']:.4f}")
            print(f"  risk model   MAE {s['model_mae']:.2f}  r {s['model_r']:.3f}  bias {s['model_bias']:+.2f}  Brier(plays) {s['model_brier']:.4f}")
            for lo, hi in ((8, 15), (15, 22), (22, 30), (30, 99)):
                t = score([r for r in rs if lo <= r[1] < hi])
                if t:
                    print(f"   tier {lo:>2}-{hi:<2} n={t['n']:5}  MAE raw {t['raw_mae']:5.2f} -> {t['model_mae']:5.2f}   bias raw {t['raw_bias']:+5.2f} -> {t['model_bias']:+5.2f}  DNP {t['dnp']:.1%}")
            for lo, hi in ((0, 1), (1, 3), (3, 7)):
                t = score([r for r in rs if lo <= r[5] < hi])
                if t:
                    print(f"   {lo}-{hi - 1} days ahead n={t['n']:5}  MAE raw {t['raw_mae']:5.2f} -> {t['model_mae']:5.2f}  DNP {t['dnp']:.1%}")
        return
    q = " ".join(sys.argv[1:]).lower()
    M = Model(L, load_params())
    hits = [pid for pid in M.games if q and q in L.pname(pid).lower()]
    today = dt.date.today().isoformat()
    for pid in hits[:3]:
        for d, team in M.games[pid]:
            if d >= today and N.week_of(d) == N.week_of(today):
                f = M.forecast(pid, today, d, team, (L.pinfo.get(pid) or {}).get("injury_status"))
                if f:
                    print(f"{L.pname(pid):24} {d} {team}  exp {f[0]:5.1f}  plays {f[1]:.0%}  if plays {f[2]:5.1f}  (Sleeper {f[3]:.1f})")


if __name__ == "__main__":
    main()
