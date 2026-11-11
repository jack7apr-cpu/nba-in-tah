#!/usr/bin/env python3
"""Export this week's lock-in plan for every team to JSON for the website.

    export_plan.py [--out site/data/plan.json] [--today YYYY-MM-DD]
"""
import argparse, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, risk as R, lock as K
from compare_methods import V as OLD_V   # the original lockin.py rule, shown as a second opinion


def proj_means(L):
    """fixed per-game projection average per player, like the original lockin.py (F.json)"""
    acc = {}
    for (pid, d), r in L.proj.items():
        v = L.projected(pid, d)
        if v > 0:
            acc.setdefault(pid, []).append(v)
    return {pid: sum(v) / len(v) for pid, v in acc.items()}


def team_plan(L, M, Rq, name, w, today, mu=None):
    mu = mu or {}
    rid = [k for k, v in L.name.items() if v.lower() == name.lower()][0]
    ro = next(r for r in L.rosters if r["roster_id"] == rid)
    mm = [m for m in (N.load(f"{L.d}/matchups/week_{w:02d}.json") or []) if m["roster_id"] == rid]
    starters = set(mm[0]["starters"]) if mm else set(ro.get("starters") or [])
    ids = [p for p in ro["players"] if p not in (ro.get("reserve") or [])]
    fixed = None
    order = ["PG", "SG", "G", "SF", "PF", "F", "C", "UTIL", "UTIL"]   # Sleeper's lineup order
    if mm and len(mm[0]["starters"]) == 9:
        fixed, taken = {}, set()
        for name, pid in zip(order, mm[0]["starters"]):
            i = next(i for i, sn in enumerate(K.SLOTS) if sn == name and i not in taken)
            taken.add(i)
            if pid in ids:
                fixed[f"{name}{i}"] = pid
    out, reg, val = K.plan(L, M, Rq, ids, starters, w, today, fixed=fixed)
    slots = []
    for s, p, v, seq in out:
        ch = []
        for d, b, (q, m), th, last in seq:
            act = "LOCK" if last == "LOCK" else "HOLD" if last == "HOLD" else "FORCED" if last is True else "IF"
            old = None
            if b == p and act in ("IF", "LOCK", "HOLD"):
                after = sum(1 for dd, _ in M.games.get(b, ()) if dd > d and N.week_of(dd) == w)
                old = round(OLD_V(mu.get(b, 0.0), after), 1) if after else 0.0
            ch.append({"date": d, "player": L.pname(b), "plays": round(q, 2), "exp": round(m, 1), "th": round(th, 1), "act": act, "free": b != p, "old": old})
        slots.append({"slot": s, "player": L.pname(p), "worth": round(v, 1), "chances": ch})
    return {"slots": slots, "total": round(sum(v for _, _, v, _ in out), 1),
            "bench": [{"player": L.pname(p), "value": round(val[p], 1)} for p in ids if p not in reg.values()]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/plan.json")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    L = N.League()
    w = N.week_of(a.today)
    M = R.Model(L, R.load_params())
    Rq = K.ratios(L, M, a.today)
    mu = proj_means(L)
    res = {"week": w, "today": a.today, "teams": {}}
    for name in sorted(set(L.name.values())):
        res["teams"][name] = team_plan(L, M, Rq, name, w, a.today, mu)
    json.dump(res, open(a.out, "w"), separators=(",", ":"))
    print(f"wrote {a.out}: week {w}, teams {list(res['teams'])}")


if __name__ == "__main__":
    main()
