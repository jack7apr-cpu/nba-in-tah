#!/usr/bin/env python3
"""Replay Sleeper's per-game projections against what actually happened (league scoring), by week and tier.

    replay.py [--weeks 1,2,3] [--before YYYY-MM-DD]

Sleeper keeps one projection row per game, overwritten up to tip-off, so this measures GAME-DAY accuracy (late
scratches already show as blank rows). Lock decisions are made days earlier: see risk.py fit for that replay."""
import argparse, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N


def line(rows, lab):
    if len(rows) < 3:
        return
    P, A = [r[0] for r in rows], [r[1] for r in rows]
    print(f"  {lab:22} n={len(rows):5}  r {N.corr(P, A):.3f}  MAE {st.mean(abs(a - p) for p, a in zip(P, A)):5.2f}  "
          f"bias {st.mean(a - p for p, a in zip(P, A)):+5.2f}  sat out {1 - st.mean(r[2] for r in rows):5.1%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", default="1,2,3")
    ap.add_argument("--before", default="9999")
    a = ap.parse_args()
    weeks = {int(x) for x in a.weeks.split(",")}
    L = N.League()
    rows = []
    for (pid, d) in L.proj:
        if N.week_of(d) in weeks and d < a.before:
            p = L.projected(pid, d)
            rows.append((p, L.actual(pid, d), L.played(pid, d), N.week_of(d)))
    blank = [r for r in rows if r[0] == 0]
    pos = [r for r in rows if r[0] > 0]
    print(f"blank projection rows {len(blank)} (played anyway: {sum(r[2] for r in blank)}, avg {st.mean([r[1] for r in blank if r[2]] or [0]):.1f} pts)")
    print("projected > 0 (sat-out games count as 0):")
    line(pos, "all")
    for w in sorted(weeks):
        line([r for r in pos if r[3] == w], f"week {w}")
    for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 99)):
        line([r for r in pos if lo <= r[0] < hi], f"projected {lo}-{hi}")
    print("only games he played:")
    line([r for r in pos if r[2]], "all")
    for lo, hi in ((10, 20), (20, 30), (30, 99)):
        line([r for r in pos if r[2] and lo <= r[0] < hi], f"projected {lo}-{hi}")


if __name__ == "__main__":
    main()
