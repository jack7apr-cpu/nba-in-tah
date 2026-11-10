#!/usr/bin/env python3
"""Values-only Excel export of the almanac (no formulas, so it opens correctly everywhere).

    export_xlsx.py --data site/data --out site/almanac.xlsx      (needs openpyxl)
"""
import argparse, json, os, sys

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
except ImportError:
    sys.exit("pip install openpyxl")


def sheet(wb, name, header, rows):
    ws = wb.create_sheet(name)
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="141B30")
    for r in rows:
        ws.append(r)
    ws.freeze_panes = "A2"
    for i, h in enumerate(header, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = max(10, min(34, len(str(h)) + 4))
    return ws


def load(d, n):
    p = os.path.join(d, n)
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="site/data")
    ap.add_argument("--out", default="site/almanac.xlsx")
    a = ap.parse_args()
    F, L, O, A = load(a.data, "factfile.json"), load(a.data, "league_data.json"), load(a.data, "official.json"), load(a.data, "auto.json")
    C, P, T = load(a.data, "crystal.json"), load(a.data, "plan.json"), load(a.data, "trades.json")
    wb = Workbook(); wb.remove(wb.active)
    m = F["mgrs"]
    sheet(wb, "Managers", ["Manager", "W", "L", "Points for", "Avg week", "Best week", "Worst week", "Lock avg", "Points missed", "Perfect locks", "Slots on final game", "30+ games"],
          [[k.replace(" (GPT)", ""), v["w"], v["l"], v["pf"], v["avgweek"], v["hi"], v["lo"], v["lockavg"], v["missed"], v["perfect"], v["final"], v["g30"]] for k, v in m.items()])
    if O:
        names = sorted({n for w in O["weeks"].values() for n in w})
        sheet(wb, "Weekly scores", ["Week"] + names, [[int(w)] + [O["weeks"][w].get(n) for n in names] for w in sorted(O["weeks"], key=int)])
    if L:
        sheet(wb, "Matchups", ["Week", "Team A", "Score A", "Team B", "Score B"],
              [[int(w), x, pa, y, pb] for w, d in L["weeks"].items() for x, pa, y, pb in d["matchups"]])
        sheet(wb, "Isaac awards", ["Week", "Biggest Chud", "Shit vs Poo", "Holy Glaze", "Heaven", "Hell"],
              [[int(w)] + [d["isaac"]["awards"].get(k, "") for k in ("Biggest Chud", "Shit vs Poo", "Holy Glaze", "Heaven", "Hell")] for w, d in L["weeks"].items()])
    sheet(wb, "Locks", ["Week", "Manager", "Slot", "Player", "Counted", "Best game", "Missed", "When"],
          [[l["wk"], l["mgr"].replace(" (GPT)", ""), l["slot"], l["player"], l["locked"], l["best"], l["missed"], l["when"]] for l in F["locks"]])
    pl = (A or {}).get("players") or F["players"]
    sheet(wb, "Players", ["Owner", "Player", "Pos", "Team", "GP", "Avg", "Last 3", "Best", "Worst", "SD", "30+ %", "Tier"],
          [[p["owner"], p["player"], p["pos"], p["team"], p["gp"], p["avg"], p["l3"], p["max"], p["min"], p["sd"], p["p30"], p["tier"]] for p in pl])
    sheet(wb, "Waivers", ["Week", "Manager", "Added", "Avg since", "Games", "Dropped", "Drop avg", "Gain"],
          [[f["wk"], f["mgr"].replace(" (GPT)", ""), f["add"], f["addavg"], f["addgp"], f["drop"], f["dropavg"], f["gain"]] for f in (A or {}).get("fa") or F["fa"]])
    if C:
        sheet(wb, "Odds", ["Manager", "W", "L", "Playoffs", "Bye", "#1 seed", "Title", "Exp wins"],
              [[k, v["w"], v["l"], round(v["playoffs"], 3), round(v["bye"], 3), round(v["seed1"], 3), round(v["title"], 3), round(v["exp_wins"], 1)] for k, v in C["teams"].items()])
    if T:
        sheet(wb, "Trade board", ["Player", "Owner", "Ours", "Market", "Gap"], [[b["name"], b["owner"], b["ours"], b["market"], b["gap"]] for b in T["board"]])
    if P:
        rows = [[team, s["slot"], s["player"], s["worth"], c["date"], c["player"], c["plays"], c["exp"], c["th"], c["act"]]
                for team, t in P["teams"].items() for s in t["slots"] for c in s["chances"]]
        sheet(wb, "Lock plan", ["Team", "Slot", "Regular", "Slot worth", "Date", "Player", "Plays", "Expected", "Threshold", "Action"], rows)
    wb.save(a.out)
    print("wrote", a.out, [ws.title for ws in wb])


if __name__ == "__main__":
    main()
