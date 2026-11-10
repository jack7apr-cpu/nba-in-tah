"use strict";
const $=(s,e=document)=>e.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const nm=s=>String(s).replace(/ \(GPT\)/,""), f1=x=>Number(x).toFixed(1), ME="Jack";
const TABS=[["home","🏠","Home"],["weeks","📅","Weeks"],["mgrs","👥","Managers"],["locks","🔒","Lock Lab"],["players","🏀","Players"],["waivers","🔄","Waivers"],["live","⚡","Live"]];
let D={}, S={tab:"home",wk:null,lk:{mgr:"All",wk:"All",sort:"missed"},pl:{q:"",own:"All",pos:"All",sort:"avg"}};

Promise.all(["league_data","factfile","live"].map(n=>fetch(`data/${n}.json`).then(r=>r.json()).catch(()=>null))).then(([L,F,V])=>{
  D.L=L; D.F=F; D.V=V; prep(); S.wk=Math.max(...Object.keys(L.weeks).map(Number)); route(); addEventListener("hashchange",route);
});

function prep(){
  const F=D.F, M={}; for(const [k,v] of Object.entries(F.mgrs)) M[nm(k)]=v; D.M=M;
  const wk={}; for(const [w,ms] of Object.entries(F.MU)) for(const [a,pa,b,pb] of ms){(wk[w]??={})[nm(a)]=pa;wk[w][nm(b)]=pb;}
  D.wk=wk; const names=Object.keys(M);
  for(const n of names){ let wins=0,t=0; for(const w in wk) for(const o of names) if(o!==n&&o in wk[w]){t++; if(wk[w][n]>wk[w][o])wins++;} M[n].ap=t?wins/t:0; M[n].eff=M[n].pf/(M[n].pf+M[n].missed); }
  const sc=(key)=>{const v=names.map(n=>M[n][key]),lo=Math.min(...v),hi=Math.max(...v);return n=>100*(M[n][key]-lo)/((hi-lo)||1)};
  const sh=sc("top9"),po=sc("eff"),re=sc("ap");
  for(const n of names){M[n].shit=sh(n);M[n].poo=po(n);M[n].res=re(n);M[n].bowel=.4*M[n].res+.3*M[n].poo+.3*M[n].shit;}
  D.rank=names.sort((a,b)=>M[b].bowel-M[a].bowel); D.rank.forEach((n,i)=>M[n].rk=i+1);
  D.locks=F.locks.map(l=>({...l,mgr:nm(l.mgr)})); D.players=F.players; D.fa=F.fa.map(x=>({...x,mgr:nm(x.mgr)}));
  $("#nav").innerHTML=TABS.map(([k,i,t])=>`<a href="#${k}" data-k="${k}"><b>${i}</b>${t}</a>`).join("");
}
const verdict=b=>b>=85?"Ghost shit: no wipe needed":b>=70?"Textbook: two wipes":b>=55?"Solid log":b>=40?"Bit of a mess":b>=25?"Dodgy kebab":"Full norovirus";
const quad=m=>m.shit>=50&&m.poo>=50?"Big and clean":m.shit>=50?"Big log, messy wipe":m.poo>=50?"Small but tidy":"Small and messy";

function route(){
  S.tab=(location.hash||"#home").slice(1)||"home"; if(!TABS.some(t=>t[0]===S.tab))S.tab="home";
  document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("on",a.dataset.k===S.tab));
  const upd=D.V?.updated?new Date(D.V.updated):null;
  $("#sub").textContent=`Week ${D.V?.state?.week??"?"} · live data ${upd?upd.toLocaleString([], {weekday:"short",hour:"2-digit",minute:"2-digit"}):"unavailable"} · almanac through week ${Math.max(...Object.keys(D.L.weeks).map(Number))}`;
  $("#app").innerHTML=({home,weeks,mgrs,locks,players,waivers,live})[S.tab](); (after[S.tab]||(()=>{}))(); scrollTo(0,0);
}
const after={};
function chips(id,opts,cur){return `<div class="chips" id="${id}">${opts.map(o=>`<span class="chip ${String(o)===String(cur)?"on":""}" data-v="${esc(o)}">${esc(o)}</span>`).join("")}</div>`}
function bindChips(id,fn){document.querySelectorAll(`#${id} .chip`).forEach(c=>c.onclick=()=>fn(c.dataset.v))}
function sheet(html){const s=document.createElement("div");s.className="sheet";s.innerHTML=`<div><button class="x">×</button>${html}</div>`;s.onclick=e=>{if(e.target===s||e.target.className==="x")s.remove()};document.body.append(s)}
function tip(el,fn){const t=$("#tt");el.onmousemove=e=>{t.hidden=false;t.innerHTML=fn();t.style.left=Math.min(e.clientX+12,innerWidth-200)+"px";t.style.top=e.clientY+12+"px"};el.onmouseleave=()=>t.hidden=true;el.onclick=e=>{e.stopPropagation();el.onmousemove(e)}}

/* HOME */
function home(){
  const m=D.M, me=m[ME], best=[...D.rank].sort((a,b)=>m[b].pf-m[a].pf)[0];
  setTimeout(()=>{document.querySelectorAll(".bar i").forEach(i=>i.style.width=i.dataset.w+"%")},50);
  after.home=()=>{drawQuad();document.querySelectorAll("[data-m]").forEach(c=>c.onclick=()=>mgrSheet(c.dataset.m))};
  return `<div class="grid g4">
   <div class="card"><div class="lbl">Your Bowel rank</div><div class="big" style="color:var(--or)">#${me.rk}</div><div class="sub">${verdict(me.bowel)}</div></div>
   <div class="card"><div class="lbl">Record</div><div class="big">${me.w}–${me.l}</div><div class="sub">${f1(me.pf)} pts · avg ${f1(me.avgweek)}</div></div>
   <div class="card"><div class="lbl">Points leader</div><div class="big">${best}</div><div class="sub">${f1(m[best].pf)} pts</div></div>
   <div class="card"><div class="lbl">Points left on bench</div><div class="big">${f1(me.missed)}</div><div class="sub">lock efficiency ${(me.eff*100).toFixed(0)}%</div></div></div>
  <h2 style="margin-top:22px">💩 The Bowel Index</h2><div class="sub" style="margin-bottom:8px"><b>Shit</b> = how big the output is (roster talent). <b>Poo</b> = how clean the job is (lock efficiency). Results = all-play win %. Weighted 40/30/30. Tap anyone.</div>
  <div class="grid g2"><div class="card">${D.rank.map(n=>`<div class="it row" data-m="${n}" style="padding:9px 0;cursor:pointer"><span class="num" style="width:22px">${m[n].rk}</span><div class="sp"><div class="row"><b>${n}</b><span class="sub">${verdict(m[n].bowel)}</span></div><div class="bar"><i data-w="${m[n].bowel}" style="width:0"></i></div></div><span class="num">${f1(m[n].bowel)}</span></div>`).join("")}</div>
  <div class="card"><div class="lbl">Talent (Shit) vs Cleanliness (Poo)</div><svg id="quad" viewBox="0 0 320 300" style="width:100%"></svg></div></div>`;
}
function drawQuad(){
  const svg=$("#quad"),m=D.M,W=320,H=300,P=30; let h=`<rect x="${P}" y="10" width="${W-P-10}" height="${H-P-10}" fill="none" stroke="#222c4a"/><line x1="${P+(W-P-10)/2}" y1="10" x2="${P+(W-P-10)/2}" y2="${H-P}" stroke="#222c4a" stroke-dasharray="4"/><line x1="${P}" y1="${10+(H-P-10)/2}" x2="${W-10}" y2="${10+(H-P-10)/2}" stroke="#222c4a" stroke-dasharray="4"/><text x="${W/2}" y="${H-8}" text-anchor="middle">Shit: talent →</text><text transform="translate(10 ${H/2}) rotate(-90)" text-anchor="middle">Poo: clean →</text>`;
  for(const n of D.rank){const x=P+m[n].shit/100*(W-P-30)+10,y=H-P-m[n].poo/100*(H-P-30)-10;h+=`<g class="pt" data-n="${n}" style="cursor:pointer"><circle cx="${x}" cy="${y}" r="${n===ME?9:7}" fill="${n===ME?"var(--or)":"#5aa9ff"}" opacity=".9"/><text x="${x}" y="${y-12}" text-anchor="middle" style="fill:#e9edf8">${n}</text></g>`}
  svg.innerHTML=h; svg.querySelectorAll(".pt").forEach(g=>{const n=g.dataset.n;tip(g,()=>`<b>${n}</b> · ${quad(m[n])}<br>Shit ${f1(m[n].shit)} · Poo ${f1(m[n].poo)}`);g.addEventListener("dblclick",()=>mgrSheet(n))})
}

/* WEEKS */
function weeks(){
  const ws=Object.keys(D.L.weeks).map(Number),w=D.L.weeks[S.wk]; after.weeks=()=>{bindChips("wkc",v=>{S.wk=+v.replace("Week ","");route()});document.querySelectorAll("[data-mu]").forEach(c=>c.onclick=()=>muSheet(+c.dataset.mu))};
  const aw=w.isaac?.awards||{};
  return `${chips("wkc",ws.map(x=>"Week "+x),"Week "+S.wk)}
  <div class="grid g2">${w.matchups.map(([a,pa,b,pb],i)=>{const win=pa>pb;return `<div class="card tap" data-mu="${i}"><div class="row"><b ${win?'style="color:var(--gr)"':""}>${a}</b><span class="sp"></span><span class="num">${pa}</span></div><div class="row"><b ${!win?'style="color:var(--gr)"':""}>${b}</b><span class="sp"></span><span class="num">${pb}</span></div><div class="sub" style="margin-top:6px">margin ${f1(Math.abs(pa-pb))} · tap for locks</div></div>`}).join("")}</div>
  <h2 style="margin-top:20px">🏅 Isaac's awards</h2><div class="grid g4">${Object.entries(aw).map(([k,v])=>`<div class="card"><div class="lbl">${esc(k)}</div><div style="margin-top:4px">${esc(v)||"–"}</div></div>`).join("")||'<div class="card sub">No awards logged.</div>'}</div>
  <h2 style="margin-top:20px">Claude's read</h2><div class="card">${esc(w.claude?.text||"")}</div>
  <h2 style="margin-top:20px">Isaac's recap</h2><div class="recap">${esc(w.isaac?.text||"No recap yet.")}</div>`;
}
function muSheet(i){const w=D.L.weeks[S.wk],[a,pa,b,pb]=w.matchups[i];const col=n=>`<div><h3>${n}</h3>${(w.locks[n]||[]).map(([p,s])=>`<div class="row" style="padding:4px 0"><span class="sp">${esc(p)}</span><span class="num ${s<18?"neg":s>=35?"pos":""}">${s}</span></div>`).join("")}</div>`;sheet(`<h2>${a} ${pa} – ${pb} ${b}</h2><div class="grid g2">${col(a)}${col(b)}</div>`)}

/* MANAGERS */
function mgrs(){after.mgrs=()=>document.querySelectorAll("[data-m]").forEach(c=>c.onclick=()=>mgrSheet(c.dataset.m));
  return `<div class="grid g2">${D.rank.map(n=>{const m=D.M,x=m[n],note=D.L.manager_notes[n]||{};return `<div class="card tap" data-m="${n}"><div class="row"><h3>#${x.rk} ${n}</h3><span class="sp"></span><span class="pill or">${esc(note.tag||quad(x))}</span></div><div class="sub">${x.w}–${x.l} · ${f1(x.pf)} pts · lock avg ${f1(x.lockavg)}</div><div style="margin-top:8px">${esc(note.style||"")}</div></div>`}).join("")}</div>`}
function mgrSheet(n){const x=D.M[n],note=D.L.manager_notes[n]||{},key=Object.keys(D.F.slotavg).find(k=>nm(k)===n),sl=D.F.slotavg[key]||{},mx=Math.max(...Object.values(sl),1);
  const pg=D.F.pg[n]||D.F.pg[key]||{};
  sheet(`<h2>${n} <span class="pill or">${esc(note.tag||"")}</span></h2><div class="sub">${esc(note.style||"")}</div>
  <div class="grid g4" style="margin:12px 0">${[["Bowel",f1(x.bowel)],["Shit",f1(x.shit)],["Poo",f1(x.poo)],["All-play",(x.ap*100).toFixed(0)+"%"],["Perfect locks",x.perfect],["30+ games",x.g30],["Final-game locks",x.final+"/"+x.nl],["Missed pts",f1(x.missed)]].map(([a,b])=>`<div class="card"><div class="lbl">${a}</div><div class="big" style="font-size:22px">${b}</div></div>`).join("")}</div>
  <h3>Average counted score by slot</h3>${Object.entries(sl).map(([s,v])=>`<div class="row" style="margin:4px 0"><span style="width:44px" class="mut">${s}</span><div class="bar sp"><i style="width:${v/mx*100}%"></i></div><span class="num" style="width:44px;text-align:right">${v}</span></div>`).join("")}
  <h3 style="margin-top:14px">Position groups</h3>${Object.entries(pg).map(([g,o])=>`<div class="row" style="margin:4px 0"><b style="width:70px">${g}</b><span class="num">${o.score}</span><span class="sub">${esc(o.who)}</span></div>`).join("")}
  <div class="grid g2" style="margin-top:14px"><div><h3 class="pos">Highs</h3>${(note.top||[]).map(t=>`<div class="sub">• ${esc(t)}</div>`).join("")}</div><div><h3 class="neg">Lows</h3>${(note.bot||[]).map(t=>`<div class="sub">• ${esc(t)}</div>`).join("")}</div></div>`)}

/* LOCK LAB */
function locks(){const mg=["All",...D.rank],wk=["All",...Object.keys(D.L.weeks)];
  after.locks=()=>{bindChips("lm",v=>{S.lk.mgr=v;route()});bindChips("lw",v=>{S.lk.wk=v;route()});bindChips("ls",v=>{S.lk.sort=v;route()})};
  let r=D.locks.filter(l=>(S.lk.mgr==="All"||l.mgr===S.lk.mgr)&&(S.lk.wk==="All"||String(l.wk)===S.lk.wk));
  r=r.sort((a,b)=>S.lk.sort==="locked"?b.locked-a.locked:S.lk.sort==="low"?a.locked-b.locked:b.missed-a.missed).slice(0,40);
  return `<h2>🔒 Lock Lab</h2><div class="sub">Every counted slot score vs the best game that player had that week. Missed = points left on the table.</div>${chips("lm",mg,S.lk.mgr)}${chips("lw",wk,S.lk.wk)}${chips("ls",["missed","locked","low"],S.lk.sort)}
  <div class="card list">${r.map(l=>`<div class="it"><span class="pill">${l.slot}</span><div class="sp"><b>${esc(l.player)}</b> <span class="sub">${l.mgr} · wk${l.wk} · ${esc(l.when)}</span><div class="bar"><i style="width:${Math.min(100,l.locked/Math.max(l.best,1)*100)}%;background:${l.missed>8?"var(--rd)":"linear-gradient(90deg,var(--or),var(--yl))"}"></i></div></div><div style="text-align:right"><span class="num">${l.locked}</span><div class="sub neg">${l.missed>0?"−"+f1(l.missed):"perfect"}</div></div></div>`).join("")}</div>`}

/* PLAYERS */
function players(){const own=["All",...D.rank],pos=["All","PG","SG","SF","PF","C"];
  after.players=()=>{const q=$("#q");q.oninput=()=>{S.pl.q=q.value;listP()};bindChips("po",v=>{S.pl.own=v;route();$("#q").value=S.pl.q;listP()});bindChips("pp",v=>{S.pl.pos=v;route();$("#q").value=S.pl.q;listP()});bindChips("ps",v=>{S.pl.sort=v;route();$("#q").value=S.pl.q;listP()});q.value=S.pl.q;listP()};
  return `<h2>🏀 Players</h2><input id="q" type="search" placeholder="Search a player…">${chips("po",own,S.pl.own)}${chips("pp",pos,S.pl.pos)}${chips("ps",["avg","l3","max","sd","gp"],S.pl.sort)}<div class="card list" id="pl"></div>`}
function listP(){const p=S.pl,q=p.q.toLowerCase();const r=D.players.filter(x=>(p.own==="All"||x.owner===p.own)&&(p.pos==="All"||x.pos.includes(p.pos))&&x.player.toLowerCase().includes(q)).sort((a,b)=>p.sort==="sd"?a.sd-b.sd:b[p.sort]-a[p.sort]).slice(0,60);
  $("#pl").innerHTML=r.map((x,i)=>`<div class="it" data-i="${D.players.indexOf(x)}"><span class="pill ${x.ir?"rd":"bl"}">${x.pos}</span><div class="sp"><b>${esc(x.player)}</b> <span class="sub">${x.team} · ${x.owner} · ${x.tier}</span></div><div style="text-align:right"><span class="num">${x[p.sort]}</span><div class="sub">${p.sort}</div></div></div>`).join("")||'<div class="sub">No match.</div>';
  document.querySelectorAll("#pl .it").forEach(e=>e.onclick=()=>{const x=D.players[e.dataset.i];sheet(`<h2>${esc(x.player)}</h2><div class="sub">${x.pos} · ${x.team} · owned by ${x.owner} · ${x.tier}</div><div class="grid g4" style="margin:12px 0">${[["Avg",x.avg],["Last 3",x.l3],["High",x.max],["Low",x.min],["Std dev",x.sd],["30+ rate",x.p30+"%"],["Games",x.gp],["Lock avg",x.lockavg]].map(([a,b])=>`<div class="card"><div class="lbl">${a}</div><div class="big" style="font-size:22px">${b}</div></div>`).join("")}</div>${x.inj?`<div class="card warn">${esc(x.inj)}</div>`:""}`)})}

/* WAIVERS */
function waivers(){return `<h2>🔄 Waivers</h2><div class="sub">Every completed add, ranked by gain over the player dropped.</div><div class="card list">${[...D.fa].sort((a,b)=>b.gain-a.gain).map(x=>`<div class="it"><div class="sp"><b>${esc(x.add)}</b> <span class="sub">for ${esc(x.drop)} · ${x.mgr} · wk${x.wk}</span></div><div style="text-align:right"><span class="num ${x.gain>=0?"pos":"neg"}">${x.gain>=0?"+":""}${f1(x.gain)}</span><div class="sub">${x.addavg} vs ${x.dropavg}</div></div></div>`).join("")}</div>`}

/* LIVE */
function live(){const V=D.V;if(!V)return '<div class="card warn">Live data unavailable.</div>';
  const age=(Date.now()-new Date(V.updated))/36e5,errs=Object.keys(V.errors||{}),sc=V.league.scoring_settings;
  const pts=s=>{let t=0;for(const k of ["pts","reb","ast","stl","blk","to","tpm"])t+=(s[k]||0)*(sc[k]||0);t+=(s.dd||0)*(sc.dd||0)+(s.td||0)*(sc.td||0);return t};
  const myU=V.users.find(u=>u.display_name?.toLowerCase()==="jackhill1617"),ro=V.rosters.find(r=>r.owner_id===myU?.user_id)||{},mine=new Set(ro.players||[]);
  const inj={};for(const i of V.espn_injuries)inj[i.player.toLowerCase()]=i;
  const games={};for(const g of V.proj)if(mine.has(String(g.pid)))(games[g.pid]??=[]).push(g);
  const rows=[...mine].map(pid=>{const p=V.players[pid]||{name:pid},gs=(games[pid]||[]).sort((a,b)=>a.date.localeCompare(b.date)),pj=gs.map(g=>pts(g.stats)),i=inj[(p.name||"").toLowerCase()];return {p,gs,pj,i,best:Math.max(0,...pj)}}).sort((a,b)=>b.best-a.best);
  return `${age>8||errs.length?`<div class="card warn" style="margin-bottom:12px">⚠ Data ${age>8?"is "+Math.round(age)+"h old":"has failed sources: "+errs.join(", ")}</div>`:""}
  <h2>⚡ Your roster this week</h2><div class="sub">Raw Sleeper per-game projections in your league scoring (the replay-tested model replaces this next), with ESPN injury status.</div>
  <div class="card list">${rows.map(r=>`<div class="it"><div class="sp"><b>${esc(r.p.name)}</b> <span class="sub">${r.p.team||""} · ${(r.p.pos||[]).join("/")}</span><div class="sub">${r.gs.length?r.gs.map((g,i)=>`${g.date.slice(5)} ${esc(g.opp||"")} ${f1(r.pj[i])}`).join(" · "):"no games projected"}</div>${r.i?`<span class="pill ${r.i.status==="Out"?"rd":"or"}">ESPN: ${esc(r.i.status)}</span><span class="sub">${esc(r.i.note||"")}</span>`:""}</div><div style="text-align:right"><span class="num">${r.gs.length}</span><div class="sub">games</div></div></div>`).join("")}</div>
  <h2 style="margin-top:20px">Trending adds (24h)</h2><div class="card list">${V.trending.slice(0,10).map(t=>{const p=V.players[t.player_id]||{};return `<div class="it"><div class="sp"><b>${esc(p.name||t.player_id)}</b> <span class="sub">${p.team||""} · ${(p.pos||[]).join("/")}</span></div><span class="num">${t.count}</span></div>`}).join("")}</div>`}
