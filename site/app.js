"use strict";
const $=(s,e=document)=>e.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const nm=s=>String(s).replace(/ \(GPT\)/,""), f1=x=>Number(x).toFixed(1), ME="Jack";
const TABS=[["home","🏠","Home"],["lineup","📋","Lineup"],["weeks","📅","Weeks"],["mgrs","👥","Managers"],["locks","🔒","Lock Lab"],["players","🏀","Players"],["waivers","🔄","Waivers"],["live","⚡","Live"],["moves","🔁","Moves"],["fun","🎉","Fun"],["guide","📖","Guide"],["odds","🔮","Odds"],["trades","🤝","Trades"]];
let D={}, S={tab:"home",wk:null,lk:{mgr:"All",wk:"All",sort:"missed"},pl:{q:"",own:"All",pos:"All",sort:"avg"}};

Promise.all(["league_data","factfile","live","weeks_auto","plan","crystal","trades","locked","official","fa","auto","review","formats","salaries","guide","values"].map(n=>fetch(`data/${n}.json?t=${Date.now()}`).then(r=>r.json()).catch(()=>null))).then(([L,F,V,A,P,C,T,K,O,FA,AU,RV,FM,SAL,GD,TV])=>{
  D.GD=GD; D.TV=TV;
  D.L=L; D.F=F; D.V=V; D.A=A||{}; D.P=P; D.C=C; D.T=T; D.K=K; D.O=O; D.FA=FA; D.AU=AU; D.RV=RV; D.FM=FM; D.SAL=SAL; prep(); S.wk=Math.max(...Object.keys(L.weeks).map(Number),...Object.keys(D.A).map(Number)); route(); addEventListener("hashchange",route);
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
  D.locks=F.locks.map(l=>({...l,mgr:nm(l.mgr)})); D.players=(D.AU?.players?.length?D.AU.players:F.players); D.fa=(D.AU?.fa?.length?D.AU.fa:F.fa).map(x=>({...x,mgr:nm(x.mgr)}));
  $("#nav").innerHTML=TABS.map(([k,i,t])=>`<a href="#${k}" data-k="${k}"><b>${i}</b>${t}</a>`).join("");
}
const lockKey=()=>"locked-"+(D.P?.week??"");
function ls(k){try{return JSON.parse(localStorage.getItem(k+lockKey())||"[]")}catch(e){return []}}
function lockedSet(){const set=new Set(D.K&&D.K.week===D.P?.week?D.K.players:[]);for(const n of ls("on-"))set.add(n);for(const n of ls("off-"))set.delete(n);return set}
function toggleLock(n){const on=!lockedSet().has(n);let a=ls("on-"),b=ls("off-");a=a.filter(x=>x!==n);b=b.filter(x=>x!==n);(on?a:b).push(n);try{localStorage.setItem("on-"+lockKey(),JSON.stringify(a));localStorage.setItem("off-"+lockKey(),JSON.stringify(b))}catch(e){}syncLock(n,on);route()}
function keyStores(){return [["localStorage",k=>localStorage.getItem(k),(k,v)=>localStorage.setItem(k,v)],["sessionStorage",k=>sessionStorage.getItem(k),(k,v)=>sessionStorage.setItem(k,v)],["cookie",k=>{const m=document.cookie.match(new RegExp("(?:^|; )"+k+"=([^;]*)"));return m?decodeURIComponent(m[1]):""},(k,v)=>{document.cookie=k+"="+encodeURIComponent(v)+"; max-age=31536000; path=/; SameSite=Lax"}]]}
function getKey(){let k="";try{const q=new URLSearchParams(location.search).get("k")||new URLSearchParams(location.hash.split("?")[1]||"").get("k");if(q){setKey(q);return q}}catch(e){}
  for(const [,g] of keyStores()){try{k=g("synckey");if(k){setKey(k);return k}}catch(e){}}return window.__synckey||""}
function setKey(k){window.__synckey=k;for(const [,,s] of keyStores()){try{s("synckey",k)}catch(e){}}}
function syncLock(n,on){const k=getKey();if(!k){toast("No sync key yet: paste it at the bottom of the Lineup tab");return}
  fetch("https://ntfy.sh/"+encodeURIComponent(k),{method:"POST",body:JSON.stringify({w:D.P?.week,p:n,l:on})}).then(()=>toast(on?"Locked sent":"Undo sent")).catch(()=>toast("Could not sync"))}
function keyCard(){const k=getKey();return `<div class="card" style="margin-top:12px"><div class="lbl">Sync key</div><div style="margin-top:4px">${k?`<b class="pos">Saved ✓</b> on this device (kept in several places so it survives Safari clean-ups).`:'<b class="neg">Not set</b>: lock taps stay on this phone only.'}</div>
  <div class="row" style="margin-top:8px"><input id="sk" type="search" placeholder="Paste your sync key" style="flex:1"><button id="skb" class="chip on" style="border:0">Save</button></div>
  <div class="sub" style="margin-top:6px">Tip: add this once to your Home Screen from a link ending in <code>?k=YOURKEY</code> and it can never be forgotten.</div></div>`}
function toast(t){const e=document.createElement("div");e.className="tt";e.style.cssText="left:50%;bottom:90px;transform:translateX(-50%);position:fixed";e.textContent=t;document.body.append(e);setTimeout(()=>e.remove(),1800)}
const verdict=b=>b>=85?"Ghost shit: no wipe needed":b>=70?"Textbook: two wipes":b>=55?"Solid log":b>=40?"Bit of a mess":b>=25?"Dodgy kebab":"Full norovirus";
const quad=m=>m.shit>=50&&m.poo>=50?"Big and clean":m.shit>=50?"Big log, messy wipe":m.poo>=50?"Small but tidy":"Small and messy";

function route(){
  S.tab=(location.hash||"#home").slice(1)||"home"; if(!TABS.some(t=>t[0]===S.tab))S.tab="home";
  document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("on",a.dataset.k===S.tab));
  const upd=D.V?.updated?new Date(D.V.updated):null;
  $("#sub").textContent=`Week ${D.V?.state?.week??"?"} · live data ${upd?upd.toLocaleString([], {weekday:"short",hour:"2-digit",minute:"2-digit"}):"unavailable"} · almanac through week ${Math.max(...Object.keys(D.L.weeks).map(Number))}`;
  $("#app").innerHTML=({home,weeks,mgrs,locks,players,waivers,live,odds,trades,lineup,fun,moves,guide})[S.tab](); (after[S.tab]||(()=>{}))(); scrollTo(0,0);
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
  <h2 style="margin-top:22px">💩 The Bowel Index</h2><div class="sub" style="margin-bottom:8px"><a href="almanac.xlsx" download style="color:var(--or)">⬇ Download the almanac as Excel</a><br><b>Shit</b> = how big the output is (roster talent). <b>Poo</b> = how clean the job is (lock efficiency). Results = all-play win %. Weighted 40/30/30. Tap anyone.</div>
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
  <div class="card list">${t.slots.map(s=>{const n=s.chances[0];return `<div class="it" data-sl="${esc(s.slot)}"><span class="pill">${s.slot}</span><div class="sp"><b>${esc(s.player)}</b> <span class="sub">worth ${s.worth}</span>${second(s.chances[0],true)}<div class="sub">${s.chances.map(c=>`${c.date.slice(5)} ${c.free?"🎲 "+esc(c.player):""} ${Math.round(c.plays*100)}% · ${c.exp}`).join(" → ")}</div></div>${LK.has(s.player)?'<span class="pill gr">locked ✓</span>':n?pill(n):""}<span class="pill" data-lk="${esc(s.player)}" style="cursor:pointer">${LK.has(s.player)?"undo":"I locked"}</span></div>`}).join("")}</div>
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

/* TRADE LAB: any two teams, live lineup maths */
S.tr={a:"Jack",b:"David",ga:[],gb:[],sort:"ours",sug:null,own:"All",mode:"both",lim:"25"};
const TSLOTS=["C","PG","SG","SF","PF","G","F","UTIL","UTIL"],TOK={PG:["PG"],SG:["SG"],G:["PG","SG"],SF:["SF"],PF:["PF"],F:["SF","PF"],C:["C"],UTIL:["PG","SG","SF","PF","C"]};
function best9(ps,w){const c=ps.map(p=>({p,v:p.weeks[w]||0})).filter(x=>x.v>0).sort((a,b)=>b.v-a.v).slice(0,14);let best=0;
  const dfs=(k,used,s)=>{if(k===9||!c.length){if(s>best)best=s;return}
    let rem=0,n=0;for(const x of c){if(!used.has(x)){rem+=x.v;if(++n===9-k)break}}if(s+rem<=best)return;
    let placed=false;for(const x of c){if(!used.has(x)&&TOK[TSLOTS[k]].some(q=>x.p.pos.includes(q))){placed=true;used.add(x);dfs(k+1,used,s+x.v);used.delete(x)}}
    if(!placed)dfs(k+1,used,s)};dfs(0,new Set(),0);return best}
function lineupValue(ps,V){let t=0;const per={};for(let w=V.w0;w<=V.last;w++){const v=best9(ps,String(w))*(w>=V.pstart?V.pw:1);per[w]=v;t+=v}return {t,per}}
function tradeEval(V,A,B,ga,gb){const pa=V.players.filter(p=>p.owner===A),pb=V.players.filter(p=>p.owner===B),by=Object.fromEntries(V.players.map(p=>[p.name,p]));
  const gaP=ga.map(n=>by[n]),gbP=gb.map(n=>by[n]);
  const newA=pa.filter(p=>!ga.includes(p.name)).concat(gbP),newB=pb.filter(p=>!gb.includes(p.name)).concat(gaP);
  const a0=lineupValue(pa,V),a1=lineupValue(newA,V),b0=lineupValue(pb,V),b1=lineupValue(newB,V);
  return {da:a1.t-a0.t,db:b1.t-b0.t,a0:a0.t,a1:a1.t,b0:b0.t,b1:b1.t,perA:a1.per,perA0:a0.per,perB:b1.per,perB0:b0.per,mkA:gbP.reduce((t,p)=>t+p.market,0)-gaP.reduce((t,p)=>t+p.market,0),mkB:gaP.reduce((t,p)=>t+p.market,0)-gbP.reduce((t,p)=>t+p.market,0),gaP,gbP,pa,pb,newA,newB}}
function trades(){const V=D.TV,T=D.T;if(!V)return '<div class="card warn">Trade data not built yet.</div>';
  const t=S.tr,teams=V.teams;
  after.trades=()=>{bindChips("tra",v=>{t.a=v;if(t.b===v)t.b=teams.find(x=>x!==v);t.ga=[];t.gb=[];t.sug=null;route()});bindChips("trb",v=>{t.b=v;if(t.a===v)t.a=teams.find(x=>x!==v);t.ga=[];t.gb=[];t.sug=null;route()});
    document.querySelectorAll("[data-tp]").forEach(e=>e.onclick=()=>{const[side,n]=e.dataset.tp.split("|"),arr=t[side],i=arr.indexOf(n);i<0?arr.push(n):arr.splice(i,1);t.sug=null;route()});
    const sg=document.getElementById("sug");if(sg)sg.onclick=()=>{sg.textContent="Searching…";setTimeout(()=>{t.sug=suggest(V,t.a,t.b,t.mode,t.lim);route()},30)};bindChips("tmd",v=>{t.mode=v==='Both win'?'both':v===('Best for '+t.a)?'a':'b';t.sug=null;route()});bindChips("tlm",v=>{t.lim=v.replace(/\D/g,'')||'999';t.sug=null;route()});
    document.querySelectorAll("[data-sg]").forEach(e=>e.onclick=()=>{const x=t.sug[+e.dataset.sg];t.ga=x.ga;t.gb=x.gb;route()});
    bindChips("tro",v=>{t.own=v;route()});bindChips("trs",v=>{t.sort=v;route()})};
  const pa=V.players.filter(p=>p.owner===t.a),pb=V.players.filter(p=>p.owner===t.b),both=t.ga.length&&t.gb.length,E=both?tradeEval(V,t.a,t.b,t.ga,t.gb):null;
  const col=(side,ps)=>`<div class="card"><div class="lbl">${side==="ga"?t.a:t.b} gives (tap to add)</div>${ps.map(p=>`<div class="row" data-tp="${side}|${esc(p.name)}" style="padding:7px 0;border-top:1px solid var(--line);cursor:pointer;${t[side].includes(p.name)?"background:#ff7a1a22;":""}"><span class="pill ${p.inj&&!["Active","Probable"].includes(p.inj)?"rd":"bl"}">${p.pos[0]||"-"}</span><span class="sp"><b>${esc(p.name)}</b><span class="sub"> ${p.team||""}${p.inj&&p.inj!=="Active"?" · "+esc(p.inj):""}${p.back?" · back ~"+p.back.slice(5):""}</span></span><span class="num">${p.ours}</span></div>`).join("")}</div>`;
  const fx=(n)=>`<span class="${n>=0?"pos":"neg"} num">${n>=0?"+":""}${Math.round(n)}</span>`;
  let res="";
  if(E){const cen=(ps)=>ps.filter(p=>p.pos.includes("C")).length;
    const verdict=E.da>0&&E.db>0?"Win-win: both lineups improve, so this is the kind of deal that actually gets accepted.":E.da>0&&E.db<=0?`Favours ${t.a}: ${t.b} loses ${Math.round(-E.db)} points, so ${t.b} probably says no unless they want the position or have injury worries.`:E.da<=0&&E.db>0?`Favours ${t.b}: ${t.a} loses ${Math.round(-E.da)} points.`:"Both lineups get worse. Don't.";
    const inj=[...E.gaP,...E.gbP].filter(p=>p.inj&&!["Active","Probable"].includes(p.inj)).map(p=>`${p.name} (${p.inj}${p.back?", back ~"+p.back:""})`);
    res=`<div class="card" style="border-color:${E.da>0&&E.db>0?"var(--gr)":"var(--or)"};margin:10px 0"><div class="lbl">Rest-of-season lineup points (playoff weeks count 1.5x)</div>
    <div class="grid g2" style="margin-top:6px"><div><b>${t.a}</b><div class="big" style="font-size:26px">${fx(E.da)}</div><div class="sub">${Math.round(E.a0)} → ${Math.round(E.a1)} · market ${E.mkA>=0?"+":""}${E.mkA}<br>centres ${cen(E.pa)} → ${cen(E.newA)}</div></div>
    <div><b>${t.b}</b><div class="big" style="font-size:26px">${fx(E.db)}</div><div class="sub">${Math.round(E.b0)} → ${Math.round(E.b1)} · market ${E.mkB>=0?"+":""}${E.mkB}<br>centres ${cen(E.pb)} → ${cen(E.newB)}</div></div></div>
    <div style="margin-top:8px"><b>${esc(verdict)}</b></div>${inj.length?`<div class="sub" style="margin-top:6px">Injured in this deal: ${inj.map(esc).join("; ")}. Return dates are estimates.</div>`:""}
    <div class="sub" style="margin-top:6px">Moving: ${esc(t.ga.join(" + "))} → ${t.b}, ${esc(t.gb.join(" + "))} → ${t.a}. This is the full model (best lineup each week, free rolls, injuries, return dates), not a simple sum.</div></div>`}
  const sug=t.sug?`<div class="card list" style="margin:8px 0">${t.sug.length?t.sug.map((x,i)=>`<div class="it" data-sg="${i}" style="display:block"><div class="row"><b>${esc(x.ga.join(" + "))}</b><span class="mut">for</span><b>${esc(x.gb.join(" + "))}</b></div><div class="sub">${t.a} <span class="${x.da>=0?"pos":"neg"}">${x.da>=0?"+":""}${Math.round(x.da)}</span> · ${t.b} <span class="${x.db>=0?"pos":"neg"}">${x.db>=0?"+":""}${Math.round(x.db)}</span> · tap to load${(t.mode==="a"?x.db:x.da)<-50?" · <b class=\"neg\">lopsided: they will almost certainly refuse</b>":""}</div></div>`).join(""):'<div class="sub" style="padding:8px">Nothing matches. Raise how much the other side may lose, or try a different pair.</div>'}</div>`:"";
  const owners=["All",...teams],rows=T?T.board.filter(b=>t.own==="All"||b.owner===t.own).sort((a,b)=>t.sort==="gap"?b.gap-a.gap:t.sort==="market"?b.market-a.market:b.ours-a.ours).slice(0,40):[];
  return `<h2>🤝 Trade Lab</h2><div class="sub">Pick any two managers, tap players from each side to put them in the deal, and see what it does to both lineups. ${esc(V.note)}</div>
  <div class="lbl" style="margin-top:12px">Manager A</div>${chips("tra",teams,t.a)}<div class="lbl">Manager B</div>${chips("trb",teams,t.b)}
  <div class="grid g2">${col("ga",pa)}${col("gb",pb)}</div>${res}
  <h3 style="margin-top:14px">Find a deal</h3>${chips("tmd",["Both win","Best for "+t.a,"Best for "+t.b],t.mode==="both"?"Both win":t.mode==="a"?"Best for "+t.a:"Best for "+t.b)}
  ${t.mode!=="both"?`<div class="sub">How many lineup points the other side is allowed to lose:</div>${chips("tlm",["0","25","50","100","any"],t.lim==="999"?"any":t.lim)}`:""}
  <div class="row" style="margin:10px 0"><button id="sug" class="chip on" style="border:0">Find deals</button><span class="sub">tries 1-for-1, 2-for-1 and 1-for-2 between ${t.a} and ${t.b}</span></div>${sug}
  ${T?`<h3 style="margin-top:20px">Win-win ideas for ${T.team}</h3><div class="card list">${T.ideas.map(i=>`<div class="it" style="display:block"><div class="row"><b>${esc(i.give.join(" + "))}</b><span class="mut">for</span><b>${esc(i.get.join(" + "))}</b></div><div class="sub">with ${i.with} · you <span class="pos">+${i.me}</span> · them <span class="pos">+${i.them}</span></div></div>`).join("")||'<div class="sub">None right now.</div>'}</div>
  <h3 style="margin-top:18px">Value board</h3><div class="sub">ours = points to season end above a free agent · market = Sleeper draft price on the same scale · gap = ours minus market (positive = underpriced)</div>${chips("tro",owners,t.own)}${chips("trs",["ours","market","gap"],t.sort)}
  <div class="card list">${rows.map(b=>`<div class="it"><span class="pill ${b.inj&&b.inj!=="Active"?"rd":"bl"}">${(b.pos||[])[0]||"-"}</span><div class="sp"><b>${esc(b.name)}</b><div class="sub">${b.owner} · ${b.team||""}${b.inj?" · "+esc(b.inj):""}</div></div><div style="text-align:right"><span class="num">${b.ours}</span><div class="sub">mkt ${b.market} · <span class="${b.gap>=0?"pos":"neg"}">${b.gap>=0?"+":""}${b.gap}</span></div></div></div>`).join("")}</div>`:""}`}
function suggest(V,A,B,mode,lim){const top=(o)=>V.players.filter(p=>p.owner===o&&!p.ir).sort((a,b)=>b.ours-a.ours).slice(0,9).map(p=>p.name),ta=top(A),tb=top(B),out=[],pairs=(arr,n)=>n===1?arr.map(x=>[x]):arr.flatMap((x,i)=>arr.slice(i+1).map(y=>[x,y])),L=+(lim||25);
  for(const [na,nb] of [[1,1],[2,1],[1,2]])for(const ga of pairs(ta,na))for(const gb of pairs(tb,nb)){const e=tradeEval(V,A,B,ga,gb);
    if(mode==="both"?(e.da>2&&e.db>2):mode==="a"?(e.da>5&&e.db>=-L):(e.db>5&&e.da>=-L))out.push({ga,gb,da:e.da,db:e.db})}
  const key=mode==="both"?(x,y)=>Math.min(y.da,y.db)-Math.min(x.da,x.db)||(y.da+y.db)-(x.da+x.db):mode==="a"?(x,y)=>y.da-x.da:(x,y)=>y.db-x.db;
  return out.sort(key).slice(0,8)}
/* LINEUP: what to start each day, free rolls included */
const SLOT_ORDER=["PG","SG","G","SF","PF","F","C","UTIL","UTIL"];
function lineup(){const P=D.P?.teams?.[ME];if(!P)return '<div class="card warn">Plan not built yet.</div>';
  const days=[...new Set(P.slots.flatMap(s=>s.chances.map(c=>c.date)))].sort();if(!days.length)return '<div class="card">No games left this week.</div>';
  if(!S.day||!days.includes(S.day))S.day=days.find(d=>d>=D.P.today)||days[0];
  const LK=lockedSet(),order=[...P.slots].sort((a,b)=>{const ia=SLOT_ORDER.indexOf(a.slot),ib=SLOT_ORDER.indexOf(b.slot);return ia-ib}),dn=d=>new Date(d+"T12:00:00").toLocaleDateString([],{weekday:"short",day:"numeric"});
  after.lineup=()=>{bindChips("dy",v=>{S.day=days.find(d=>dn(d)===v);route()});document.querySelectorAll("[data-lk]").forEach(e=>e.onclick=()=>toggleLock(e.dataset.lk));const b=document.getElementById("skb");if(b)b.onclick=()=>{const v=document.getElementById("sk").value.trim();if(v){setKey(v);toast("Key saved");route()}}};
  const rows=order.map(s=>{const c=s.chances.find(c=>c.date===S.day),lk=LK.has(s.player);
    if(lk)return `<div class="it" style="display:block"><div class="row"><span class="pill">${s.slot}</span><b>${esc(s.player)}</b><span class="sp"></span><span class="pill gr">locked ✓ leave him</span><span class="pill" data-lk="${esc(s.player)}" style="cursor:pointer">undo</span></div></div>`;
    if(!c)return `<div class="it" style="display:block"><div class="row"><span class="pill">${s.slot}</span><span class="mut">${esc(s.player)}: nobody to play today</span></div></div>`;
    const act=c.act==="LOCK"?'<span class="pill gr">LOCK NOW</span>':c.act==="HOLD"?'<span class="pill">scored, hold</span>':c.act==="FORCED"?'<span class="pill rd">final chance</span>':`<span class="pill or">lock if ≥ ${c.th}</span>`;
    return `<div class="it" style="display:block"><div class="row"><span class="pill">${s.slot}</span><b>${esc(c.player)}</b>${c.free?'<span class="pill bl">🎲 free roll</span>':""}<span class="sp"></span>${act}</div><div class="sub">${Math.round(c.plays*100)}% to play · expects ${c.exp}${c.free?` · swap in for ${esc(s.player)} before tip`:""}</div>${second(c)}<div class="row" style="margin-top:4px"><span class="sub sp">regular: ${esc(s.player)}</span><span class="pill" data-lk="${esc(c.player)}" style="cursor:pointer">I locked</span></div></div>`}).join("");
  const benchToday=P.bench.map(b=>b.player);
  return `<h2>📋 Your lineup</h2><div class="sub">The best 9 for each day, free rolls included. Set it in the Sleeper app before the first tip each day. Free roll = a bench player in a slot on a night your regular doesn't play (costs nothing while unlocked).</div>
  ${chips("dy",days.map(dn),dn(S.day))}<div class="card list">${rows}</div>
  <div class="sub" style="margin:8px 0">Bench: ${benchToday.map(esc).join(", ")||"–"}. Tap <b>I locked</b> after you lock someone. Sleeper can't tell us.</div>${keyCard()}`}

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
  ${reviewCard()}${formatLab()}${teamValue()}<h3 style="margin-top:20px">🔒 Lock Leaderboard</h3><div class="sub">The best, worst and costliest counted locks of the season.</div>${lockBoard()}
  <h3 style="margin-top:20px">🏅 Isaac's awards tally</h3><div class="card tw"><table><tr><th>Manager</th>${AW.map(k=>`<th>${k.replace("Biggest ","").replace("Shit vs Poo","S v P")}</th>`).join("")}</tr>${awRows}</table></div>`}

/* MOVES: matchup stance + free agents */
function moves(){const X=D.FA;if(!X)return '<div class="card warn">Not built yet.</div>';const m=X.matchup;
  return `<h2>🔁 Moves</h2>${m?`<div class="card"><div class="lbl">Your week ${X.week} vs ${esc(m.opp)}</div><div class="big" style="color:${m.p_win>=.5?"var(--gr)":"var(--rd)"}">${Math.round(m.p_win*100)}% to win</div>
  <div class="sub">Expected locked totals: you ${m.mine} · ${esc(m.opp)} ${m.theirs}</div><div style="margin-top:8px"><b>Lock stance:</b> ${esc(m.stance)}</div>
  <div class="sub" style="margin-top:6px">Sleeper's own box shows a closer game because it uses single-game projections. This number assumes both of you lock sensibly, so ${esc(m.opp)} (who barely uses locks) is probably weaker than shown. A heuristic on top of the model.</div></div>`:""}
  ${oppCard(m)}<h3 style="margin-top:18px">Free agents worth adding</h3><div class="sub">Best add/drop for your lineup. <b>Rest of season</b> and <b>this week</b> are the change in your best-lineup Lock-In points. Streamers show up in "this week".</div>
  <div class="card list">${X.fa.map(f=>`<div class="it" style="display:block"><div class="row"><b>Add ${esc(f.add)}</b><span class="pill">${(f.pos||[]).join("/")}</span><span class="sp"></span><span class="num pos">+${f.ros} ros</span></div><div class="sub">drop ${esc(f.drop)} · this week ${f.week>=0?"+":""}${f.week} · value ${f.value}</div></div>`).join("")||'<div class="sub">No pickup beats your current bench.</div>'}</div>
  <div class="sub" style="margin-top:8px">Waivers are rolling, so claims run in priority order. Check the player isn't hurt or on a back-to-back before claiming.</div>`}

function lockBoard(){const L=D.locks,top=(arr,f)=>arr.slice(0,10).map(l=>`<div class="row" style="padding:5px 0;border-top:1px solid var(--line)"><span class="pill">${l.slot}</span><span class="sp"><b>${esc(l.player)}</b> <span class="sub">${l.mgr} · wk${l.wk}</span></span><span class="num">${f(l)}</span></div>`).join("");
  const best=[...L].sort((a,b)=>b.locked-a.locked),worst=[...L].filter(l=>l.locked>0||l.best>0).sort((a,b)=>a.locked-b.locked),miss=[...L].sort((a,b)=>b.missed-a.missed);
  return `<div class="grid g2"><div class="card"><div class="lbl">Best counted scores</div>${top(best,l=>l.locked)}</div><div class="card"><div class="lbl">Worst counted scores</div>${top(worst,l=>l.locked)}</div></div>
  <div class="card" style="margin-top:12px"><div class="lbl">Biggest misses (best game minus the score taken)</div>${top(miss,l=>`−${f1(l.missed)} <span class="sub">(took ${l.locked}, best ${l.best})</span>`)}</div>`}

function reviewCard(){const R=D.RV;if(!R)return "";const L=R.league,rows=Object.entries(R.managers).sort((a,b)=>b[1].gain-a[1].gain);
  return `<h3 style="margin-top:20px">📝 Weekly review: you vs the lock engine</h3><div class="sub">Weeks ${R.weeks.join(", ")}. "Engine" is what the model would have scored on the same starters using only what was known at the time. Uses Sleeper's per-slot scores, so totals can differ slightly from the official ones. Rebuilt every Monday.</div>
  <div class="card tw"><table><tr><th>Manager</th><th>Actual</th><th>Engine</th><th>Gain</th><th>Never lock</th><th>Hindsight</th></tr>${rows.map(([n,x])=>`<tr><td><b>${n}</b></td><td class="num">${f1(x.actual)}</td><td class="num">${f1(x.engine)}</td><td class="num ${x.gain>=0?"pos":"neg"}">${x.gain>=0?"+":""}${f1(x.gain)}</td><td class="num">${f1(x.never_lock)}</td><td class="num">${f1(x.hindsight)}</td></tr>`).join("")}</table></div>
  ${L?`<div class="sub" style="margin-top:6px">League: managers ${f1(L.managers)} · engine ${f1(L.engine)} · never lock ${f1(L.never_lock)} · perfect hindsight ${f1(L.hindsight)}</div>`:""}
  <div class="card" style="margin-top:10px"><div class="lbl">Biggest engine-vs-manager differences</div>${R.misses.map(m=>`<div class="row" style="padding:5px 0;border-top:1px solid var(--line)"><span class="sp"><b>${esc(m.player)}</b> <span class="sub">${m.mgr} · wk${m.wk} · games ${m.games.join(", ")}</span></span><span class="num">took ${m.took} · engine ${m.engine}</span></div>`).join("")}</div>
  <div class="sub" style="margin-top:6px">${esc(R.refit||"")}</div>`}

function oppCard(m){const t=D.P?.teams?.[m?.opp];if(!t)return "";
  const lk=lockedSet();
  return `<h3 style="margin-top:18px">👀 ${esc(m.opp)}'s lineup</h3><div class="sub">What he can still score this week (expected value of each slot) and where he is in each. Use it to decide how hard to chase or protect.</div>
  <div class="card list">${t.slots.map(s=>{const c=s.chances[0],state=!c?"no games left":c.act==="LOCK"||c.act==="HOLD"?`scored ${c.exp}`:c.act==="FORCED"?"final chance":`next ${c.date.slice(5)}`;return `<div class="it"><span class="pill">${s.slot}</span><div class="sp"><b>${esc(s.player)}</b> <span class="sub">${state}</span></div><span class="num">${s.worth}</span></div>`}).join("")}</div>
  <div class="sub" style="margin:6px 0">He totals about ${t.total} to your ${D.P.teams[ME].total}. He rarely locks early (final-game slots), so his real total tends to land under this.</div>`}

function formatLab(){const FM=D.FM;if(!FM)return "";const W={};
  for(const [w,ms] of Object.entries(D.F.MU))for(const [a,pa,b,pb] of ms){const A=nm(a),B=nm(b),fa=FM[A+"|"+w],fb=FM[B+"|"+w];if(!fa||!fb)continue;
    for(const [k,x,y] of [["actual",pa,pb],["perfect",fa.perfect,fb.perfect],["daily",fa.daily,fb.daily]]){(W[A]??={actual:0,perfect:0,daily:0});(W[B]??={actual:0,perfect:0,daily:0});if(x>y)W[A][k]++;else if(y>x)W[B][k]++}}
  const rows=Object.entries(W).sort((a,b)=>b[1].actual-a[1].actual);
  return `<h3 style="margin-top:20px">🧪 Format Lab: same scoring, different league</h3><div class="sub">Wins so far if every matchup had been decided by: <b>Lock-In</b> (what happened), <b>Perfect Lock-In</b> (each player's best game, ideally slotted: pure roster quality) or <b>Daily lineups</b> (a normal set-your-lineup-each-day league).</div>
  <div class="card tw"><table><tr><th>Manager</th><th>Lock-In</th><th>Perfect</th><th>Daily</th></tr>${rows.map(([n,x])=>`<tr><td><b>${n}</b></td><td class="num">${x.actual}</td><td class="num">${x.perfect}</td><td class="num">${x.daily}</td></tr>`).join("")}</table></div>`}
function teamValue(){const S=D.SAL;if(!S||!D.players)return "";const fold=s=>s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[.']/g,"").trim(),by={};
  for(const p of D.players){const k=S[fold(p.player)];if(!k)continue;const sal=+k[1]/1e6;(by[p.owner]??={pay:0,pts:0,n:0,best:null});by[p.owner].pay+=sal;by[p.owner].pts+=p.avg;by[p.owner].n++;const v=p.avg/sal;if(!by[p.owner].best||v>by[p.owner].best.v)by[p.owner].best={n:p.player,v}}
  const rows=Object.entries(by).sort((a,b)=>b[1].pts/b[1].pay-a[1].pts/a[1].pay),mx=Math.max(...rows.map(r=>r[1].pts/r[1].pay));
  return `<h3 style="margin-top:20px">💰 Team value: fantasy points per real NBA salary</h3><div class="sub">Sum of each roster's per-game averages divided by their combined 2026-27 salary ($M). Higher = more fantasy output per dollar.</div>
  <div class="card">${rows.map(([n,x])=>`<div class="row" style="margin:6px 0"><b style="width:56px">${n}</b><div class="bar sp"><i style="width:${(x.pts/x.pay)/mx*100}%"></i></div><span class="num" style="width:150px;text-align:right">${(x.pts/x.pay).toFixed(2)} pts/$M · $${Math.round(x.pay)}M</span></div>`).join("")}</div>`}

function guide(){const md=t=>esc(t).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>").replace(/`(.+?)`/g,"<code>$1</code>");
  return `<h2>📖 How to use this</h2><div class="sub">Tap a section to open it.</div>${(D.GD||[]).map(s=>`<details class="card" style="margin-top:10px" ${s.o?"open":""}><summary style="cursor:pointer;font-weight:700">${esc(s.t)}</summary>${s.b.map(b=>`<p style="margin:8px 0 0">${md(b)}</p>`).join("")}</details>`).join("")}`}

/* second opinion: the original lockin.py rule next to the engine */
function second(c,short){if(!c||c.old==null||c.free)return "";
  if(c.act==="LOCK"||c.act==="HOLD"){const agree=(c.exp>=c.old)===(c.act==="LOCK");return `<div class="sub">2nd opinion (old rule): lock at ≥ ${c.old} → ${c.exp>=c.old?"lock":"hold"}${agree?" · agrees":" · <b style=\"color:var(--or)\">disagrees</b>"}</div>`}
  const diff=Math.abs(c.th-c.old);return `<div class="sub">2nd opinion (old rule): lock if ≥ ${c.old}${diff>4?` · <b style="color:var(--or)">⚠ differs by ${diff.toFixed(1)}</b>`:""}</div>`}
