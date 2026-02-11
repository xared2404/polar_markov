async function fetchText(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return await r.text();
}

async function fetchJson(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return await r.json();
}

function fmt(n, k=3) {
  if (typeof n !== "number" || !isFinite(n)) return "—";
  return n.toFixed(k);
}

function clamp01(x){ return Math.max(0, Math.min(1, x)); }

function cellColor(p) {
  // simple grayscale: higher prob = darker
  const v = clamp01(p);
  const shade = Math.round(255 - (v * 200)); // keep readable
  return `rgb(${shade},${shade},${shade})`;
}

function renderStats(el, meta) {
  const lines = [
    `<div><span class="k">Sequences</span><span class="v">${meta.n_sequences ?? 0}</span></div>`,
    `<div><span class="k">Mean entropy</span><span class="v">${fmt(meta.mean_entropy)}</span></div>`,
    `<div><span class="k">Mean loop</span><span class="v">${fmt(meta.mean_loop)}</span></div>`,
  ];
  el.innerHTML = lines.join("");
}

function computeMeans(obj) {
  const ent = Array.isArray(obj.entropy) ? obj.entropy : [];
  const loop = Array.isArray(obj.loop_strength) ? obj.loop_strength : [];
  const mean = (arr) => arr.length ? arr.reduce((a,b)=>a+b,0)/arr.length : NaN;
  return { mean_entropy: mean(ent), mean_loop: mean(loop) };
}

function renderMatrix(container, states, P) {
  container.innerHTML = "";

  if (!Array.isArray(states) || !Array.isArray(P) || !P.length) {
    container.innerHTML = `<p class="muted">No matrix data.</p>`;
    return;
  }

  const table = document.createElement("table");
  table.className = "matrix";

  // header row
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  const corner = document.createElement("th");
  corner.textContent = "from \\ to";
  hr.appendChild(corner);
  for (const s of states) {
    const th = document.createElement("th");
    th.textContent = s;
    hr.appendChild(th);
  }
  thead.appendChild(hr);
  table.appendChild(thead);

  // body
  const tbody = document.createElement("tbody");
  for (let i = 0; i < states.length; i++) {
    const tr = document.createElement("tr");
    const rowh = document.createElement("th");
    rowh.textContent = states[i];
    tr.appendChild(rowh);

    const row = P[i] || [];
    for (let j = 0; j < states.length; j++) {
      const p = Number(row[j] ?? 0);
      const td = document.createElement("td");
      td.textContent = fmt(p, 3);
      td.style.background = cellColor(p);
      td.title = `${states[i]} → ${states[j]}: ${fmt(p, 5)}`;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  container.appendChild(table);
}

function buildViewOptions(data) {
  const opts = [];
  // global poles
  for (const pole of ["conservative", "liberal"]) {
    if (data[pole]) opts.push({ kind: "pole", pole, label: pole.toUpperCase() });
  }
  return opts;
}

function buildActorOptions(data, pole) {
  const actors = data.actors || {};
  const out = [];
  for (const [name, payload] of Object.entries(actors)) {
    if (payload?.pole === pole) out.push({ name, label: name });
  }
  out.sort((a,b)=>a.label.localeCompare(b.label));
  return out;
}

function setSelectOptions(selectEl, options, placeholder=null) {
  selectEl.innerHTML = "";
  if (placeholder) {
    const o = document.createElement("option");
    o.value = "";
    o.textContent = placeholder;
    selectEl.appendChild(o);
  }
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt.value ?? opt.name ?? opt.pole;
    o.textContent = opt.label;
    selectEl.appendChild(o);
  }
}

async function main() {
  const viewSelect = document.getElementById("viewSelect");
  const actorSelect = document.getElementById("actorSelect");
  const statsEl = document.getElementById("stats");
  const matrixWrap = document.getElementById("matrixWrap");
  const reportEl = document.getElementById("report");

  const data = await fetchJson("./data/markov_results.json");
  const report = await fetchText("./data/report.md");
  reportEl.textContent = report;

  const views = buildViewOptions(data);
  setSelectOptions(viewSelect, views.map(v => ({ value: v.pole, label: v.label })));

  function renderPole(pole) {
    const payload = data[pole];
    if (!payload) return;

    const means = computeMeans(payload);
    renderStats(statsEl, {
      n_sequences: payload.n_sequences ?? 0,
      ...means
    });

    renderMatrix(matrixWrap, payload.states, payload.P);

    // populate actor select for this pole
    const actorOpts = buildActorOptions(data, pole);
    if (actorOpts.length) {
      actorSelect.disabled = false;
      setSelectOptions(actorSelect, actorOpts.map(a => ({ value: a.name, label: a.label })), "— show pole aggregate —");
    } else {
      actorSelect.disabled = true;
      setSelectOptions(actorSelect, [], "No actor matrices available");
    }
    actorSelect.value = "";
  }

  function renderActor(actorName) {
    const a = (data.actors || {})[actorName];
    if (!a) return;
    const means = computeMeans(a);
    renderStats(statsEl, {
      n_sequences: a.n_sequences ?? 0,
      ...means
    });
    renderMatrix(matrixWrap, a.states, a.P);
  }

  // init default
  const defaultPole = views[0]?.pole || "conservative";
  viewSelect.value = defaultPole;
  renderPole(defaultPole);

  viewSelect.addEventListener("change", () => {
    renderPole(viewSelect.value);
  });

  actorSelect.addEventListener("change", () => {
    const pole = viewSelect.value;
    const actor = actorSelect.value;
    if (!actor) {
      renderPole(pole);
    } else {
      renderActor(actor);
    }
  });
}

main().catch(err => {
  console.error(err);
  const m = document.getElementById("matrixWrap");
  if (m) m.innerHTML = `<p class="muted">Failed to load data: ${String(err)}</p>`;
});
