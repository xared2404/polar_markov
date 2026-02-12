const CANDIDATE_DATA_URLS = [
  "./data/markov_results.json",
  "data/markov_results.json",
  "./docs/data/markov_results.json",
];

const CANDIDATE_REPORT_URLS = [
  "./data/report.md",
  "data/report.md",
  "./docs/data/report.md",
];

const poleSelect = document.getElementById("poleSelect");
const actorSelect = document.getElementById("actorSelect");
const viewSelect = document.getElementById("viewSelect");
const out = document.getElementById("out");
const reportEl = document.getElementById("report");
const statusEl = document.getElementById("status");
const refreshBtn = document.getElementById("refreshBtn");

const debugEl = document.getElementById("debug");

let DATA = null;

function logDebug(msg){
  if (!debugEl) return;
  debugEl.textContent += `\n${msg}`;
}

function esc(s){
  return String(s ?? "").replace(/[&<>"']/g, (c)=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

function fmt(n){
  if (typeof n !== "number" || !isFinite(n)) return "—";
  return (Math.round(n * 1000) / 1000).toFixed(3);
}

function setStatus(msg){
  statusEl.textContent = msg || "";
}

async function tryFetch(url){
  const r = await fetch(url, { cache: "no-store" });
  return r;
}

async function fetchFirstOk(urls, kind){
  for (const u of urls){
    try{
      const r = await tryFetch(u);
      logDebug(`${kind} try: ${u} -> ${r.status}`);
      if (r.ok) return { url: u, resp: r };
    }catch(e){
      logDebug(`${kind} try: ${u} -> ERROR ${e.message}`);
    }
  }
  throw new Error(`${kind} fetch failed for all candidate urls`);
}

async function loadJson(){
  const { url, resp } = await fetchFirstOk(CANDIDATE_DATA_URLS, "json");
  const text = await resp.text();
  logDebug(`json ok from: ${url} bytes=${text.length}`);
  return JSON.parse(text);
}

async function loadReport(){
  const { url, resp } = await fetchFirstOk(CANDIDATE_REPORT_URLS, "report");
  const text = await resp.text();
  logDebug(`report ok from: ${url} bytes=${text.length}`);
  return text;
}

function poleOptions(){
  const opts = [];
  if (DATA?.conservative) opts.push({value:"conservative", label:"conservative"});
  if (DATA?.liberal) opts.push({value:"liberal", label:"liberal"});
  return opts;
}

function fillSelect(sel, options, value){
  sel.innerHTML = "";
  for (const o of options){
    const opt = document.createElement("option");
    opt.value = o.value;
    opt.textContent = o.label ?? o.value;
    sel.appendChild(opt);
  }
  if (value && options.some(o => o.value === value)) sel.value = value;
}

function getPoleActors(data, pole){
  const stats = (data.actor_stats || []).filter(x => x.pole === pole);
  const seen = new Set();
  const out = [];
  for (const s of stats){
    if (!seen.has(s.actor)){
      seen.add(s.actor);
      out.push(s.actor);
    }
  }
  out.sort((a,b)=>a.localeCompare(b));
  return out;
}

function findActorMatrix(data, pole, actor){
  const actors = data.actors || {};
  for (const key of Object.keys(actors)){
    const obj = actors[key];
    if (obj?.pole === pole && obj?.actor === actor) return obj;
  }
  return null;
}

function topTransitions(P, states, k=12){
  const items = [];
  for (let i=0;i<P.length;i++){
    for (let j=0;j<P[i].length;j++){
      items.push({ p:P[i][j], a:states[i], b:states[j] });
    }
  }
  items.sort((x,y)=>y.p-x.p);
  return items.slice(0, k);
}

function renderSummary(pole, actor){
  const poleBlock = DATA[pole] || {};
  const states = poleBlock.states || [];
  const nSeq = poleBlock.n_sequences ?? 0;

  const actorStats = (DATA.actor_stats || []).find(x => x.pole===pole && x.actor===actor);

  const div = document.createElement("div");

  const rows = [
    ["Pole", pole],
    ["Pole sequences", nSeq],
    ["States", states.join(", ") || "(none)"],
    ["Actor", actor || "(none)"],
  ];

  if (actorStats){
    rows.push(["Actor sequences", actorStats.n_sequences]);
    rows.push(["Actor mean entropy", fmt(actorStats.mean_entropy)]);
    rows.push(["Actor mean loop", fmt(actorStats.mean_loop)]);
  } else {
    rows.push(["Actor stats", "Not enough sequences yet (or not saved)"]);
    rows.push(["actors_min_seqs", DATA.actors_min_seqs ?? "?" ]);
    rows.push(["actors_saved", Object.keys(DATA.actors || {}).length ]);
  }

  for (const [k,v] of rows){
    const kv = document.createElement("div");
    kv.className = "kv";
    kv.innerHTML = `<div class="k">${esc(k)}</div><div class="v">${esc(v)}</div>`;
    div.appendChild(kv);
  }
  return div;
}

function renderMatrix(pole, actor){
  const obj = findActorMatrix(DATA, pole, actor);
  if (!obj){
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No saved actor matrix for this actor yet.";
    return p;
  }
  const states = obj.states || [];
  const P = obj.P || [];

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  trh.appendChild(Object.assign(document.createElement("th"), { textContent: "from \\ to" }));
  for (const s of states) trh.appendChild(Object.assign(document.createElement("th"), { textContent: s }));
  thead.appendChild(trh);
  table.appendChild(thead);

  const tb = document.createElement("tbody");
  for (let i=0;i<P.length;i++){
    const tr = document.createElement("tr");
    tr.appendChild(Object.assign(document.createElement("td"), { textContent: states[i] ?? `S${i}` }));
    for (let j=0;j<P[i].length;j++){
      const td = document.createElement("td");
      td.textContent = fmt(P[i][j]);
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  table.appendChild(tb);
  return table;
}

function renderTop(pole, actor){
  const obj = findActorMatrix(DATA, pole, actor);
  if (!obj){
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No saved actor matrix for this actor yet.";
    return p;
  }
  const states = obj.states || [];
  const P = obj.P || [];
  const items = topTransitions(P, states, 12);
  const ul = document.createElement("ul");
  for (const it of items){
    const li = document.createElement("li");
    li.textContent = `${it.a} → ${it.b}: ${fmt(it.p)}`;
    ul.appendChild(li);
  }
  return ul;
}

function render(){
  if (!DATA) return;
  const pole = poleSelect.value;
  const actor = actorSelect.value;
  const view = viewSelect.value;

  out.innerHTML = "";
  if (view === "summary") out.appendChild(renderSummary(pole, actor));
  if (view === "matrix") out.appendChild(renderMatrix(pole, actor));
  if (view === "top") out.appendChild(renderTop(pole, actor));
}

function wire(){
  poleSelect.addEventListener("change", ()=>{
    const pole = poleSelect.value;
    const actors = getPoleActors(DATA, pole);
    fillSelect(actorSelect, actors.map(a=>({value:a,label:a})), actors[0] || "");
    render();
  });
  actorSelect.addEventListener("change", render);
  viewSelect.addEventListener("change", render);

  refreshBtn.addEventListener("click", init);
}

async function init(){
  try{
    debugEl.textContent = "boot…";
    setStatus("Loading…");

    DATA = await loadJson();
    logDebug(`json keys: ${Object.keys(DATA).join(", ")}`);

    fillSelect(poleSelect, poleOptions(), "conservative");

    const actors = getPoleActors(DATA, poleSelect.value);
    logDebug(`actors for ${poleSelect.value}: ${actors.length}`);
    fillSelect(actorSelect, actors.map(a=>({value:a,label:a})), actors[0] || "");

    const rep = await loadReport();
    reportEl.textContent = rep;

    wire();
    render();

    setStatus(`OK · seqs C=${DATA?.conservative?.n_sequences ?? 0} L=${DATA?.liberal?.n_sequences ?? 0} · actors_saved=${Object.keys(DATA?.actors || {}).length} · min=${DATA?.actors_min_seqs ?? "?"}`);
  }catch(e){
    console.error(e);
    logDebug(`FATAL: ${e.message}`);
    setStatus(`Error: ${e.message}`);
    out.innerHTML = `<p class="muted">Failed to load. See Debug box above.</p>`;
  }
}

init();
