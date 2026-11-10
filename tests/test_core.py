"""Core tests: python3 -m unittest discover -s tests -v   (stdlib only; run from the repo root)"""
import datetime as dt, io, json, os, subprocess, sys, tempfile, unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "alerts"), os.path.join(ROOT, "engine"), os.path.join(ROOT, "almanac")]
os.chdir(ROOT)
import notify, sync_locks, nbadata as N, risk as R, lock as K  # noqa: E402

LIVE = json.load(open("site/data/live.json")) if os.path.exists("site/data/live.json") else json.load(open("/tmp/live.json"))
PLAN = json.load(open("site/data/plan.json"))


def jack_starter(live):
    u = next(u["user_id"] for u in live["users"] if u["display_name"].lower() == "jackhill1617")
    ro = next(r for r in live["rosters"] if r["owner_id"] == u)
    return ro["starters"][0]


class Alerts(unittest.TestCase):
    def setUp(self):
        self.live = json.loads(json.dumps(LIVE))
        pid = jack_starter(self.live)
        self.p = self.live["players"][pid]
        self.tip = dt.datetime(2026, 11, 11, 0, 30, tzinfo=dt.timezone.utc)
        self.live["schedule"] = [{"date": "2026-11-11T00:30Z", "name": "x", "status": "STATUS_SCHEDULED", "teams": [self.p["team"], "ZZZ"]}]

    def flag(self, status):
        self.live["espn_injuries"] = [{"player": self.p["name"], "status": status, "note": "", "team": "", "date": ""}]

    def test_questionable_only_inside_window(self):
        self.flag("Questionable")
        self.assertEqual(notify.decide(self.live, {}, self.tip - dt.timedelta(minutes=200)), [])
        self.assertEqual(len(notify.decide(self.live, {}, self.tip - dt.timedelta(minutes=60))), 1)
        self.assertEqual(notify.decide(self.live, {}, self.tip - dt.timedelta(minutes=5)), [])

    def test_out_pings_any_time_same_day(self):
        self.flag("Out")
        self.assertEqual(len(notify.decide(self.live, {}, self.tip - dt.timedelta(hours=5))), 1)

    def test_dedupe(self):
        self.flag("Questionable")
        now = self.tip - dt.timedelta(minutes=60)
        key = notify.decide(self.live, {}, now)[0][0]
        self.assertEqual(notify.decide(self.live, {key: "x"}, now), [])

    def test_healthy_is_silent(self):
        self.live["espn_injuries"] = []
        self.p["inj"] = None
        self.assertEqual(notify.decide(self.live, {}, self.tip - dt.timedelta(minutes=60)), [])

    def test_alert_is_short(self):
        self.flag("Questionable")
        txt = notify.decide(self.live, {}, self.tip - dt.timedelta(minutes=60))[0][1]
        self.assertLess(len(txt), 60)

    def test_lock_alert_respects_locked_and_dedupe(self):
        plan = {"week": 4, "teams": {"Jack": {"slots": [{"slot": "PG", "player": "Jamal Murray", "worth": 30.5, "chances": [{"act": "LOCK", "exp": 30.5}]}]}}}
        self.assertEqual(len(notify.lock_alerts(plan, None, {})), 1)
        self.assertEqual(notify.lock_alerts(plan, {"week": 4, "players": ["Jamal Murray"]}, {}), [])
        self.assertEqual(len(notify.lock_alerts(plan, {"week": 3, "players": ["Jamal Murray"]}, {})), 1)   # old week ignored
        key = notify.lock_alerts(plan, None, {})[0][0]
        self.assertEqual(notify.lock_alerts(plan, None, {key: "x"}), [])


class SyncLocks(unittest.TestCase):
    def run_sync(self, lines, week=4, start=None):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(start or {"week": week, "players": []}, f); f.close()
        body = "\n".join(json.dumps({"event": "message", "message": json.dumps(m)} if isinstance(m, dict) else {"event": "open"}) for m in lines).encode()
        resp = mock.Mock(); resp.read.return_value = body
        with mock.patch.dict(os.environ, {"NTFY_CMD_TOPIC": "t"}), mock.patch("urllib.request.urlopen", return_value=resp), \
                mock.patch.object(sys, "argv", ["x", "--locked", f.name, "--week", str(week)]):
            sync_locks.main()
        return json.load(open(f.name))["players"]

    def test_lock_then_undo(self):
        self.assertEqual(self.run_sync([{"w": 4, "p": "A", "l": True}, {"w": 4, "p": "B", "l": True}, {"w": 4, "p": "A", "l": False}]), ["B"])

    def test_other_week_ignored(self):
        self.assertEqual(self.run_sync([{"w": 3, "p": "A", "l": True}]), [])

    def test_new_week_resets_list(self):
        self.assertEqual(self.run_sync([], week=5, start={"week": 4, "players": ["Old"]}), [])

    def test_garbage_lines_skipped(self):
        self.assertEqual(self.run_sync([{"event": "open"}, {"w": 4, "p": "A", "l": True}]), ["A"])


class Official(unittest.TestCase):
    def build(self, bump, out):
        live = json.loads(json.dumps(LIVE))
        for i, r in enumerate(live["rosters"]):
            r["settings"]["wins"] += bump
            r["settings"]["fpts"] += (200 + i) * bump
        lf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(live, lf); lf.close()
        subprocess.run([sys.executable, "almanac/official_weeks.py", "--live", lf.name, "--out", out], check=True, capture_output=True)
        return json.load(open(out))["weeks"]

    def test_seed_matches_screenshots(self):
        out = tempfile.mktemp(suffix=".json")
        w = self.build(0, out)
        self.assertEqual(sorted(w), ["1", "2", "3"])
        self.assertEqual(w["3"]["Jack"], 279)
        self.assertEqual(w["3"]["Isaac"], 262.5)

    def test_season_points_equal_sum_of_weeks(self):
        w = json.load(open("site/data/official.json"))["weeks"]
        for r in LIVE["rosters"]:
            s = r["settings"]
            name = {u["user_id"]: u["display_name"] for u in LIVE["users"]}[r["owner_id"]].lower()
            mgr = {"jackhill1617": "Jack", "kingboo25": "Kyran", "idbh": "Isaac", "lmlewis": "Lewis", "matttallguy": "Matt", "maxcmaples": "Maxi", "vpiggz": "David", "donghyuk101301": "Tony"}[name]
            self.assertAlmostEqual(sum(w[k][mgr] for k in w), s["fpts"] + s.get("fpts_decimal", 0) / 100, places=1)

    def test_new_week_is_difference(self):
        out = tempfile.mktemp(suffix=".json"); json.dump(json.load(open("site/data/official.json")), open(out, "w"))
        w = self.build(1, out)
        self.assertEqual(sorted(w), ["1", "2", "3", "4"])
        self.assertTrue(all(190 < v < 215 for v in w["4"].values()))


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = N.League()

    def test_scoring_reproduces_counted_locks(self):
        """every curated lock score should equal a real game of that player in that week (or a 0/troll)"""
        facts = json.load(open("site/data/factfile.json"))["locks"]
        hits = tot = 0
        names = {self.L.pname(p).lower(): p for p in self.L.pinfo}
        for l in facts:
            pid = names.get(l["player"].lower())
            if not pid or l["locked"] in (0, None):
                continue
            tot += 1
            games = [self.L.actual(pid, d) for d in self.L.team_dates.get((self.L.pinfo[pid] or {}).get("team"), ())
                     if N.week_of(d) == l["wk"]]
            if any(g is not None and abs(g - l["locked"]) < 0.51 for g in games):
                hits += 1
        self.assertGreater(tot, 150)
        self.assertGreater(hits / tot, 0.9)

    def healthy(self, M):
        """a player who played his latest game (so no ongoing-absence floor) and his last game date"""
        for pid in self.L.pinfo:
            if self.L.pname(pid) == "Jamal Murray":
                t = "2026-11-10"
                d = min(d for d, _ in M.games[pid] if d >= t)
                return pid, (t, d), (self.L.pinfo[pid] or {}).get("team")

    def test_probable_beats_generic_gtd(self):
        M = R.Model(self.L, R.load_params())
        pid, d, team = self.healthy(M)
        a = M.forecast(pid, *d, team, ["GTD", "Probable"])[1]
        b = M.forecast(pid, *d, team, ["GTD"])[1]
        self.assertGreater(a, b)
        self.assertGreater(a, 0.85)

    def test_status_ordering_out_lt_questionable_lt_healthy(self):
        M = R.Model(self.L, R.load_params())
        pid, d, team = self.healthy(M)
        out, q, ok = (M.forecast(pid, *d, team, [s])[1] for s in ("Out", "Questionable", None))
        self.assertLess(out, 0.2)          # an Out tag fades slowly (0.85/day), so ~0.15 a day later
        self.assertLess(out, q)
        self.assertLess(q, ok)


class Plan(unittest.TestCase):
    def test_every_team_has_nine_slots(self):
        for name, t in PLAN["teams"].items():
            self.assertEqual(len(t["slots"]), 9, name)

    def test_jack_slots_match_real_lineup(self):
        got = [s["player"] for s in sorted(PLAN["teams"]["Jack"]["slots"], key=lambda s: ["PG", "SG", "G", "SF", "PF", "F", "C", "UTIL", "UTIL"].index(s["slot"]))]
        u = next(u["user_id"] for u in LIVE["users"] if u["display_name"].lower() == "jackhill1617")
        ro = next(r for r in LIVE["rosters"] if r["owner_id"] == u)
        m = json.load(open("data/2026/matchups/week_%02d.json" % PLAN["week"]))
        mine = next(x for x in m if x["roster_id"] == ro["roster_id"])
        want = [LIVE["players"][p]["name"] for p in mine["starters"]]
        self.assertEqual(sorted(got), sorted(want))

    def test_last_chance_is_forced(self):
        for s in PLAN["teams"]["Jack"]["slots"]:
            if len(s["chances"]) > 1:
                self.assertIn(s["chances"][-1]["act"], ("FORCED", "LOCK", "HOLD", "IF"))
                self.assertEqual(s["chances"][-1]["act"], "FORCED") if not any(c["act"] in ("LOCK", "HOLD") for c in s["chances"]) else None

    def test_thresholds_fall_with_fewer_games_left(self):
        for s in PLAN["teams"]["Jack"]["slots"]:
            ths = [c["th"] for c in s["chances"] if c["act"] == "IF"]
            self.assertEqual(ths, sorted(ths, reverse=True))


class Crystal(unittest.TestCase):
    def test_probabilities_are_consistent(self):
        out = tempfile.mktemp(suffix=".json")
        subprocess.run([sys.executable, "engine/crystal_nba.py", "--live", "site/data/live.json", "--runs", "3000", "--out", out], check=True, capture_output=True)
        C = json.load(open(out))
        t = C["teams"]
        self.assertAlmostEqual(sum(x["playoffs"] for x in t.values()), C["n_playoff"], places=6)
        self.assertAlmostEqual(sum(x["title"] for x in t.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(x["seed1"] for x in t.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(x["bye"] for x in t.values()), 2.0, places=6)
        for x in t.values():
            self.assertLessEqual(x["bye"], x["playoffs"] + 1e-9)
            self.assertLessEqual(x["title"], x["playoffs"] + 1e-9)


class AutoAlmanac(unittest.TestCase):
    def test_players_close_to_curated_and_complete(self):
        out = tempfile.mktemp(suffix=".json")
        subprocess.run([sys.executable, "almanac/build_auto.py", "--out", out], check=True, capture_output=True)
        a = json.load(open(out))
        cur = {p["player"]: p for p in json.load(open("site/data/factfile.json"))["players"]}
        self.assertGreater(len(a["players"]), 100)
        diffs = [abs(p["avg"] - cur[p["player"]]["avg"]) for p in a["players"] if p["player"] in cur]
        self.assertGreater(len(diffs), 90)
        self.assertLess(sum(diffs) / len(diffs), 1.0)
        for p in a["players"]:
            self.assertGreaterEqual(p["max"], p["avg"] - 1e-6)
            self.assertLessEqual(p["min"], p["avg"] + 1e-6)
            self.assertGreaterEqual(p["sd"], 0)
        self.assertTrue(all(f["mgr"] != "?" for f in a["fa"]))


class Review(unittest.TestCase):
    def test_review_json_shape_and_engine_beats_never_lock(self):
        R_ = json.load(open("site/data/review.json"))
        self.assertEqual(len(R_["managers"]), 8)
        for v in R_["managers"].values():
            self.assertGreaterEqual(v["hindsight"], v["actual"] - 1e-6)
            self.assertGreaterEqual(v["actual"], v["never_lock"] - 1e-6)
        self.assertGreater(R_["league"]["engine"], R_["league"]["never_lock"])
        self.assertLessEqual(len(R_["misses"]), 12)


class Export(unittest.TestCase):
    def test_xlsx_has_sheets_without_formulas(self):
        import openpyxl
        out = tempfile.mktemp(suffix=".xlsx")
        subprocess.run([sys.executable, "almanac/export_xlsx.py", "--out", out], check=True, capture_output=True)
        wb = openpyxl.load_workbook(out)
        for name in ("Managers", "Locks", "Players", "Waivers", "Lock plan"):   # Odds/Trade board only exist when those files are built
            self.assertIn(name, wb.sheetnames)
        for ws in wb:
            for row in ws.iter_rows(values_only=True):
                for c in row:
                    self.assertFalse(isinstance(c, str) and c.startswith("="), ws.title)
        self.assertEqual(wb["Managers"].max_row, 9)


class Frozen(unittest.TestCase):
    def test_finished_week_matchups_are_frozen(self):
        """Sleeper's past-week matchup points drift; the stored copies must stay as first saved (Jack = 794.5 over weeks 1-3)"""
        r = json.load(open("data/2026/rosters.json")); u = {x["user_id"]: x["display_name"] for x in json.load(open("data/2026/users.json"))}
        rid = next(x["roster_id"] for x in r if u[x["owner_id"]] == "jackhill1617")
        tot = sum(sum(m["starters_points"]) for w in (1, 2, 3) for m in json.load(open(f"data/2026/matchups/week_0{w}.json")) if m["roster_id"] == rid)
        self.assertEqual(tot, 794.5)


class Data(unittest.TestCase):
    def test_live_json_complete(self):
        for k in ("state", "league", "users", "rosters", "matchups", "proj", "players", "espn_injuries", "schedule", "updated"):
            self.assertIn(k, LIVE)
        self.assertEqual(LIVE["errors"], {})
        self.assertEqual(len(LIVE["rosters"]), 8)

    def test_league_scoring_unchanged(self):
        sc = LIVE["league"]["scoring_settings"]
        for k, v in {"pts": 0.5, "reb": 1, "ast": 1, "stl": 2, "blk": 2, "to": -1, "tpm": 0.5}.items():
            self.assertEqual(sc[k], v, k)

    def test_no_secrets_in_repo(self):
        out = subprocess.run(["git", "grep", "-nE", "github_pat_|ghp_|nba-in-tah-jh-|nba-in-tah-cmd-", "--", ".", ":!tests"], capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()
