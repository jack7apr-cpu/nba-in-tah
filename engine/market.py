"""League-calibrated trade market. Values come from how THESE owners priced players (startup draft + 33 past trades):
steep rank->value curve above a replacement level, package discount for depth, age/mode adjustments, pick values fit to trades.

    market.py backtest            calibrate, print fit + guards (exit 1 if the curve is flat/degenerate)
    market.py trades TEAM         trades the partner would accept that raise TEAM's lineup now and dynasty value
"""
import glob, itertools, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import engine as e
import sleeper as S

SKILL = {"QB", "RB", "WR", "TE"}
CLIFF = {"RB": 26, "WR": 28, "TE": 29, "QB": 34}
TAIL = 0.04  # depth keeps a sliver of value so scrub-for-scrub swaps are not 0:0
SLOT_RANK = lambda rnd: 16 * (rnd - 1) + 8.5  # an already-slotted startup pick: mid-round overall rank


class Params:
    """k: steepness, r0: rank scale, repl: replacement rank (worth 0), pkg: weight decay for each extra asset in a package,
    age: rank penalty per year past the position cliff, pk: rank-equivalent of a rookie-draft R1/R2/R3, yr: yearly pick discount."""
    def __init__(self, k=1.6, r0=40, repl=130, pkg=0.8, age=0.08, pk=(45, 100, 160), yr=0.9):
        self.k, self.r0, self.repl, self.pkg, self.age, self.pk, self.yr = k, r0, repl, pkg, age, tuple(pk), yr

    def raw(self, rank):
        return 100 * (1 + rank / self.r0) ** -self.k

    def value(self, rank):
        """0 at/below replacement; convex above it, so one star outweighs several mid players."""
        rr = self.raw(self.repl)
        return (max(0.0, self.raw(rank) - rr) + TAIL * self.raw(rank)) / (100 - rr) * 100

    def pick(self, season, rnd, cur_season, rank_of_slot=False):
        if rank_of_slot or int(season) <= int(cur_season):
            return self.value(SLOT_RANK(rnd))
        yrs = int(season) - int(cur_season)
        r = self.pk[min(rnd, 3) - 1] + 60 * max(0, rnd - 3)
        return self.value(r) * self.yr ** (yrs - 1)

    def package(self, vals):
        return sum(v * self.pkg ** i for i, v in enumerate(sorted(vals, reverse=True)))


def age_rank(rank, pos, age, slope):
    """older than the position cliff -> market sees him ranked worse; <=23 gets a small boost."""
    if not age:
        return rank
    return rank * (1 + slope * max(0, age - CLIFF.get(pos, 30))) * (0.95 if age <= 23 else 1)


def side_values(side, P, cur_season):
    """side = list of ('p', base_rank, pos, age) or ('pk', season, round[, True])."""
    return [P.value(age_rank(x[1], x[2], x[3], P.age)) if x[0] == "p" else P.pick(x[1], x[2], cur_season, len(x) > 3) for x in side]


def balances(sides_list, P, cur_season):
    out = []
    for a, b in sides_list:
        va, vb = P.package(side_values(a, P, cur_season)), P.package(side_values(b, P, cur_season))
        out.append(min(va, vb) / max(va, vb) if max(va, vb) > 0 else 0.0)
    return out


def loss(bal):
    return sum(min(math.log(1 / max(b, 1e-6)), math.log(4)) for b in bal) / len(bal)  # mean log-imbalance clipped at 4:1 (outlier trades); 0 = even


def shuffled_share(sides_list, P, cur_season):
    """share within 2:1 if each trade's first side were paired with the next trade's second side (null model)."""
    n = len(sides_list)
    return sum(b >= 0.5 for b in balances([(sides_list[i][0], sides_list[(i + 1) % n][1]) for i in range(n)], P, cur_season)) / n


def guards(P, bal, cur_season, sides_list=None):
    """Fail on a flat or degenerate scale. Returns list of failure strings."""
    bad = []
    v = P.value
    if not v(1) > v(25) > v(60) > v(100) >= 0:
        bad.append("value not strictly decreasing with rank")
    if v(1) < 6 * v(60) or v(10) < 3 * v(60):
        bad.append(f"curve too flat: v1={v(1):.0f} v10={v(10):.0f} v60={v(60):.0f}")
    if v(P.repl + 40) > 0.25 * v(60):
        bad.append("replacement-level players keep real value")
    if P.pick("2027", 1, cur_season) <= P.pick("2027", 2, cur_season) <= 0 or P.pick("2027", 2, cur_season) < P.pick("2027", 3, cur_season):
        bad.append("pick values not ordered R1>R2>=R3")
    if P.pick("2028", 1, cur_season) >= P.pick("2027", 1, cur_season):
        bad.append("future picks not discounted")
    if sides_list is not None:
        share = sum(b >= 0.5 for b in bal) / len(bal)
        base = shuffled_share(sides_list, P, cur_season)
        if share < base + 0.10:
            bad.append(f"scale barely beats mismatched trades: {share:.0%} of real trades within 2:1 vs {base:.0%} when sides are paired at random")
    return bad


def fit(sides_list, cur_season):
    """Grid search for the Params under which past accepted trades look most even. Coarse on purpose (33 noisy trades)."""
    best = None
    for k, r0, repl, pkg, age, pk1, pk2, yr in itertools.product((1.0, 1.5, 2.0, 3.0, 4.0), (20, 40, 80, 160), (100, 130, 160, 200), (1.0, 0.8, 0.6), (0, 0.08, 0.16), (25, 45, 70, 100), (80, 110, 150, 200), (0.85, 0.95)):
        P = Params(k, r0, repl, pkg, age, (pk1, pk2, pk2 + 60), yr)
        if guards(P, [1] * 99, cur_season):  # cheap structural guards before scoring
            continue
        L = loss(balances(sides_list, P, cur_season)) + 0.05 * abs(math.log(k / 2)) + 0.05 * abs(math.log(r0 / 40))  # weak prior: 33 noisy trades barely identify the shape, prefer a steep, moderate one
        if best is None or L < best[0]:
            best = (L, P)
    return best


FC_URL = "https://api.fantasycalc.com/values/current?isDynasty=true&numQbs={qb}&numTeams={n}&ppr={ppr}"


def load_external(c, max_age=86400):
    """FantasyCalc dynasty values (public JSON, refreshed daily) in THIS league's shape: QBs, teams, PPR from league.json.
    Returns ({sleeper_id: value}, {(season, round): value}) scaled so the top player = 100; ({}, {}) if unavailable."""
    qbs = 2 if any(s in ("SUPER_FLEX", "QB") and c.positions.count(s) > 1 or s == "SUPER_FLEX" for s in set(c.positions)) else 1
    ppr = c.scoring.get("rec", 0)
    path = f"{c.d}/fantasycalc.json"
    try:
        if not os.path.exists(path) or __import__("time").time() - os.path.getmtime(path) > max_age:
            data = S.http_get(FC_URL.format(qb=qbs, n=c.lg["total_rosters"], ppr=ppr))
            if data:
                S.save(path, data)
    except S.SleeperError:
        pass
    data = S.load(path) or []
    if not data:
        return {}, {}
    top = max(x["value"] for x in data)
    players, picks = {}, {}
    for x in data:
        v = 100 * x["value"] / top
        pl = x["player"]
        if pl.get("sleeperId"):
            players[str(pl["sleeperId"])] = v
        elif pl.get("position") == "PICK":
            parts = pl["name"].split()  # "2027 1st" (generic) vs "2027 1st (Early)"
            if len(parts) == 2 and parts[1][0].isdigit():
                picks[(parts[0], int(parts[1][0]))] = v
    return players, picks


class Market:
    def __init__(self, c, params=None):
        self.c = c
        self.ext_players, self.ext_picks = load_external(c)
        self.draft_rank = {}
        for f in glob.glob(f"{c.d}/drafts/*_picks.json"):
            for p in S.load(f) or []:
                self.draft_rank[p["player_id"]] = p["pick_no"]
        skill = [p for p in c.proj.get(c.week, {}) if c.pos(p) in SKILL]
        score = {p: sum(c.pts(p, w) for w in c.weeks_left()) for p in skill}
        self.cur_rank = {p: i + 1 for i, p in enumerate(sorted(score, key=lambda p: -score[p]))}
        self.ros = score
        wk = max(len(c.weeks_left()), 1)
        self.repl_ppw = {}  # weekly points of a replacement-level (3rd best unrostered) player at each position
        for pos in SKILL:
            fa = sorted((score[p] / wk for p in score if p not in c.rostered and c.pos(p) == pos), reverse=True)
            self.repl_ppw[pos] = fa[2] if len(fa) > 2 else 0.0
        self.trades = self.load_trades()
        self.trades = self.drop_reversals(self.trades)
        self.sides = [self.trade_sides(t) for t in self.trades]
        self.sides = [s for s in self.sides if len(s) == 2]
        if params:
            self.P, self.loss = params, None
        else:
            self.loss, self.P = fit(self.sides, c.season)
        self.bal = balances(self.sides, self.P, c.season)

    def rank(self, pid):
        c = self.c
        return age_rank(self.base_rank(pid), c.pos(pid), (c.db.get(pid) or {}).get("age"), self.P.age)

    def base_rank(self, pid):
        """market rank: owners' startup-draft price blended with production; hurt players keep their draft price."""
        c = self.c
        cur = min(self.cur_rank.get(pid, 250), 250)
        dr = self.draft_rank.get(pid)
        injured = (c.db.get(pid) or {}).get("injury_status") in ("Out", "IR", "PUP", "Suspended")
        r = dr if dr and injured else 0.55 * dr + 0.45 * cur if dr else cur
        if dr and dr > 200 and not injured:
            r = min(r, 0.3 * dr + 0.7 * cur)
        return r

    def player(self, pid):
        """dynasty market value (FantasyCalc, top = 100); falls back to this league's own startup-draft price."""
        if pid in self.ext_players:
            return self.ext_players[pid]
        return self.P.value(self.rank(pid)) if not self.ext_players else 0.0  # unlisted = replacement level in the outside market

    def pick(self, season, rnd):
        if (season, rnd) in self.ext_picks:
            return self.ext_picks[(season, rnd)]
        return self.P.pick(season, rnd, self.c.season)

    def load_trades(self):
        out = []
        for f in sorted(glob.glob(f"{self.c.d}/transactions/*.json")):
            out += [t for t in S.load(f) if t["type"] == "trade" and t["status"] == "complete"]
        return out

    @staticmethod
    def drop_reversals(trades):
        """a trade later undone by the same two rosters swapping the same assets back is noise, not a price signal."""
        def key(t, flip):
            ids = sorted(t["roster_ids"])
            assets = {(p, r) for p, r in (t.get("adds") or {}).items()} | {(f"{k['season']}R{k['round']}", k["owner_id"]) for k in t.get("draft_picks") or []}
            return (tuple(ids), frozenset((a, (ids[1] if r == ids[0] else ids[0]) if flip else r) for a, r in assets))
        seen, drop = {}, set()
        for i, t in enumerate(trades):
            if key(t, True) in seen:
                drop |= {i, seen[key(t, True)]}
            seen[key(t, False)] = i
        return [t for i, t in enumerate(trades) if i not in drop]

    def trade_sides(self, t):
        rec = {rid: [] for rid in t["roster_ids"]}
        for pid, rid in (t.get("adds") or {}).items():
            if self.c.pos(pid) in SKILL | {"DB"}:
                rec[rid].append(("p", self.base_rank(pid), self.c.pos(pid), (self.c.db.get(pid) or {}).get("age")))
        for pk in t.get("draft_picks") or []:
            rec[pk["owner_id"]].append(("pk", pk["season"], pk["round"], int(pk["season"]) <= int(self.c.season)))
        return list(rec.values())

    def ext_side_values(self):
        """past trades re-priced at today's outside market (noisy, but a neutral yardstick for what owners accept)."""
        out = []
        for t in self.trades:
            rec = {rid: [] for rid in t["roster_ids"]}
            for pid, rid in (t.get("adds") or {}).items():
                if self.c.pos(pid) in SKILL:
                    rec[rid].append(self.ext_players.get(pid, 0.0))
            for pk in t.get("draft_picks") or []:
                rec[pk["owner_id"]].append(self.pick(pk["season"], pk["round"]))
            if len(rec) == 2:
                out.append(list(rec.values()))
        return out

    def floor(self, q=0.25):
        b = sorted(self.bal)
        if self.ext_players:
            b = sorted(min(x, y) / max(x, y) for x, y in ((self.P.package(a), self.P.package(c)) for a, c in self.ext_side_values()) if max(x, y) > 0) or b
        return b[int(q * len(b))]

    def top_floor(self, q=0.25):
        """a partner's best incoming asset vs its best outgoing one, lesser/greater, in past trades: depth does not buy a star."""
        r = []
        sides = self.ext_side_values() if self.ext_players else [(side_values(a, self.P, self.c.season), side_values(b, self.P, self.c.season)) for a, b in self.sides]
        for a, b in sides:
            ta, tb = max(a, default=0), max(b, default=0)
            if max(ta, tb) > 0:
                r.append(min(ta, tb) / max(ta, tb))
        r.sort()
        return r[int(q * len(r))] if r else 0.0

    def check(self):
        return guards(self.P, self.bal, self.c.season, self.sides)


def owned_picks(c, rid, years=(1, 2, 3), rounds=(1, 2, 3)):
    """(season, round) rookie picks a roster owns: its own minus those traded away, plus those acquired."""
    traded = S.load(f"{c.d}/traded_picks.json") or []
    owned = {(str(int(c.season) + y), r) for y in years for r in rounds}
    for tp in traded:
        if tp["roster_id"] == rid and tp["owner_id"] != rid:
            owned.discard((tp["season"], tp["round"]))
    for tp in traded:
        if tp["owner_id"] == rid and tp["roster_id"] != rid and int(tp["season"]) > int(c.season):
            owned.add((tp["season"], tp["round"]))
    return sorted(owned)


def adj_value(item_value, kind, age, mode_now, pos=None):
    """what a particular owner thinks an asset is worth. contender (mode_now==1): vets full price, picks cheap.
    rebuilder: vets 28+ at a discount, youth and picks at a premium."""
    if mode_now >= 1.0:
        return item_value * (0.8 if kind == "pick" else 1.0)
    if kind == "pick":
        return item_value * 1.2
    if age and age >= 28:
        return item_value * 0.6
    return item_value * (1.1 if age and age <= 24 else 1.0)


def roster_ok(c, pids, limits, cap):
    """legal after the trade: not over the roster cap or position limits, and every starting slot still fillable."""
    if len(pids) > cap:
        return False
    cnt = {}
    for p in pids:
        cnt[c.pos(p)] = cnt.get(c.pos(p), 0) + 1
    if any(cnt.get(k, 0) > v for k, v in limits.items()):
        return False
    slots = [s for s in c.positions if s not in e.NON_STARTING]
    return len(c.best_lineup(pids, c.week)) >= len(slots) - 0  # K/DEF count too: no empty starting slot


def future_pts(c, m, pid):
    """production-based dynasty points ABOVE REPLACEMENT over the next 3 seasons (independent of market price)."""
    pos = c.pos(pid)
    if pos not in SKILL:
        return 0.0
    wk = max(len(c.weeks_left()), 1)
    base = max(0.0, sum(c.pts(pid, w) for w in c.weeks_left()) / wk - m.repl_ppw[pos])
    age = (c.db.get(pid) or {}).get("age")
    return sum(base * 17 * e.age_factor(pos, (age or 0) + y if age else None) for y in range(1, 4))


def cmd_trades(c, m, a):
    me = c.team(a.team)
    keep, premium = c.no_trade(), c.premium()
    mode = e.modes(c)
    P = m.P
    cap = len(c.positions) + c.lg["settings"].get("reserve_slots", 0) + c.lg["settings"].get("taxi_slots", 0)
    limits = {k[len("position_limit_"):].upper(): v for k, v in c.lg["settings"].items() if k.startswith("position_limit_")}
    age = lambda p: (c.db.get(p) or {}).get("age")
    isp = lambda it: isinstance(it, tuple)
    val = lambda it: m.pick(*it) if isp(it) else m.player(it)
    lbl = lambda it: f"{it[0]} R{it[1]}" if isp(it) else f"{c.name(it)} ({c.pos(it)}, {age(it) or '?'})"
    my_all = me.get("players") or []
    top_floor = m.top_floor(0.5)
    memo = {}
    ros = lambda ps: memo.setdefault(frozenset(ps), c.ros_value(list(ps)))
    base_me = ros(e.active(me))
    # points per market unit: scale for valuing picks in the same currency as production
    top = sorted(m.ros, key=lambda p: -m.player(p))[:80]
    ppu = sum(future_pts(c, m, p) for p in top) / max(1e-9, sum(m.player(p) for p in top))
    fut = lambda it: val(it) * ppu  # dynasty value in points: outside market price x points-per-market-unit (injured stars keep theirs)
    my_give = [p for p in my_all if p not in keep and c.pos(p) in SKILL and val(p) > 0] + [(k[0], k[1]) for k in owned_picks(c, me["roster_id"])]
    my_give = sorted(my_give, key=lambda it: -val(it))[:a.pool + 6]
    out = []
    for r in c.rosters:
        if r["roster_id"] == me["roster_id"] or (getattr(a, "partner", None) and r["roster_id"] != a.partner):
            continue
        theirs = r.get("players") or []
        t_mode = mode[r["roster_id"]][0]
        t_active = e.active(r)
        base_t = ros(t_active)
        targets = sorted([p for p in theirs if c.pos(p) in SKILL and val(p) > 0], key=lambda p: -val(p))[:a.pool + 6]
        for give in e.combos(my_give, (1, 2, 3)):
            gp = [x for x in give if not isp(x)]
            for get in e.combos(targets, (1, 2)):
                vg, vr = P.package([val(x) for x in give]), P.package([val(x) for x in get])
                if vr <= 0 or vg <= 0:
                    continue
                if any(x in premium and vr < premium[x] * vg for x in give if not isp(x)):
                    continue  # premium players only go for a clearly better return
                # partner's own valuation (mode-adjusted) of what it gets vs gives
                pg = P.package([adj_value(val(x), "pick" if isp(x) else "p", None if isp(x) else age(x), t_mode) for x in give])  # what partner receives
                pl = P.package([adj_value(val(x), "pick" if isp(x) else "p", None if isp(x) else age(x), t_mode) for x in get])  # what partner gives up
                if pg / max(pl, 1e-9) < a.floor * (0.6 if t_mode >= 1.0 else 1.0):
                    continue  # cheap pre-check before any lineup math (contenders may credit lineup gain below)
                if max(val(x) for x in give) < top_floor * max(val(x) for x in get):
                    continue  # partner's best incoming asset must be in the range owners accept for their best outgoing one
                theirs_after = [p for p in theirs if p not in get] + gp
                mine_after = [p for p in my_all if p not in gp] + list(get)
                if not roster_ok(c, theirs_after, limits, cap) or not roster_ok(c, mine_after, limits, cap):
                    continue
                t_now = ros(e.active({"players": theirs_after, "reserve": r.get("reserve"), "taxi": r.get("taxi")})) - base_t
                if t_mode >= 1.0 and t_now < -0.03 * base_t:
                    continue  # contender will not weaken its lineup
                # partner needs (value they get, in their eyes + contender lineup gain) to clear the fair floor seen in past trades
                bonus = (t_now / max(base_t, 1)) * pl * 2 if t_mode >= 1.0 else 0  # contender credits lineup gain
                if (pg + bonus) / max(pl, 1e-9) < a.floor:
                    continue
                now = ros(e.active({"players": mine_after, "reserve": me.get("reserve"), "taxi": me.get("taxi")})) - base_me
                fut_d = sum(map(fut, get)) - sum(map(fut, give))
                if now < a.min_now or fut_d < a.min_future:
                    continue
                score = a.now * now + a.future * fut_d
                out.append((score, (pg + bonus) / pl, now, fut_d, r["roster_id"], give, get, t_now))
    out.sort(key=lambda x: (-x[0], -x[1]))
    print(f"{c.owner[me['roster_id']]} trades, week {c.week} (deadline week {c.lg['settings'].get('trade_deadline')}); partner must get >= {a.floor:.2f}x what it gives in its own eyes (median of past trades; 25th pct {m.floor():.2f}).")
    seen, n, per = set(), 0, {}
    for score, bal, now, fd, rid, give, get, tn in out:
        key = (rid, tuple(map(str, get)))
        if key in seen:
            continue
        if per.get(rid, 0) >= a.per_partner:
            continue
        per[rid] = per.get(rid, 0) + 1
        seen.add(key); n += 1
        why = f"{'contender' if mode[rid][0] >= 1 else 'rebuilder'}; sees {bal:.2f}x the value it gives ({'likely' if bal >= 0.75 else 'fair' if bal >= 1.0 * m.floor(0.5) else 'stretch'}), its lineup {tn:+.0f} pts"
        print(f"  [{score:6.0f}] with {c.owner[rid]}: give {', '.join(map(lbl, give))} | get {', '.join(map(lbl, get))}\n           me: lineup {now:+.0f} pts ROS, dynasty {fd:+.0f} pts; partner: {why}")
        if n >= a.top:
            break
    if not n:
        print("  none clear every filter; loosen --floor or --min-now")


def cmd_backtest(c, m):
    P = m.P
    b = sorted(m.bal)
    print(f"{len(m.sides)} accepted trades. fit: k={P.k} r0={P.r0} repl={P.repl} pkg={P.pkg} age={P.age} picks R1/R2/R3 ranks={P.pk} yr={P.yr}; mean log-imbalance {loss(m.bal):.2f} (flat curve: {loss(balances(m.sides, Params(k=0.05, r0=1000, repl=400, pkg=1.0), c.season)):.2f})")
    print(f"  null model (sides paired at random): {shuffled_share(m.sides, P, c.season):.0%} within 2:1")
    print(f"  best-asset balance: median {m.top_floor(0.5):.2f}, 25th pct {m.top_floor():.2f}")
    print(f"  balance (smaller/larger side): median {b[len(b)//2]:.2f}, 25th pct {m.floor():.2f}, min {b[0]:.2f}; within 2:1: {sum(x >= 0.5 for x in b)}/{len(b)}")
    print(f"  value: rank1 {P.value(1):.0f}, rank10 {P.value(10):.0f}, rank30 {P.value(30):.0f}, rank60 {P.value(60):.0f}, rank100 {P.value(100):.0f}; picks 27R1 {m.pick('2027',1):.0f} R2 {m.pick('2027',2):.0f} R3 {m.pick('2027',3):.0f}")
    bad = m.check()
    for f in bad:
        print("  FAIL:", f)
    return 1 if bad else 0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["backtest", "trades"], nargs="?", default="backtest")
    ap.add_argument("team", nargs="?")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--per-partner", type=int, default=1, help="max ideas listed per trade partner")
    ap.add_argument("--pool", type=int, default=8)
    ap.add_argument("--now", type=float, default=1.0)
    ap.add_argument("--future", type=float, default=0.25)
    ap.add_argument("--floor", type=float, default=None, help="min partner-received / partner-given value (default: median of past trades' lesser/greater side)")
    ap.add_argument("--min-now", type=float, default=0.0, help="min lineup gain (pts ROS) for the team")
    ap.add_argument("--min-future", type=float, default=0.0, help="min dynasty-points change for the team")
    a = ap.parse_args()
    c = e.Ctx()
    m = Market(c)
    if a.floor is None:
        a.floor = m.floor(0.5)
    if a.cmd == "trades":
        a.team = a.team or sys.exit("team required")
        return cmd_trades(c, m, a)
    sys.exit(cmd_backtest(c, m))


if __name__ == "__main__":
    main()
