#!/usr/bin/env python3
"""Lock engine for Lock-In mode: optimal stopping per lineup slot.

Rules (Sleeper help article): one game per starter counts; a game can be locked after it ends and before that
player's next game starts; locks can't be undone; an unlocked starter scores his team's FINAL game of the week,
0 if he sat it. A slot is therefore a sequence of chances (its regular's games plus free rolls on nights he is
idle); the last chance is forced. Backward induction gives "lock if >= X" after every chance.

    lock.py plan [TEAM] [--week W] [--today YYYY-MM-DD]   thresholds + free-roll nights for the rest of the week
    lock.py backtest [--weeks 1,2,3]                         engine policy vs every manager's real locks
"""
import argparse, datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N
import risk as R

SLOTS = ["C", "PG", "SG", "SF", "PF", "G", "F", "UTIL", "UTIL"]   # narrow slots first (playbook rule 3)
OK = {"PG": {"PG"}, "SG": {"SG"}, "G": {"PG", "SG"}, "SF": {"SF"}, "PF": {"PF"}, "F": {"SF", "PF"}, "C": {"C"},
      "UTIL": {"PG", "SG", "SF", "PF", "C"}}


def ratios(L, M, before):
    """empirical spread: actual / expected-if-plays for games he played, cond >= 8, dated before `before`.
    Fantasy points are right-skewed (a 50-pt night is possible, a -10 isn't), so use the real shape, not a normal."""
    out = []
    for pid, gl in M.games.items():
        for d, team in gl:
            if d >= before or not L.played(pid, d):
                continue
            f = M.forecast(pid, d, d, team)
            if f and f[2] >= 8:
                out.append(L.actual(pid, d) / f[2])
    out.sort()
    step = max(1, len(out) // 200)
    return out[::step] or [1.0]


def emax(m, v, Rq):
    """E[max(m * ratio, v)] over the empirical ratio sample"""
    return sum(max(m * r, v) for r in Rq) / len(Rq)


def chain(chances, Rq):
    """chances: [(play_prob, mean_if_plays)] in date order, last one forced.
    returns thresholds[i] = value of carrying on after chance i (lock chance i if its score >= this), and V0."""
    n = len(chances)
    cont = [0.0] * n
    v = 0.0
    for i in range(n - 1, -1, -1):
        q, m = chances[i]
        cont[i] = v
        v = q * m if i == n - 1 else (1 - q) * v + q * emax(m, v, Rq)
    return cont, v


def week_dates(w):
    a = N.WEEK0 + dt.timedelta(days=7 * (w - 1))
    return [(a + dt.timedelta(days=i)).isoformat() for i in range(7)]


def positions(L, pid):
    return set((L.pinfo.get(pid) or {}).get("fantasy_positions") or [])


def plan(L, M, Rq, roster_ids, starters, w, today, locked=None, espn=None):
    """assign regulars to slots by lock-value, then fill idle nights with bench free rolls."""
    locked = locked or {}
    dates = [d for d in week_dates(w) if d >= today]
    espn = R.espn_status(L) if espn is None else espn
    status = {pid: [(L.pinfo.get(pid) or {}).get("injury_status"), espn.get(pid)] for pid in roster_ids}

    def games(pid):
        return [(d, t) for d, t in M.games.get(pid, ()) if d in dates]

    def fc(pid, d, t):
        f = M.forecast(pid, today, d, t, status.get(pid))
        return (f[1], f[2]) if f else (0.0, 0.0)

    # a starter who already played this week has that score on the board: lockable now, before his next game
    board = {}
    for pid in starters:
        done = [d for d in week_dates(w) if d < today and L.played(pid, d)]
        if done:
            board[pid] = (done[-1], L.actual(pid, done[-1]))
    rest = {pid: chain([fc(pid, d, t) for d, t in games(pid)], Rq)[1] if games(pid) else 0.0 for pid in roster_ids}
    val = {pid: max(rest[pid], board[pid][1]) if pid in board else rest[pid] for pid in roster_ids}
    # regulars: best value per slot, narrow slots first; starters already in a slot keep priority on ties
    free = [p for p in roster_ids if p not in locked.values()]
    reg = {}
    for i, s in enumerate(SLOTS):
        key = f"{s}{i}"
        if key in locked:
            continue
        cands = [p for p in free if positions(L, p) & OK[s] and p not in reg.values()]
        if cands:
            reg[key] = max(cands, key=lambda p: (val[p], p in starters))
    bench = [p for p in free if p not in reg.values()]
    out = []
    used = {d: set() for d in dates}
    for i, s in enumerate(SLOTS):
        key = f"{s}{i}"
        if key in locked or key not in reg:
            continue
        p = reg[key]
        if p in board and board[p][1] >= rest[p]:      # lock now: the score on the board beats waiting
            out.append((s, p, board[p][1], [(board[p][0], p, (1.0, board[p][1]), board[p][1], "LOCK")]))
            continue
        mine = {d: t for d, t in games(p)}
        seq = []
        for d in dates:
            if d in mine:
                seq.append((d, p, mine[d]))
            else:   # free roll: best eligible bench player playing tonight, not already used tonight
                opts = [(b, t) for b in bench if b not in used[d] and positions(L, b) & OK[s]
                        for dd, t in games(b) if dd == d]
                if opts:
                    b, t = max(opts, key=lambda x: fc(x[0], d, x[1])[0] * fc(x[0], d, x[1])[1])
                    if fc(b, d, t)[0] * fc(b, d, t)[1] > 0:
                        used[d].add(b)
                        seq.append((d, b, t))
        # a free roll after the regular's last game would make the free roller the forced final score; only keep it
        # if he is worth more than the regular's own final game
        while seq and seq[-1][1] != p and len(seq) > 1:
            q, m = fc(seq[-1][1], seq[-1][0], seq[-1][2])
            lastreg = [x for x in seq if x[1] == p]
            if lastreg and q * m < fc(p, lastreg[-1][0], lastreg[-1][2])[0] * fc(p, lastreg[-1][0], lastreg[-1][2])[1]:
                seq.pop()
            else:
                break
        ch = [fc(b, d, t) for d, b, t in seq]
        cont, v = chain(ch, Rq) if ch else ([], 0.0)
        rows = [(d, b, ch[j], cont[j], j == len(seq) - 1) for j, (d, b, t) in enumerate(seq)]
        if p in board:                                  # on the board but worth holding
            rows.insert(0, (board[p][0], p, (1.0, board[p][1]), v, "HOLD"))
        out.append((s, p, v, rows))
    return out, reg, val


# ---------------------------------------------------------------------------------------------- backtest
def counted_game(L, pid, w, pts):
    """which of his games produced the counted score: (index, games list) — earliest exact match"""
    gl = [(d, L.actual(pid, d), L.played(pid, d)) for d in week_dates(w) if (pid, d) in L.act or (pid, d) in L.proj]
    gl = [g for g in gl if (pid, g[0]) in L.act]
    for i, (d, a, pl) in enumerate(gl):
        if pl and abs(a - pts) < 0.01:
            return i, gl
    return (len(gl) - 1 if gl else None), gl


def engine_policy(L, M, Rq, pid, gl):
    """walk his real week: after each played game compare score to the value of his remaining games (forecast with
    info up to that night). DNP nights can't be locked. Returns the score the engine ends with."""
    for i, (d, a, pl) in enumerate(gl):
        if i == len(gl) - 1:
            return a if pl else 0.0
        if not pl:
            continue
        nxt = gl[i + 1][0]
        rest = []
        for d2, _, _ in gl[i + 1:]:
            f = M.forecast(pid, nxt, d2)
            rest.append((f[1], f[2]) if f else (0.0, 0.0))
        if a >= chain(rest, Rq)[1]:
            return a
    return 0.0


RAW = dict(k=1e9, mt=0, cal=1, streak=0, prior=0, a=1e9, bb=0, bpen=0, rest=0)   # risk model switched off = raw Sleeper


def backtest(L, weeks):
    M = R.Model(L, R.load_params())
    Mr = R.Model(L, R.Params(**RAW))
    rawtot = {}
    print(f"{'manager':8} {'wk':>2}  {'actual':>7} {'engine':>7} {'ride':>7} {'perfect':>7}   locks early / of starters")
    tot = {}
    detail = []
    for w in weeks:
        Rq = ratios(L, M, week_dates(w)[0])
        for m in N.load(f"{L.d}/matchups/week_{w:02d}.json"):
            who = L.name[m["roster_id"]]
            act = eng = ride = best = 0.0
            early = n = 0
            for pid, pts in zip(m["starters"], m["starters_points"]):
                if pid == "0":
                    continue
                i, gl = counted_game(L, pid, w, pts)
                if not gl:
                    continue
                n += 1
                e = engine_policy(L, M, Rq, pid, gl)
                rawtot[who] = rawtot.get(who, 0) + engine_policy(L, Mr, Rq, pid, gl)
                r = gl[-1][1] if gl[-1][2] else 0.0
                b = max([g[1] for g in gl if g[2]] or [0.0])
                act, eng, ride, best = act + pts, eng + e, ride + r, best + b
                if i is not None and i < len(gl) - 1:
                    early += 1
                if abs(e - pts) >= 5:
                    detail.append((w, who, L.pname(pid), pts, e, [g[1] if g[2] else "DNP" for g in gl]))
            t = tot.setdefault(who, [0, 0, 0, 0])
            for k, x in enumerate((act, eng, ride, best)):
                t[k] += x
            print(f"{who:8} {w:>2}  {act:7.1f} {eng:7.1f} {ride:7.1f} {best:7.1f}   {early}/{n}")
    print("\nTOTAL weeks", ",".join(map(str, weeks)))
    for who, t in sorted(tot.items(), key=lambda x: x[1][0] - x[1][1]):
        print(f"{who:8} actual {t[0]:7.1f}  engine {t[1]:7.1f} ({t[1] - t[0]:+6.1f})  never-lock {t[2]:7.1f}  perfect hindsight {t[3]:7.1f}  "
              f"capture {100 * (t[0] - t[2]) / max(1, t[3] - t[2]):4.0f}% vs engine {100 * (t[1] - t[2]) / max(1, t[3] - t[2]):4.0f}%")
    s = lambda i: sum(t[i] for t in tot.values())
    print(f"\nLEAGUE  managers {s(0):.1f}  engine+risk model {s(1):.1f}  engine+raw Sleeper {sum(rawtot.values()):.1f}  "
          f"never-lock {s(2):.1f}  hindsight {s(3):.1f}")
    return detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "backtest"])
    ap.add_argument("team", nargs="?", default="Jack")
    ap.add_argument("--week", type=int)
    ap.add_argument("--weeks", default="1,2,3")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--detail", action="store_true")
    a = ap.parse_args()
    L = N.League()
    if a.cmd == "backtest":
        det = backtest(L, [int(x) for x in a.weeks.split(",")])
        if a.detail:
            print("\nbiggest engine-vs-manager differences (>=5 pts):")
            for w, who, nm, pts, e, gl in sorted(det, key=lambda x: -abs(x[3] - x[4]))[:25]:
                print(f"  wk{w} {who:6} {nm:24} took {pts:5.1f}  engine {e:5.1f}  games {gl}")
        return
    w = a.week or N.week_of(a.today)
    rid = [k for k, v in L.name.items() if v.lower() == a.team.lower()][0]
    ro = [r for r in L.rosters if r["roster_id"] == rid][0]
    mm = [m for m in (N.load(f"{L.d}/matchups/week_{w:02d}.json") or []) if m["roster_id"] == rid]
    starters = set(mm[0]["starters"]) if mm else set(ro.get("starters") or [])
    ids = [p for p in ro["players"] if p not in (ro.get("reserve") or [])]
    M = R.Model(L, R.load_params())
    Rq = ratios(L, M, a.today)
    out, reg, val = plan(L, M, Rq, ids, starters, w, a.today)
    print(f"{a.team} week {w} from {a.today}: lock-in value by slot (expected locked score)\n")
    for s, p, v, seq in out:
        print(f"{s:4} {L.pname(p):24} worth {v:5.1f}")
        for d, b, (q, m), th, last in seq:
            tag = {"LOCK": f"scored {m:.1f}: LOCK NOW (beats waiting)", "HOLD": f"scored {m:.1f}: hold, rest of week worth {th:.1f}",
                   True: "FORCED (final chance)"}.get(last, f"lock if >= {th:4.1f}")
            fr = "  FREE ROLL" if b != p else ""
            print(f"      {d[5:]} {L.pname(b):22} plays {q:4.0%} exp {m:5.1f}  {tag}{fr}")
    print(f"\nlineup lock-in total {sum(v for _, _, v, _ in out):.1f}")
    print("bench:", ", ".join(f"{L.pname(p)} ({val[p]:.1f})" for p in ids if p not in reg.values()))


if __name__ == "__main__":
    main()
