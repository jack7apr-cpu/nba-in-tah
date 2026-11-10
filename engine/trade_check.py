#!/usr/bin/env python3
"""Test ONE trade idea against the data, after the owner has stated his reasoning.
    trade_check.py --with CJ --give "Rome Odunze,2027R2" --get "Kenneth Walker" [--reason "why I want this"] [--me 10]
Prints: his reasoning back, market values, what the partner sees, lineup now/dynasty effect for both, rule checks, a verdict, and the best alternatives with the same partner."""
import argparse, os, re, sys, types
sys.path.insert(0, os.path.dirname(__file__))
import engine as e
import market as M
import sleeper as S


def find_roster(c, q):
    q = q.lower()
    hits = [r for r in c.rosters if str(r["roster_id"]) == q or q == (c.manager.get(r["roster_id"]) or "").lower() or q in c.owner[r["roster_id"]].lower()]
    if len(hits) != 1:
        sys.exit("partner must match one of: " + ", ".join(f"{r['roster_id']}={c.manager.get(r['roster_id'])}" for r in c.rosters))
    return hits[0]


def items(c, text, roster):
    out = []
    for tok in [x.strip() for x in text.split(",") if x.strip()]:
        m = re.fullmatch(r"(\d{4})\s*R(\d)", tok, re.I)
        if m:
            out.append((m.group(1), int(m.group(2))))
            continue
        q = S.norm(tok)
        hit = [p for p in roster.get("players") or [] if q in S.norm(c.name(p))]
        if len(hit) != 1:
            sys.exit(f"'{tok}' matched {len(hit)} players on that roster: {[c.name(p) for p in hit]}")
        out.append(hit[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with", dest="partner", required=True)
    ap.add_argument("--give", required=True)
    ap.add_argument("--get", required=True)
    ap.add_argument("--reason", default="")
    ap.add_argument("--me", default="10")
    a = ap.parse_args()
    c = e.Ctx(); m = M.Market(c)
    me, ot = c.team(a.me), find_roster(c, a.partner)
    give, get = items(c, a.give, me), items(c, a.get, ot)
    isp = lambda x: isinstance(x, tuple)
    val = lambda x: m.pick(*x) if isp(x) else m.player(x)
    lbl = lambda x: f"{x[0]} R{x[1]}" if isp(x) else f"{c.name(x)} ({c.pos(x)}, {(c.db.get(x) or {}).get('age') or '?'})"
    mode = e.modes(c)[ot["roster_id"]][0]
    age = lambda x: None if isp(x) else (c.db.get(x) or {}).get("age")
    P = m.P
    vg, vr = P.package([val(x) for x in give]), P.package([val(x) for x in get])
    pg = P.package([M.adj_value(val(x), "pick" if isp(x) else "p", age(x), mode) for x in give])
    pl = P.package([M.adj_value(val(x), "pick" if isp(x) else "p", age(x), mode) for x in get])
    gp, tp = [x for x in give if not isp(x)], [x for x in get if not isp(x)]
    mine_after = [p for p in me["players"] if p not in gp] + tp
    theirs_after = [p for p in ot["players"] if p not in tp] + gp
    act = lambda r, ps: e.active({"players": ps, "reserve": r.get("reserve"), "taxi": r.get("taxi")})
    my_now = c.ros_value(act(me, mine_after)) - c.ros_value(e.active(me))
    t_now = c.ros_value(act(ot, theirs_after)) - c.ros_value(e.active(ot))
    cap = len(c.positions) + c.lg["settings"].get("reserve_slots", 0) + c.lg["settings"].get("taxi_slots", 0)
    limits = {k[len("position_limit_"):].upper(): v for k, v in c.lg["settings"].items() if k.startswith("position_limit_")}
    def why(ps):
        cnt = {}
        for p in ps:
            cnt[c.pos(p)] = cnt.get(c.pos(p), 0) + 1
        bad = [f"{k} {cnt[k]}>{v}" for k, v in limits.items() if cnt.get(k, 0) > v]
        return (["roster size %d>%d" % (len(ps), cap)] if len(ps) > cap else []) + bad
    fails = [f"{c.manager.get(r['roster_id'])}: {', '.join(w)}" for r, ps in ((me, mine_after), (ot, theirs_after)) for w in [why(ps)] if w]
    ok = not fails and M.roster_ok(c, mine_after, limits, cap) and M.roster_ok(c, theirs_after, limits, cap)
    prem = c.premium(); nt = c.no_trade()
    broken = [c.name(x) for x in gp if x in nt or (x in prem and vr < prem[x] * vg)]
    ratio = pg / max(pl, 1e-9)
    med, low = m.floor(0.5), m.floor(0.25)
    verdict = "LIKELY to be accepted" if ratio >= med else "a STRETCH" if ratio >= low else "UNLIKELY to be accepted"
    print(f"=== YOUR REASONING (stated first) ===\n{a.reason or '(none given: ask him why before sharing numbers)'}\n")
    print(f"=== THE FACTS ===\n{c.manager.get(me['roster_id'], 'You')} gives: {', '.join(map(lbl, give))}\n{c.manager.get(ot['roster_id'])} gives: {', '.join(map(lbl, get))}")
    print(f"\nMarket value (top player = 100, package-discounted): you give {vg:.1f}, you get {vr:.1f}  ->  you {'win' if vr > vg else 'lose'} {abs(vr - vg):.1f} on the market")
    print(f"What {c.manager.get(ot['roster_id'])} sees ({'contender' if mode >= 1 else 'rebuilder'}): receives {pg:.1f} vs gives {pl:.1f} = {ratio:.2f}x  (past accepted trades: median {med:.2f}, 25th pct {low:.2f})  -> {verdict}")
    print(f"Lineup, rest of season: you {my_now:+.0f} pts, them {t_now:+.0f} pts")
    print(f"Rule checks: roster/position limits {'OK' if ok else 'FAIL (' + '; '.join(fails) + ')'}; protected/premium rules {'OK' if not broken else 'BROKEN for ' + ', '.join(broken)}; trade deadline week {c.lg['settings'].get('trade_deadline')}, now week {c.week}")
    print("\n=== BETTER OR SIMILAR IDEAS WITH THE SAME PARTNER ===")
    ns = types.SimpleNamespace(team=a.me, top=3, per_partner=3, pool=8, now=1.0, future=0.25, floor=med, min_now=0.0, min_future=0.0, partner=ot["roster_id"])
    M.cmd_trades(c, m, ns)


if __name__ == "__main__":
    main()
