#!/usr/bin/env python3
"""Apply lock taps made on the phone to site/data/locked.json.

    sync_locks.py --locked site/data/locked.json --week 4

The site posts {"w": week, "p": player, "l": true|false} to a private ntfy topic (env NTFY_CMD_TOPIC,
a GitHub secret). Messages are kept ~12h by ntfy, so each run replays the last 12h in order.
"""
import argparse, json, os, sys, urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locked", default="site/data/locked.json")
    ap.add_argument("--week", type=int, required=True)
    a = ap.parse_args()
    topic = os.environ.get("NTFY_CMD_TOPIC")
    cur = json.load(open(a.locked)) if os.path.exists(a.locked) else {"week": a.week, "players": []}
    if cur.get("week") != a.week:
        cur = {"week": a.week, "players": []}
    if not topic:
        print("NTFY_CMD_TOPIC not set; skipping")
        return 0
    raw = urllib.request.urlopen(f"https://ntfy.sh/{topic}/json?poll=1&since=12h", timeout=30).read().decode()
    players, n = list(cur["players"]), 0
    for line in raw.splitlines():
        try:
            m = json.loads(line)
            if m.get("event") != "message":
                continue
            c = json.loads(m["message"])
            if c.get("w") != a.week:
                continue
            p = str(c["p"])
            if c.get("l") and p not in players:
                players.append(p); n += 1
            elif not c.get("l") and p in players:
                players.remove(p); n += 1
        except Exception:
            continue
    json.dump({"week": a.week, "players": players}, open(a.locked, "w"))
    print(f"applied {n} change(s); locked this week: {players}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
