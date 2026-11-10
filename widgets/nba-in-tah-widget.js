// NBA in tah: iPhone widget for the free Scriptable app.
// Shows what to do now (lock calls), your record, and title odds. Reads the same files as the website.
const BASE = "https://jack7apr-cpu.github.io/nba-in-tah/data/";
const ME = "Jack";

async function get(name) {
  try { return await new Request(BASE + name + "?t=" + Date.now()).loadJSON(); } catch (e) { return null; }
}
const [plan, crystal, locked] = await Promise.all([get("plan.json"), get("crystal.json"), get("locked.json")]);
const done = new Set(locked && plan && locked.week === plan.week ? locked.players : []);

const w = new ListWidget();
w.backgroundColor = new Color("#0a0e1a");
w.setPadding(14, 14, 14, 14);
w.refreshAfterDate = new Date(Date.now() + 20 * 60 * 1000);

const t = w.addText("NBA IN TAH");
t.font = Font.boldSystemFont(11); t.textColor = new Color("#ff7a1a");
w.addSpacer(4);

const locks = plan ? plan.teams[ME].slots.filter(s => s.chances[0] && s.chances[0].act === "LOCK" && !done.has(s.player)) : [];
const main = w.addText(locks.length ? "Lock " + locks.map(s => s.player.split(" ").slice(-1)[0]).join(", ") : plan ? "All clear" : "No data");
main.font = Font.boldSystemFont(locks.length ? 20 : 22);
main.textColor = new Color(locks.length ? "#35e0a1" : "#e9edf8");
main.minimumScaleFactor = 0.6;

if (plan) {
  const next = plan.teams[ME].slots
    .map(s => ({ s, c: s.chances[0] }))
    .filter(x => x.c && x.c.act === "IF")
    .sort((a, b) => b.s.worth - a.s.worth)[0];
  if (next) {
    w.addSpacer(4);
    const n = w.addText(next.s.player.split(" ").slice(-1)[0] + " lock at " + next.c.th + "+");
    n.font = Font.systemFont(12); n.textColor = new Color("#8b95b3");
  }
}
w.addSpacer();
if (crystal) {
  const me = crystal.teams[ME];
  const r = w.addText(me.w + "-" + me.l + " · title " + Math.round(me.title * 100) + "%");
  r.font = Font.mediumSystemFont(12); r.textColor = new Color("#e9edf8");
}
const u = w.addText("tap to open site"); u.font = Font.systemFont(9); u.textColor = new Color("#8b95b3");
w.url = "https://jack7apr-cpu.github.io/nba-in-tah/#live";

if (config.runsInWidget) Script.setWidget(w); else await w.presentSmall();
Script.complete();
