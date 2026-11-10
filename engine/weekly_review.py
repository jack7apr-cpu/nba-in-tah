#!/usr/bin/env python3
"""Weekly review + safe refit.

    weekly_review.py [--out site/data/review.json] [--refit]

review: for every finished week, what each manager's counted locks scored vs what the lock engine would have
scored with only the information available at the time, plus the biggest individual differences.
refit (optional): fit the risk model on all finished weeks but the latest, test it on that latest week against the
current parameters, and only replace risk_params.json when it is clearly better (MAE at least 0.05 lower).
"""
import argparse, contextlib, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbadata as N, risk as R, lock as K


def review(L, weeks):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        det = K.backtest(L, weeks)
    out = buf.getvalue()
    mg = {}
    for m in re.finditer(r"^(\w+)\s+actual\s+([\d.]+)\s+engine\s+([\d.]+)\s+\(\s*([+-][\d.]+)\)\s+never-lock\s+([\d.]+)\s+perfect hindsight\s+([\d.]+)", out, re.M):
        who, act, eng, gain, nl, best = m.groups()
        mg[who] = {"actual": float(act), "engine": float(eng), "gain": float(gain), "never_lock": float(nl), "hindsight": float(best)}
    lg = re.search(r"LEAGUE\s+managers\s+([\d.]+)\s+engine\+risk model\s+([\d.]+)\s+engine\+raw Sleeper\s+([\d.]+)\s+never-lock\s+([\d.]+)\s+hindsight\s+([\d.]+)", out)
    big = sorted(det, key=lambda x: -abs(x[3] - x[4]))[:12]
    return {"weeks": weeks, "managers": mg,
            "league": dict(zip(("managers", "engine", "engine_raw", "never_lock", "hindsight"), map(float, lg.groups()))) if lg else None,
            "misses": [{"wk": w, "mgr": who, "player": nm, "took": pts, "engine": round(e, 1), "games": [g if g == "DNP" else round(g, 1) for g in gl]} for w, who, nm, pts, e, gl in big]}


def refit(L, done):
    if len(done) < 3:
        return "need 3 finished weeks to refit safely"
    train, test = done[:-1], [done[-1]]
    ptrain, ptest = R.targets(L, tuple(train)), R.targets(L, tuple(test))
    cand, _ = R.fit(L, ptrain)
    cur = R.load_params()
    mc, mu = R.score(R.evaluate(L, cand, ptest))["model_mae"], R.score(R.evaluate(L, cur, ptest))["model_mae"]
    if mc < mu - 0.05:
        json.dump(cand.as_dict(), open(R.PARAMS_FILE, "w"), indent=1)
        return f"refit accepted: test MAE {mu:.2f} -> {mc:.2f} on week {test[0]}"
    return f"kept current params: candidate MAE {mc:.2f} vs current {mu:.2f} on week {test[0]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/review.json")
    ap.add_argument("--refit", action="store_true")
    a = ap.parse_args()
    L = N.League()
    cur = (N.load(os.path.join(N.ROOT, "state.json")) or {}).get("week", 1)
    done = [w for w in range(1, cur) if N.load(f"{L.d}/matchups/week_{w:02d}.json")]
    if not done:
        print("no finished weeks yet")
        return
    msg = refit(L, done) if a.refit else "no refit requested"
    rv = review(L, done)
    rv["refit"] = msg
    json.dump(rv, open(a.out, "w"), separators=(",", ":"))
    print(msg, "| weeks", done, "| league", rv["league"])


if __name__ == "__main__":
    main()
