const DATA_URL = "./data/markov_results.json";
const REPORT_URL = "./data/report.md";

const poleSelect = document.getElementById("poleSelect");
const actorSelect = document.getElementById("actorSelect");
const viewSelect = document.getElementById("viewSelect");
const out = document.getElementById("out");
const reportEl = document.getElementById("report");
const statusEl = document.getElementById("status");
const refreshBtn = document.getElementById("refreshBtn");

let DATA = null;

function esc(s){
  return String(s ?? "").replace(/[&<>"']/g, (c)=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

function fmt(n){
  if (typeof n !== "number") return String(n);
  return (Math.round(n * 1000) / 1000).toFixed(3);
}

function setStatus(msg){
  statusEl.textContent = msg || "";
}

async function fetchText(url){
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`Fetch failed ${r.status} for ${url}`);
  return await r.text();
}

async function fetchJson(url){
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`Fetch failed ${r.status} for ${url}`);
  return await r.json();
}

function getPoleActors(data, pole){
  // actor matrices are saved in data.actors[ACTOR_KEY], where actor includes pole in metadata
  // but we also have actor_stats listing per actor.
  const stats = (data.actor_stats || []).filter(x => x.pole === pole);
  const uniq = [];
  const seen = new Set();
  for (const s of stats){
    const name = s.actor;
    if (!seen.has(name)){
      seen.add(name);
      uniq.push(name);
    }
  }
  return uniq;
}

function poleOptions(){
  return [
    { value:"conservative", label:"conservative" },
    { value:"liberal", label:"liberal" }
  ];
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

function renderSummary(data, pole, actor){
  const poleBlock = data[pole] || {};
  const states = poleBlock.states || [];
  const nSeq = poleBlock.n_sequences ?? 0;

  const actorStats = (data.actor_stats || []).find(x => x.pole===pole && x.actor===actor);

  const div = document.createElement("div");

  const rows = [
    ["Pole sequences (total)", nSeq],
    ["States", states.join(", ") || "(none)"],
  ];

  if (actorStats){
    rows.push(["Actor sequences", actorStats.n_sequences]);
    rows.push(["Actor mean entropy", fmt(actorStats.mean_entropy)]);
    rows.push(["Actor mean loop", fmt(actorStats.mean_loop)]);
  }else{
    rows.push(["Actor stats", "Not enough sequences yet (or not saved)"]);
    rows.push(["Hint", `Increase docs per actor or lower actors_min_seqs (current: ${data.actors_min_seqs ?? "?"})`]);
  }

  for (const [k,v] of rows){
    const kv = document.createElement("div");
    kv.className = "kv";
    kv.innerHTML = `<div class="k">${esc(k)}</div><div class="v">${esc(v)}</div>`;
    div.appendChild(kv);
  }
  return div;
}

function findActorMatrix(data, pole, actor){
  // data.actors is keyed by safe strings; we search by metadata inside value
  const actors = data.actors || {};
  for (const key of Object.keys(actors)){
    const obj = actors[key];
    if (!obj) continue;
    if (obj.pole === pole && obj.actor === actor) return obj;
  }
  return null;
}

function renderMatrix(data, pole, actor){
  const obj = findActorMatrix(data, pole, actor);
  if (!obj){
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No saved actor matrix for this actor yet (min_seqs threshold or missing).";
    return p;
  }
  const states = obj.states || [];
  const P = obj.P || [];

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  trh.appendChild(Object.assign(document.createElement("th"), { textContent: "from \\ to" }));
  for (const s of states){
    trh.appendChild(Object.assign(document.createElement("th"), { textContent: s }));
  }
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

function renderTop(data, pole, actor){
  const obj = findActorMatrix(data, pole, actor);
  if (!obj){
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No saved actor matrix for this actor yet (min_seqs threshold or missing).";
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
  if (view === "summary") out.appendChild(renderSummary(DATA, pole, actor));
  if (view === "matrix") out.appendChild(renderMatrix(DATA, pole, actor));
  if (view === "top") out.appendChild(renderTop(DATA, pole, actor));
}

function wire(){
  poleSelect.addEventListener("change", ()=>{
    const pole = poleSelect.value;
    const actors = getPoleActors(DATA, pole);
    fillSelect(actorSelect, actors.map(a=>({value:a,label:a})), actors[0]);
    render();
  });
  actorSelect.addEventListener("change", render);
  viewSelect.addEventListener("change", render);
  refreshBtn.addEventListener("click", init);
}

async function init(){
  try{
    setStatus("Loading…");
    DATA = await fetchJson(DATA_URL);

    // fill pole select
    fillSelect(poleSelect, poleOptions(), "conservative");

    // fill actor list for default pole
    const actors = getPoleActors(DATA, poleSelect.value);
    fillSelect(actorSelect, actors.map(a=>({value:a,label:a})), actors[0]);

    // load report
    const rep = await fetchText(REPORT_URL);
    reportEl.textContent = rep;

    wire();
    render();
    setStatus(`OK · seqs: C=${DATA?.conservative?.n_sequences ?? 0} L=${DATA?.liberal?.n_sequences ?? 0} · actors_saved=${Object.keys(DATA?.actors || {}).length} · min=${DATA?.actors_min_seqs ?? "?"}`);
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`);
    out.innerHTML = `<p class="muted">Failed to load data. Check that docs/data/markov_results.json exists and Pages deployed.</p>`;
  }
}

init();
