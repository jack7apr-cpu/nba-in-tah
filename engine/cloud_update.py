#!/usr/bin/env python3
"""Cloud/any-machine refresh with no Claude involved: fetch Sleeper, rebuild the dashboard, Crystal Ball page and almanac.
Run from this folder:  python3 cloud_update.py   -> files land in ./out/  (needs: pip install openpyxl; optional: LibreOffice for a values-only share copy)"""
import json, os, shutil, subprocess, sys
H = os.path.dirname(os.path.abspath(__file__))
os.chdir(H)
cfg = json.load(open("config.json"))
os.makedirs("out", exist_ok=True)


def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    print(f"== {' '.join(args)[:70]}: {'ok' if r.returncode == 0 else 'FAILED'}")
    if r.returncode:
        print(r.stderr[-800:]); sys.exit(1)
    return r.stdout


run("sleeper.py", "fetch", cfg["league_id"], "--sport", cfg["sport"])
run("engine.py", "refresh", cfg["me"])
run("dashboard.py", cfg["me"])
run("crystal_page.py") if os.path.exists("crystal_page.py") else None
run("almanac.py", "--out", "out/Demons_Dynasty_Almanac.xlsx")
for f in ("dashboard.html", "crystal_ball.html"):
    if os.path.exists(f):
        shutil.copy(f, "out/" + f)
soffice = shutil.which("soffice") or shutil.which("libreoffice")
if soffice:  # LibreOffice recalculates and stores values; used to build a copy that shows data in any viewer
    subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", "recalc", "out/Demons_Dynasty_Almanac.xlsx"], capture_output=True, timeout=300)
    if os.path.exists("recalc/Demons_Dynasty_Almanac.xlsx"):
        run("almanac.py", "--out", "out/Demons_Dynasty_Almanac_SHARE.xlsx", "--share-from", "recalc/Demons_Dynasty_Almanac.xlsx")
print("done:", sorted(os.listdir("out")))
