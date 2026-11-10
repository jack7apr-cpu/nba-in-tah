"use strict";
const $=(s,e=document)=>e.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const nm=s=>String(s).replace(/ \(GPT\)/,""), f1=x=>Number(x).toFixed(1), ME="Jack";
const TABS=[["home","🏠","Home"],["lineup","📋","Lineup"],["weeks","📅","Weeks"],["mgrs","👥","Managers"],["locks","🔒","Lock Lab"],["players","🏀","Players"],["waivers","🔄","Waivers"],["live","⚡","Live"],["moves","🔁","Moves"],["fun","🎉","Fun"],["odds","🔮","Odds"],["trades","🤝","Trades"]];
let D={}, S={tab:"home",wk:null,lk:{mgr:"All",wk:"All",sort:"missed"},pl:{q:"",own:"All",pos:"All",sort:"avg"}};

Promise.all(["league_data","factfile","live","weeks_auto","plan","crystal","trades","locked","official","fa"].map(n=>fetch(`data/${n}.json`).then(r=>r.json()).catch(()=>null))).then(([L,F,V,A,P,C,T,K,O,FA])=>{
  D.L=L; D.F=F; D.V=V; D.A=A||{}; D.P=P; D.C=C; D.T=T; D.K=K; D.O=O; D.FA=FA; prep(); S.wk=Math.max(...Object.keys(L.weeks).map(Number),...Object.keys(D.A).map(Number)); route(); addEventListener("hashchange",route);
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
const lockKey=()=>"locked-"+(D.P?.week??"");
function lockedSet(){const set=new Set(D.K&&D.K.week===D.P?.week?D.K.players:[]);try{for(const n of JSON.parse(localStorage.getItem(lockKey())||"[]"))set.add(n)}catch(e){}return set}
function toggleLock(n){let a=[];try{a=JSON.parse(localStorage.getItem(lockKey())||"[]")}catch(e){}const i=a.indexOf(n),on=i<0;on?a.push(n):a.splice(i,1);try{localStorage.setItem(lockKey(),JSON.stringify(a))}catch(e){}syncLock(n,on);route()}
function syncLock(n,on){let k="";try{k=localStorage.getItem("synckey")||"";if(!k){k=(prompt("Paste your sync key once (lets GitHub and Claude see what you lock). Cancel to keep it on this phone only.")||"").trim();if(k)localStorage.setItem("synckey",k)}}catch(e){}
  if(!k)return;fetch("https://ntfy.sh/"+encodeURIComponent(k),{method:"POST",body:JSON.stringify({w:D.P?.week,p:n,l:on})}).then(()=>toast(on?"Locked sent":"Undo sent")).catch(()=>toast("Could not sync"))}
function toast(t){const e=document.createElement("div");e.className="tt";e.style.cssText="left:50%;bottom:90px;transform:translateX(-50%);position:fixed";e.textContent=t;document.body.append(e);setTimeout(()=>e.remove(),1800)}
const verdict=b=>b>=85?"Ghost shit: no wipe needed":b>=70?"Textbook: two wipes":b>=55?"Solid log":b>=40?"Bit of a mess":b>=25?"Dodgy kebab":"Full norovirus";
const quad=m=>m.shit>=50&&m.poo>=50?"Big and clean":m.shit>=50?"Big log, messy wipe":m.poo>=50?"Small but tidy":"Small and messy";

function route(){
  S.tab=(location.hash||"#home").slice(1)||"home"; if(!TABS.some(t=>t[0]===S.tab))S.tab="home";
  document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("on",a.dataset.k===S.tab));
  const upd=D.V?.updated?new Date(D.V.updated):null;
  $("#sub").textContent=`Week ${D.V?.state?.week??"?"} · live data ${upd?upd.toLocaleString([], {weekday:"short",hour:"2-digit",minute:"2-digit"}):"unavailable"} · almanac through week ${Math.max(...Object.keys(D.L.weeks).map(Number))}`;
  $("#app").innerHTML=({home,weeks,mgrs,locks,players,waivers,live,odds,trades,lineup,fun,moves})[S.tab](); (after[S.tab]||(()=>{}))(); scrollTo(0,0);
}
const after={};
function chips(id,opts,cur){return `<div class="chips" id="${id}">${opts.map(o=>`<span class="chip ${String(o)===String(cur)?"on":""}" data-v="${esc(o)}">${esc(o)}</span>`).join("")}</div>`}
function bindChips(id,fn){document.querySelectorAll(`#${id} .chip`).forEach(c=>c.onclick=()=>fn(c.dataset.v))}
function sheet(html){const s=document.createElement("div");s.className="sheet";s.innerHTML=`<div><button class="x">×</button>${html}</div>`;s.onclick=e=>{if(e.target===s||e.target.className==="x")s.remove()};document.body.append(s)}
function tip(el,fn){const t=$("#tt");el.onmousemove=e=>{t.hidden=false;t.innerHTML=fn();t.style.left=Math.min(e.clientX+12,innerWidth-200)+"px";t.style.top=e.clientY+12+"px"};el.onmouseleave=()=>t.hidden=true;el.onclick=e=>{e.stopPropagation();el.onmousemove(e)}}

/* HOME */
function nowBanner(){
  const out=[],P=D.P?.teams?.[ME],V=D.V;
  const LK=lockedSet();if(P)for(const s of P.slots)if(s.chances[0]?.act==="LOCK"&&!LK.has(s.player))out.push(`<b class="pos">Lock ${esc(s.player)}</b> <span class="sub">beats the rest of his week</span>`);
  if(V){const users=V.users.find(u=>u.display_name?.toLowerCase()==="jackhill1617"),ro=V.rosters.find(r=>r.owner_id===users?.user_id),inj={};for(const i of V.espn_injuries)inj[i.player.toLowerCase()]=i;
    for(const pid of ro?.starters||[]){const p=V.players[pid],i=p&&inj[p.name.toLowerCase()];if(i&&/out|doubtful|questionable|day/i.test(i.status))out.push(`<b class="${/out|doubt/i.test(i.status)?"neg":"or"}" style="${/out|doubt/i.test(i.status)?"":"color:var(--or)"}">${esc(p.name)}: ${esc(i.status)}</b> <span class="sub">check before tip</span>`)}
    const age=(Date.now()-new Date(V.updated))/36e5;if(age>8)out.push(`<b class="neg">Data is ${Math.round(age)}h old</b>`)}
  return `<div class="card" style="margin-bottom:12px;border-color:${out.length?"var(--or)":"var(--line)"}"><div class="lbl">${out.length?"Do now":"Right now"}</div>${out.length?out.map(x=>`<div style="margin-top:4px">${x}</div>`).join(""):'<div style="margin-top:4px">Nothing needs doing. All clear.</div>'}</div>`}
function home(){
  const m=D.M, me=m[ME], best=[...D.rank].sort((a,b)=>m[b].pf-m[a].pf)[0];
  setTimeout(()=>{document.querySelectorAll(".bar i").forEach(i=>i.style.width=i.dataset.w+"%")},50);
  after.home=()=>{drawQuad();document.querySelectorAll("[data-m]").forEach(c=>c.onclick=()=>mgrSheet(c.dataset.m))};
  return `${nowBanner()}<div class="grid g4">
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
  const ws=[...new Set([...Object.keys(D.L.weeks),...Object.keys(D.A)].map(Number))].sort((a,b)=>a-b);
  if(!D.L.weeks[S.wk]){const A=JSON.parse(JSON.stringify(D.A[S.wk]||{matchups:[]})),OF=D.O?.weeks?.[S.wk];if(OF){A.status="official";for(const [a,b] of A.matchups){a.pts=OF[a.mgr]??a.pts;b.pts=OF[b.mgr]??b.pts}}after.weeks=()=>{bindChips("wkc",v=>{S.wk=+v.replace("Week ","");route()});document.querySelectorAll("[data-au]").forEach(c=>c.onclick=()=>autoSheet(+c.dataset.au))};
    return `${chips("wkc",ws.map(x=>"Week "+x),"Week "+S.wk)}<div class="card warn" style="margin-bottom:12px">${A.status==="official"?"Official team totals (Sleeper season points, matches the official Lock-In scores). Slot-by-slot locks and Isaac's recap are added after the week.":A.status==="live"?"Live week: scores come straight from Sleeper's API and can differ from the official Lock-In counted totals. Official totals appear automatically when the week settles.":"Week not yet curated: raw API scores."}</div><div class="grid g2">${A.matchups.map(([a,b],i)=>`<div class="card tap" data-au="${i}"><div class="row"><b ${a.pts>b.pts?'style="color:var(--gr)"':""}>${a.mgr}</b><span class="sp"></span><span class="num">${a.pts}</span></div><div class="row"><b ${b.pts>a.pts?'style="color:var(--gr)"':""}>${b.mgr}</b><span class="sp"></span><span class="num">${b.pts}</span></div><div class="sub" style="margin-top:6px">tap for slots</div></div>`).join("")||'<div class="card sub">No matchups yet.</div>'}</div>`}
  const w=D.L.weeks[S.wk]; after.weeks=()=>{bindChips("wkc",v=>{S.wk=+v.replace("Week ","");route()});document.querySelectorAll("[data-mu]").forEach(c=>c.onclick=()=>muSheet(+c.dataset.mu))};
  const aw=w.isaac?.awards||{};
  return `${chips("wkc",ws.map(x=>"Week "+x),"Week "+S.wk)}
  <div class="grid g2">${w.matchups.map(([a,pa,b,pb],i)=>{const win=pa>pb;return `<div class="card tap" data-mu="${i}"><div class="row"><b ${win?'style="color:var(--gr)"':""}>${a}</b><span class="sp"></span><span class="num">${pa}</span></div><div class="row"><b ${!win?'style="color:var(--gr)"':""}>${b}</b><span class="sp"></span><span class="num">${pb}</span></div><div class="sub" style="margin-top:6px">margin ${f1(Math.abs(pa-pb))} · tap for locks</div></div>`}).join("")}</div>
  <h2 style="margin-top:20px">🏅 Isaac's awards</h2><div class="grid g4">${Object.entries(aw).map(([k,v])=>`<div class="card"><div class="lbl">${esc(k)}</div><div style="margin-top:4px">${esc(v)||"–"}</div></div>`).join("")||'<div class="card sub">No awards logged.</div>'}</div>
  <h2 style="margin-top:20px">Claude's read</h2><div class="card">${esc(w.claude?.text||"")}</div>
  <h2 style="margin-top:20px">Isaac's recap</h2><div class="recap">${esc(w.isaac?.text||"No recap yet.")}</div>`;
}
function muSheet(i){const w=D.L.weeks[S.wk],[a,pa,b,pb]=w.matchups[i];const col=n=>`<div><h3>${n}</h3>${(w.locks[n]||[]).map(([p,s])=>`<div class="row" style="padding:4px 0"><span class="sp">${esc(p)}</span><span class="num ${s<18?"neg":s>=35?"pos":""}">${s}</span></div>`).join("")}</div>`;sheet(`<h2>${a} ${pa} – ${pb} ${b}</h2><div class="grid g2">${col(a)}${col(b)}</div>`)}

function autoSheet(i){const [a,b]=D.A[S.wk].matchups[i];const col=x=>`<div><h3>${x.mgr} · ${x.pts}</h3>${x.slots.map(([sl,p,pt])=>`<div class="row" style="padding:4px 0"><span class="pill">${sl}</span><span class="sp">${esc(p)}</span><span class="num ${pt===0?"mut":pt>=35?"pos":""}">${pt}</span></div>`).join("")}</div>`;sheet(`<h2>${a.mgr} vs ${b.mgr}</h2><div class="grid g2">${col(a)}${col(b)}</div>`)}

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
function planCard(){const P=D.P;if(!P)return "";const t=P.teams[ME];if(!t)return "";
  const LK=lockedSet(),lock=t.slots.filter(s=>s.chances[0]?.act==="LOCK"&&!LK.has(s.player));after.live=()=>document.querySelectorAll("[data-lk]").forEach(e=>e.onclick=ev=>{ev.stopPropagation();toggleLock(e.dataset.lk)});
  const pill=c=>c.act==="LOCK"?'<span class="pill gr">LOCK NOW</span>':c.act==="HOLD"?'<span class="pill">hold</span>':c.act==="FORCED"?'<span class="pill rd">final chance</span>':`<span class="pill or">lock if ≥ ${c.th}</span>`;
  return `<h2>🔒 Lock plan · week ${P.week}</h2><div class="sub">From the replay-tested model: each slot is a run of chances, and you lock when the score beats what the rest of the week is worth. Built ${P.today}. Sleeper doesn't tell the site what you've locked, so tap <b>I locked</b> on a slot to clear it here.</div>
  ${lock.length?`<div class="card" style="border-color:var(--gr);margin:10px 0"><div class="lbl">Do now</div>${lock.map(s=>`<div class="big" style="font-size:22px;color:var(--gr)">Lock ${esc(s.player)}</div><div class="sub">his score beats the rest of the week (worth ${s.worth})</div>`).join("")}</div>`:'<div class="card" style="margin:10px 0">Nothing to lock right now. Hold everyone.</div>'}
  <div class="card list">${t.slots.map(s=>{const n=s.chances[0];return `<div class="it" data-sl="${esc(s.slot)}"><span class="pill">${s.slot}</span><div class="sp"><b>${esc(s.player)}</b> <span class="sub">worth ${s.worth}</span><div class="sub">${s.chances.map(c=>`${c.date.slice(5)} ${c.free?"🎲 "+esc(c.player):""} ${Math.round(c.plays*100)}% · ${c.exp}`).join(" → ")}</div></div>${LK.has(s.player)?'<span class="pill gr">locked ✓</span>':n?pill(n):""}<span class="pill" data-lk="${esc(s.player)}" style="cursor:pointer">${LK.has(s.player)?"undo":"I locked"}</span></div>`}).join("")}</div>
  <div class="sub" style="margin:6px 0 18px">Expected lineup total ${t.total}. Bench: ${t.bench.map(b=>esc(b.player)).join(", ")||"–"}.</div>`}
function live(){const V=D.V;if(!V)return '<div class="card warn">Live data unavailable.</div>';
  const age=(Date.now()-new Date(V.updated))/36e5,errs=Object.keys(V.errors||{}),sc=V.league.scoring_settings;
  const pts=s=>{let t=0;for(const k of ["pts","reb","ast","stl","blk","to","tpm"])t+=(s[k]||0)*(sc[k]||0);t+=(s.dd||0)*(sc.dd||0)+(s.td||0)*(sc.td||0);return t};
  const myU=V.users.find(u=>u.display_name?.toLowerCase()==="jackhill1617"),ro=V.rosters.find(r=>r.owner_id===myU?.user_id)||{},mine=new Set(ro.players||[]);
  const inj={};for(const i of V.espn_injuries)inj[i.player.toLowerCase()]=i;
  const games={};for(const g of V.proj)if(mine.has(String(g.pid)))(games[g.pid]??=[]).push(g);
  const rows=[...mine].map(pid=>{const p=V.players[pid]||{name:pid},gs=(games[pid]||[]).sort((a,b)=>a.date.localeCompare(b.date)),pj=gs.map(g=>pts(g.stats)),i=inj[(p.name||"").toLowerCase()];return {p,gs,pj,i,best:Math.max(0,...pj)}}).sort((a,b)=>b.best-a.best);
  return `${age>8||errs.length?`<div class="card warn" style="margin-bottom:12px">⚠ Data ${age>8?"is "+Math.round(age)+"h old":"has failed sources: "+errs.join(", ")}</div>`:""}
  ${planCard()}<h2>⚡ Your roster this week</h2><div class="sub">Raw Sleeper per-game projections in your league scoring (the replay-tested model replaces this next), with ESPN injury status.</div>
  <div class="card list">${rows.map(r=>`<div class="it"><div class="sp"><b>${esc(r.p.name)}</b> <span class="sub">${r.p.team||""} · ${(r.p.pos||[]).join("/")}</span><div class="sub">${r.gs.length?r.gs.map((g,i)=>`${g.date.slice(5)} ${esc(g.opp||"")} ${f1(r.pj[i])}`).join(" · "):"no games projected"}</div>${r.i?`<span class="pill ${r.i.status==="Out"?"rd":"or"}">ESPN: ${esc(r.i.status)}</span><span class="sub">${esc(r.i.note||"")}</span>`:""}</div><div style="text-align:right"><span class="num">${r.gs.length}</span><div class="sub">games</div></div></div>`).join("")}</div>
  <h2 style="margin-top:20px">Trending adds (24h)</h2><div class="card list">${V.trending.slice(0,10).map(t=>{const p=V.players[t.player_id]||{};return `<div class="it"><div class="sp"><b>${esc(p.name||t.player_id)}</b> <span class="sub">${p.team||""} · ${(p.pos||[]).join("/")}</span></div><span class="num">${t.count}</span></div>`}).join("")}</div>`}

/* ODDS (Crystal Ball) */
function odds(){const C=D.C;if(!C)return '<div class="card warn">Odds not built yet.</div>';
  const t=C.teams,names=Object.keys(t).sort((a,b)=>t[b].title+t[b].playoffs*.001-t[a].title-t[a].playoffs*.001),pc=x=>(x*100).toFixed(x<.1&&x>0?1:0)+"%";
  setTimeout(()=>document.querySelectorAll("#odds .bar i").forEach(i=>i.style.width=i.dataset.w+"%"),50);
  after.odds=()=>document.querySelectorAll("[data-o]").forEach(c=>c.onclick=()=>oddsSheet(c.dataset.o));
  const ji=C.jack_if,opp=C.jack_opp;
  return `<h2>🔮 Crystal Ball</h2><div class="sub">${C.runs.toLocaleString()} simulated seasons from week ${C.week}. Top ${C.n_playoff} make the playoffs (week ${C.playoff_start}+). Tap a team for its win range.</div>
  ${ji&&ji.win?`<div class="grid g2" style="margin:12px 0"><div class="card"><div class="lbl">Your week ${C.week} vs ${esc(opp)}</div><div style="margin-top:6px">If you <b class="pos">win</b>: bye <b>${pc(ji.win.bye)}</b> · title <b>${pc(ji.win.title)}</b></div><div>If you <b class="neg">lose</b>: bye <b>${pc(ji.loss.bye)}</b> · title <b>${pc(ji.loss.title)}</b></div><div class="sub" style="margin-top:6px">How much this one result moves your season.</div></div>
  <div class="card"><div class="lbl">Your title odds</div><div class="big" style="color:var(--or)">${pc(t[ME].title)}</div><div class="sub">expected wins ${t[ME].exp_wins.toFixed(1)}</div></div></div>`:""}
  <div id="odds" class="card">${names.map(n=>{const x=t[n];return `<div class="it" data-o="${n}" style="display:block;padding:10px 4px"><div class="row"><b>${n}</b><span class="sub">${x.w}–${x.l}</span><span class="sp"></span><span class="num">${pc(x.title)} title</span></div>
   <div class="sub">make playoffs ${pc(x.playoffs)} · bye ${pc(x.bye)} · #1 seed ${pc(x.seed1)}</div><div class="bar" style="margin-top:4px"><i data-w="${x.playoffs*100}" style="width:0"></i></div></div>`}).join("")}</div>
  <div class="sub" style="margin-top:10px">${C.assumptions.map(a=>"• "+esc(a)).join("<br>")}</div>`}
function oddsSheet(n){const x=D.C.teams[n],ks=Object.keys(x.dist).map(Number),mx=Math.max(...Object.values(x.dist));
  sheet(`<h2>${n}</h2><div class="sub">Now ${x.w}–${x.l}. Scores like ${x.mu} a week. Expected final wins ${x.exp_wins.toFixed(1)}.</div>
  <h3 style="margin-top:12px">Where the regular season ends (wins)</h3><div style="display:flex;align-items:flex-end;gap:3px;height:120px;margin-top:8px">${ks.map(k=>`<div title="${k} wins: ${(x.dist[k]*100).toFixed(1)}%" style="flex:1;background:linear-gradient(0deg,var(--or),var(--yl));border-radius:4px 4px 0 0;height:${Math.max(2,x.dist[k]/mx*100)}%"></div>`).join("")}</div><div class="row sub" style="justify-content:space-between"><span>${ks[0]} wins</span><span>${ks[ks.length-1]} wins</span></div>
  <div class="grid g4" style="margin-top:12px">${[["Playoffs",x.playoffs],["Bye",x.bye],["#1 seed",x.seed1],["Title",x.title]].map(([a,b])=>`<div class="card"><div class="lbl">${a}</div><div class="big" style="font-size:22px">${(b*100).toFixed(1)}%</div></div>`).join("")}</div>`)}

/* TRADE LAB */
S.tr={own:"All",sort:"ours",give:[],get:[]};
function trades(){const T=D.T;if(!T)return '<div class="card warn">Trade data not built yet.</div>';
  after.trades=()=>{bindChips("tro",v=>{S.tr.own=v;route()});bindChips("trs",v=>{S.tr.sort=v;route()});
    document.querySelectorAll("[data-b]").forEach(e=>e.onclick=()=>{const b=T.board[e.dataset.b],side=b.owner===ME?"give":"get";if(b.owner==="FA")return;const a=S.tr[side],i=a.indexOf(b.name);i<0?a.push(b.name):a.splice(i,1);route()})};
  const owners=["All",...new Set(T.board.map(b=>b.owner))],B=T.board,by=Object.fromEntries(B.map(b=>[b.name,b]));
  const sum=(arr,k)=>arr.reduce((t,n)=>t+(by[n]?.[k]||0),0),gO=sum(S.tr.give,"ours"),tO=sum(S.tr.get,"ours"),gM=sum(S.tr.give,"market"),tM=sum(S.tr.get,"market");
  const rows=B.filter(b=>S.tr.own==="All"||b.owner===S.tr.own).sort((a,b)=>S.tr.sort==="gap"?b.gap-a.gap:S.tr.sort==="market"?b.market-a.market:b.ours-a.ours).slice(0,60);
  return `<h2>🤝 Trade Lab</h2><div class="sub">${esc(T.note)}</div>
  <h3 style="margin-top:14px">Win-win ideas for you</h3><div class="sub">Both lineups improve over the remaining weeks (our proxy for "they'd say yes"). Points = change in best-lineup value to season end.</div>
  <div class="card list">${T.ideas.map(i=>`<div class="it" style="display:block"><div class="row"><b>${esc(i.give.join(" + "))}</b><span class="mut">for</span><b>${esc(i.get.join(" + "))}</b></div><div class="sub">with ${i.with} · you <span class="pos">+${i.me}</span> · them <span class="pos">+${i.them}</span></div></div>`).join("")||'<div class="sub">No mutually good trades right now.</div>'}</div>
  <h3 style="margin-top:18px">Try your own</h3><div class="sub">Tap your players to give, then theirs to get (tap again to remove). A quick value check, not the full lineup model.</div>
  <div class="card" style="margin:8px 0"><div>Give: <b>${esc(S.tr.give.join(", ")||"–")}</b> <span class="sub">(${gO} ours · ${gM} market)</span></div><div>Get: <b>${esc(S.tr.get.join(", ")||"–")}</b> <span class="sub">(${tO} ours · ${tM} market)</span></div>
  ${S.tr.give.length&&S.tr.get.length?`<div class="big" style="font-size:22px;margin-top:6px;color:${tO-gO>=0?"var(--gr)":"var(--rd)"}">${tO-gO>=0?"+":""}${tO-gO} for you</div><div class="sub">${tO-gO<-20?"Fuck no.":tO-gO<0?"You lose value; only if you need the position.":"You win on our numbers; check if they'd accept ("+(tM-gM>0?"market says they lose":"market says it's fair to them")+")."}</div>`:""}</div>
  ${chips("tro",owners,S.tr.own)}${chips("trs",["ours","market","gap"],S.tr.sort)}
  <div class="card list">${rows.map((b,i)=>`<div class="it" data-b="${B.indexOf(b)}"><span class="pill ${b.inj&&b.inj!=="Active"?"rd":"bl"}">${(b.pos||[])[0]||"-"}</span><div class="sp"><b>${esc(b.name)}</b> ${S.tr.give.includes(b.name)||S.tr.get.includes(b.name)?'<span class="pill gr">selected</span>':""}<div class="sub">${b.owner} · ${b.team||""}${b.inj?" · "+esc(b.inj):""}</div></div><div style="text-align:right"><span class="num">${b.ours}</span><div class="sub">mkt ${b.market} · <span class="${b.gap>=0?"pos":"neg"}">${b.gap>=0?"+":""}${b.gap}</span></div></div></div>`).join("")}</div>`}

/* LINEUP: what to start each day, free rolls included */
const SLOT_ORDER=["PG","SG","G","SF","PF","F","C","UTIL","UTIL"];
function lineup(){const P=D.P?.teams?.[ME];if(!P)return '<div class="card warn">Plan not built yet.</div>';
  const days=[...new Set(P.slots.flatMap(s=>s.chances.map(c=>c.date)))].sort();if(!days.length)return '<div class="card">No games left this week.</div>';
  if(!S.day||!days.includes(S.day))S.day=days.find(d=>d>=D.P.today)||days[0];
  const LK=lockedSet(),order=[...P.slots].sort((a,b)=>{const ia=SLOT_ORDER.indexOf(a.slot),ib=SLOT_ORDER.indexOf(b.slot);return ia-ib}),dn=d=>new Date(d+"T12:00:00").toLocaleDateString([],{weekday:"short",day:"numeric"});
  after.lineup=()=>{bindChips("dy",v=>{S.day=days.find(d=>dn(d)===v);route()});document.querySelectorAll("[data-lk]").forEach(e=>e.onclick=()=>toggleLock(e.dataset.lk))};
  const rows=order.map(s=>{const c=s.chances.find(c=>c.date===S.day),lk=LK.has(s.player);
    if(lk)return `<div class="it" style="display:block"><div class="row"><span class="pill">${s.slot}</span><b>${esc(s.player)}</b><span class="sp"></span><span class="pill gr">locked ✓ leave him</span><span class="pill" data-lk="${esc(s.player)}" style="cursor:pointer">undo</span></div></div>`;
    if(!c)return `<div class="it" style="display:block"><div class="row"><span class="pill">${s.slot}</span><span class="mut">${esc(s.player)}: nobody to play today</span></div></div>`;
    const act=c.act==="LOCK"?'<span class="pill gr">LOCK NOW</span>':c.act==="HOLD"?'<span class="pill">scored, hold</span>':c.act==="FORCED"?'<span class="pill rd">final chance</span>':`<span class="pill or">lock if ≥ ${c.th}</span>`;
    return `<div class="it" style="display:block"><div class="row"><span class="pill">${s.slot}</span><b>${esc(c.player)}</b>${c.free?'<span class="pill bl">🎲 free roll</span>':""}<span class="sp"></span>${act}</div><div class="sub">${Math.round(c.plays*100)}% to play · expects ${c.exp}${c.free?` · swap in for ${esc(s.player)} before tip`:""}</div><div class="row" style="margin-top:4px"><span class="sub sp">regular: ${esc(s.player)}</span><span class="pill" data-lk="${esc(c.player)}" style="cursor:pointer">I locked</span></div></div>`}).join("");
  const benchToday=P.bench.map(b=>b.player);
  return `<h2>📋 Your lineup</h2><div class="sub">The best 9 for each day, free rolls included. Set it in the Sleeper app before the first tip each day. Free roll = a bench player in a slot on a night your regular doesn't play (costs nothing while unlocked).</div>
  ${chips("dy",days.map(dn),dn(S.day))}<div class="card list">${rows}</div>
  <div class="sub" style="margin:8px 0">Bench: ${benchToday.map(esc).join(", ")||"–"}. Tap <b>I locked</b> after you lock someone. Sleeper can't tell us.</div>`}

/* FUN: awards tally, fun metrics, weekly score lines, head-to-head */
S.h2h=["Jack","Isaac"];S.hl=null;
const AW=["Biggest Chud","Holy Glaze","Heaven","Hell","Shit vs Poo"];
function funStats(){const m={};for(const n of D.rank)m[n]={f40:0,f30:0,stink:0,zero:0,perfect:0,n:0,left:0};
  for(const l of D.locks){const x=m[l.mgr];if(!x)continue;x.n++;if(l.locked>=40)x.f40++;if(l.locked>=30)x.f30++;if(l.locked<15)x.stink++;if(l.locked<=0)x.zero++;if(l.missed<=0)x.perfect++;x.left+=l.missed}return m}
function awardTally(){const t={};for(const n of D.rank)t[n]={};for(const [w,x] of Object.entries(D.L.weeks))for(const [k,v] of Object.entries(x.isaac?.awards||{}))for(const n of D.rank)if(new RegExp("\\b"+n+"\\b","i").test(v||""))t[n][k]=(t[n][k]||0)+1;return t}
function fun(){const fs=funStats(),T=awardTally(),weeks=Object.keys(D.wk).sort((a,b)=>a-b);
  after.fun=()=>{bindChips("h1",v=>{S.h2h[0]=v;route()});bindChips("h2",v=>{S.h2h[1]=v;route()});document.querySelectorAll("[data-ln]").forEach(e=>e.onclick=()=>{S.hl=S.hl===e.dataset.ln?null:e.dataset.ln;route()})};
  const cards=[["🏆 Points leader",n=>D.M[n].pf,x=>f1(x)+" pts"],["🎯 Best lock average",n=>D.M[n].lockavg,x=>f1(x)],["💥 Most 40+ locks",n=>fs[n].f40,x=>x],["🧻 Most stinkers (<15)",n=>fs[n].stink,x=>x],["✨ Most perfect locks",n=>fs[n].perfect,x=>x],["🕳️ Points left on bench",n=>fs[n].left,x=>f1(x)]];
  const hi=cards.map(([t,f,fmt])=>{const o=[...D.rank].sort((a,b)=>f(b)-f(a));return `<div class="card"><div class="lbl">${t}</div><div class="big" style="font-size:24px">${o[0]}</div><div class="sub">${fmt(f(o[0]))} · last: ${o[o.length-1]} ${fmt(f(o[o.length-1]))}</div></div>`}).join("");
  const W=640,H=240,P=34,all=D.rank.flatMap(n=>weeks.map(w=>D.wk[w][n]).filter(v=>v!=null)),lo=Math.floor(Math.min(...all)/20)*20,hiY=Math.ceil(Math.max(...all)/20)*20,x=i=>P+i*(W-P-12)/Math.max(1,weeks.length-1),y=v=>H-P-(v-lo)/(hiY-lo)*(H-P-12);
  const cols=["#ff7a1a","#5aa9ff","#35e0a1","#ffd23f","#c084fc","#ff4d6d","#2dd4bf","#a3a3a3"];
  const lines=D.rank.map((n,k)=>{const pts=weeks.map((w,i)=>[x(i),y(D.wk[w][n]),D.wk[w][n]]).filter(p=>p[1]===p[1]),on=!S.hl||S.hl===n;return `<g opacity="${on?1:.15}"><polyline fill="none" stroke="${cols[k]}" stroke-width="${n===ME||S.hl===n?3:1.8}" points="${pts.map(p=>p[0]+","+p[1]).join(" ")}"/>${pts.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="3.5" fill="${cols[k]}"><title>${n}: ${p[2]}</title></circle>`).join("")}</g>`}).join("");
  const grid=[0,1,2,3,4].map(i=>{const v=lo+(hiY-lo)*i/4;return `<line x1="${P}" x2="${W-8}" y1="${y(v)}" y2="${y(v)}" stroke="#222c4a"/><text x="4" y="${y(v)+4}">${Math.round(v)}</text>`}).join("")+weeks.map((w,i)=>`<text x="${x(i)}" y="${H-10}" text-anchor="middle">W${w}</text>`).join("");
  const legend=D.rank.map((n,k)=>`<span class="chip ${S.hl===n?"on":""}" data-ln="${n}" style="border-color:${cols[k]}">${n}</span>`).join("");
  const [a,b]=S.h2h,rows=[["Record",n=>D.M[n].w+"–"+D.M[n].l],["Points for",n=>f1(D.M[n].pf)],["Avg week",n=>f1(D.M[n].avgweek)],["Best week",n=>D.M[n].hi],["Worst week",n=>D.M[n].lo],["Lock avg",n=>f1(D.M[n].lockavg)],["Talent (Shit)",n=>f1(D.M[n].shit)],["Cleanliness (Poo)",n=>f1(D.M[n].poo)],["Bowel score",n=>f1(D.M[n].bowel)],["40+ locks",n=>fs[n].f40],["Stinkers",n=>fs[n].stink]];
  const met=weeks.filter(w=>a in D.wk[w]&&b in D.wk[w]).map(w=>`W${w}: ${D.wk[w][a]}–${D.wk[w][b]}`).join(" · ");
  const awRows=D.rank.map(n=>`<tr><td><b>${n}</b></td>${AW.map(k=>`<td class="num">${T[n][k]||"·"}</td>`).join("")}</tr>`).join("");
  return `<h2>🎉 Fun</h2><div class="grid g2">${hi}</div>
  <h3 style="margin-top:20px">Weekly scores</h3><div class="sub">Tap a name to highlight a line. Tap a dot for the score.</div><div class="chips">${legend}</div>
  <div class="card"><svg viewBox="0 0 ${W} ${H}" style="width:100%">${grid}${lines}</svg></div>
  <h3 style="margin-top:20px">Head to head</h3>${chips("h1",D.rank,a)}${chips("h2",D.rank,b)}
  <div class="card"><div class="row" style="font-weight:700"><span class="sp mut"></span><span style="width:90px;text-align:right">${a}</span><span style="width:90px;text-align:right">${b}</span></div>${rows.map(([t,f])=>`<div class="row" style="padding:5px 0;border-top:1px solid var(--line)"><span class="sp mut">${t}</span><span class="num" style="width:90px;text-align:right">${f(a)}</span><span class="num" style="width:90px;text-align:right">${f(b)}</span></div>`).join("")}${met?`<div class="sub" style="margin-top:8px">Played each other: ${met}</div>`:'<div class="sub" style="margin-top:8px">Not played yet.</div>'}</div>
  <h3 style="margin-top:20px">🏅 Isaac's awards tally</h3><div class="card tw"><table><tr><th>Manager</th>${AW.map(k=>`<th>${k.replace("Biggest ","").replace("Shit vs Poo","S v P")}</th>`).join("")}</tr>${awRows}</table></div>`}

/* MOVES: matchup stance + free agents */
function moves(){const X=D.FA;if(!X)return '<div class="card warn">Not built yet.</div>';const m=X.matchup;
  return `<h2>🔁 Moves</h2>${m?`<div class="card"><div class="lbl">Your week ${X.week} vs ${esc(m.opp)}</div><div class="big" style="color:${m.p_win>=.5?"var(--gr)":"var(--rd)"}">${Math.round(m.p_win*100)}% to win</div>
  <div class="sub">Expected locked totals: you ${m.mine} · ${esc(m.opp)} ${m.theirs}</div><div style="margin-top:8px"><b>Lock stance:</b> ${esc(m.stance)}</div>
  <div class="sub" style="margin-top:6px">Sleeper's own box shows a closer game because it uses single-game projections. This number assumes both of you lock sensibly, so ${esc(m.opp)} (who barely uses locks) is probably weaker than shown. A heuristic on top of the model.</div></div>`:""}
  <h3 style="margin-top:18px">Free agents worth adding</h3><div class="sub">Best add/drop for your lineup. <b>Rest of season</b> and <b>this week</b> are the change in your best-lineup Lock-In points. Streamers show up in "this week".</div>
  <div class="card list">${X.fa.map(f=>`<div class="it" style="display:block"><div class="row"><b>Add ${esc(f.add)}</b><span class="pill">${(f.pos||[]).join("/")}</span><span class="sp"></span><span class="num pos">+${f.ros} ros</span></div><div class="sub">drop ${esc(f.drop)} · this week ${f.week>=0?"+":""}${f.week} · value ${f.value}</div></div>`).join("")||'<div class="sub">No pickup beats your current bench.</div>'}</div>
  <div class="sub" style="margin-top:8px">Waivers are rolling, so claims run in priority order. Check the player isn't hurt or on a back-to-back before claiming.</div>`}
