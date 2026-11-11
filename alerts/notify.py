#!/usr/bin/env python3
"""Short phone alerts via ntfy. Silent unless one of Jack's starters needs a decision.

    notify.py --live site/data/live.json --state state/notified.json [--dry]

Rules (Jack, 10 Nov 2026): alerts are 1-3 short lines, and a pre-game final check goes out
WHEN AND ONLY WHEN a starter with a game today is Questionable/Day-To-Day (pinged once,
20-100 min before tip) or Doubtful/Out (pinged once, any time today). Each (player, status,
game date) is sent at most once. NTFY_TOPIC comes from the environment (GitHub secret).
"""
import argparse, datetime as dt, json, os, sys, urllib.request

ME = "jackhill1617"
ME_NAME = "Jack"
ALIAS = {"GS": "GSW", "NY": "NYK", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS", "PHO": "PHX", "BKN": "BRK", "CHA": "CHO"}
HARD, SOFT = {"out", "doubtful", "suspended"}, {"questionable", "day-to-day", "gtd"}
SHORT = {"out": "OUT", "doubtful": "DOUBT", "suspended": "SUSP", "questionable": "Q", "day-to-day": "DTD", "gtd": "GTD"}
WINDOW = (20, 100)  # minutes before tip for questionable-type pings


def canon(t):
    t = (t or "").upper()
    return ALIAS.get(t, t)


def decide(live, state, now):
    users = {u.get("display_name", "").lower(): u["user_id"] for u in live["users"]}
    ro = next((r for r in live["rosters"] if r["owner_id"] == users.get(ME)), None)
    if not ro:
        return []
    inj = {i["player"].lower(): i for i in live["espn_injuries"]}
    tips = {}
    for g in live["schedule"]:
        if g["status"] in ("STATUS_FINAL", "STATUS_IN_PROGRESS"):
            continue
        when = dt.datetime.fromisoformat(g["date"].replace("Z", "+00:00"))
        for t in g["teams"]:
            tips.setdefault(canon(t), []).append(when)
    alerts = []
    for pid in ro.get("starters") or []:
        p = live["players"].get(pid)
        if not p:
            continue
        status = (inj.get(p["name"].lower(), {}).get("status") or p.get("inj") or "").lower()
        if status not in HARD | SOFT:
            continue
        nxt = sorted(w for w in tips.get(canon(p["team"]), []) if w > now - dt.timedelta(minutes=5))
        if not nxt or nxt[0].date() != now.date() and (nxt[0] - now) > dt.timedelta(hours=14):
            continue
        tip, mins = nxt[0], (nxt[0] - now).total_seconds() / 60
        if status in SOFT and not WINDOW[0] <= mins <= WINDOW[1]:
            continue
        key = f"{p['name']}|{status}|{tip.date()}"
        if key not in state:
            alerts.append((key, f"{p['name']} {SHORT[status]} · tip {tip.astimezone(dt.timezone(dt.timedelta(hours=0))).strftime('%H:%M')}Z"))
    return alerts


def lock_alerts(plan, locked, state):
    """slots whose finished score beats the rest of the week (plan says LOCK) and that Jack hasn't marked locked"""
    done = set(locked["players"]) if locked and locked.get("week") == plan["week"] else set()
    out = []
    for sl in plan["teams"][ME_NAME]["slots"]:
        c = sl["chances"][0] if sl["chances"] else None
        if c and c["act"] == "LOCK" and sl["player"] not in done:
            key = f"lock|{sl['player']}|{c['exp']}|{plan['week']}"
            if key not in state:
                old = c.get("old")
                tag = "" if old is None else " both agree" if c["exp"] >= old else f" engine only, old rule holds ({old})"
                out.append((key, f"LOCK {sl['player']} {c['exp']}{tag}"))
    return out


def send(topic, title, lines):
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data="\n".join(lines).encode(), headers={"Title": title, "Priority": "4"})
    urllib.request.urlopen(req, timeout=20).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="site/data/live.json")
    ap.add_argument("--state", default="state/notified.json")
    ap.add_argument("--plan", default="site/data/plan.json")
    ap.add_argument("--locked", default="site/data/locked.json")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    live = json.load(open(a.live))
    state = json.load(open(a.state)) if os.path.exists(a.state) else {}
    now = dt.datetime.now(dt.timezone.utc)
    batches = [("Final check", decide(live, state, now))]
    if os.path.exists(a.plan):
        plan = json.load(open(a.plan))
        locked = json.load(open(a.locked)) if os.path.exists(a.locked) else None
        batches.append(("LOCK NOW", lock_alerts(plan, locked, state)))
    batches = [(t, al) for t, al in batches if al]
    if not batches:
        print("no alerts")
        return 0
    topic = os.environ.get("NTFY_TOPIC")
    for title, alerts in batches:
        lines = [t for _, t in alerts[:3]] + ([f"+{len(alerts) - 3} more"] if len(alerts) > 3 else [])
        print(title, "|", " / ".join(lines))
        if a.dry:
            continue
        if not topic:
            print("NTFY_TOPIC not set", file=sys.stderr)
            return 1
        send(topic, title, lines)
        for k, _ in alerts:
            state[k] = now.isoformat(timespec="minutes")
    if a.dry:
        return 0
    state = {k: v for k, v in state.items() if v >= (now - dt.timedelta(days=3)).isoformat()}
    os.makedirs(os.path.dirname(a.state), exist_ok=True)
    json.dump(state, open(a.state, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
