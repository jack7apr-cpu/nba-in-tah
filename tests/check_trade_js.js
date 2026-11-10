const fs=require("fs");const src=fs.readFileSync("site/app.js","utf8");
const a=src.indexOf("const TSLOTS"),b=src.indexOf("function trades()");
eval(src.slice(a,b).replace(/^const /gm,"var ").replace(/function (\w+)/g,"var $1=function $1"));
const V=JSON.parse(fs.readFileSync("site/data/values.json"));
const jack=V.players.filter(p=>p.owner==="Jack");
console.log("JS Jack total",lineupValue(jack,V).t.toFixed(2));
