#!/usr/bin/env python3
"""Head-to-head: the original lockin.py rule vs this repo's engine, on the same starters and games.

    compare_methods.py [--weeks 1,2,3]

Original rule: lock a finished game when its score >= V(mu, n), where n = team games left after it and V is the
expected locked score of optimal stopping with normally distributed scores (CV 0.30) around a fixed projection mu.
No availability model, no form, no free rolls. Engine: risk model + empirical score spread (lock.py engine_policy).
"""
import argparse, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, risk as R, lock as K

CV = 0.30
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
phi = lambda z: math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def V(mu, n):
    if n == 0 or mu <= 0:
        return 0.0
    v, sd = mu, CV * mu
    for _ in range(n - 1):
        d = (mu - v) / sd
        v = v + (mu - v) * Phi(d) + sd * phi(d)
    return v


def old_policy(mu, gl):
    """gl = [(date, points, played)] for each team game that week, in order"""
    for k, (d, g, played) in enumerate(gl):
        if k == len(gl) - 1:
            return g if played else 0.0
        if played and g >= V(mu, len(gl) - k - 1):
            return g
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", default="1,2,3")
    a = ap.parse_args()
    weeks = [int(x) for x in a.weeks.split(",")]
    L = N.League()
    M = R.Model(L, R.load_params())
    proj = {}
    for (pid, d), r in L.proj.items():
        p = L.projected(pid, d)
        if p > 0:
            proj.setdefault(pid, []).append(p)
    mu = {pid: sum(v) / len(v) for pid, v in proj.items()}
    # no-lookahead variant: use only projections dated before the week (week 1: that week's own, as nothing earlier exists)
    rows = {}
    for (pid, d), r in L.proj.items():
        p_ = L.projected(pid, d)
        if p_ > 0:
            rows.setdefault(pid, []).append((d, p_))

    def mu_before(pid, w):
        start = K.week_dates(w)[0]
        v = [x for d, x in rows.get(pid, []) if d < start] or [x for d, x in rows.get(pid, []) if K.week_dates(w)[0] <= d <= K.week_dates(w)[-1]]
        return sum(v) / len(v) if v else 0.0
    tot = {}
    for w in weeks:
        Rq = K.ratios(L, M, K.week_dates(w)[0])
        for m in N.load(f"{L.d}/matchups/week_{w:02d}.json"):
            who = L.name[m["roster_id"]]
            t = tot.setdefault(who, [0.0] * 6)   # actual, engine, old rule, ride (never lock), perfect, old rule without lookahead
            for pid, pts in zip(m["starters"], m["starters_points"]):
                if pid == "0":
                    continue
                i, gl = K.counted_game(L, pid, w, pts)
                if not gl:
                    continue
                t[0] += pts
                t[1] += K.engine_policy(L, M, Rq, pid, gl)
                t[2] += old_policy(mu.get(pid, 0.0), gl)
                t[3] += gl[-1][1] if gl[-1][2] else 0.0
                t[4] += max([g[1] for g in gl if g[2]] or [0.0])
                t[5] += old_policy(mu_before(pid, w), gl)
    print(f"weeks {weeks}: same starters, same games\n")
    print(f"{'manager':8}{'actual':>8}{'engine':>8}{'old rule':>9}{'never lock':>11}{'perfect':>9}   engine-old")
    for who, t in sorted(tot.items(), key=lambda x: -x[1][1]):
        print(f"{who:8}{t[0]:8.1f}{t[1]:8.1f}{t[2]:9.1f}{t[3]:11.1f}{t[4]:9.1f}   {t[1] - t[2]:+6.1f}")
    s = lambda i: sum(t[i] for t in tot.values())
    print(f"{'LEAGUE':8}{s(0):8.1f}{s(1):8.1f}{s(2):9.1f}{s(3):11.1f}{s(4):9.1f}   {s(1) - s(2):+6.1f}")
    cap = lambda x: 100 * (x - s(3)) / (s(4) - s(3))
    print(f"\nshare of the possible gain over never-locking: actual {cap(s(0)):.0f}%  engine {cap(s(1)):.0f}%  old rule {cap(s(2)):.0f}%  old rule, no lookahead {cap(s(5)):.0f}% ({s(5):.1f} pts)")


if __name__ == "__main__":
    main()
