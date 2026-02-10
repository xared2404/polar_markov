async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`Failed to load ${path}: ${r.status}`);
  return await r.json();
}

async function loadText(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`Failed to load ${path}: ${r.status}`);
  return await r.text();
}

function mean(arr) {
  if (!arr || arr.length === 0) return null;
  return arr.reduce((a,b)=>a+b, 0) / arr.length;
}

function topTransitions(P, states, k=12) {
  const pairs = [];
  for (let i=0;i<states.length;i++){
    for (let j=0;j<states.length;j++){
      pairs.push({p: P[i][j], from: states[i], to: states[j]});
    }
  }
  pairs.sort((a,b)=>b.p-a.p);
  return pairs.slice(0,k);
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function renderTransitions(tblId, transitions) {
  const tbody = document.querySelector(`#${tblId} tbody`);
  tbody.innerHTML = "";
  for (const t of transitions) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${t.from}</td><td>${t.to}</td><td>${t.p.toFixed(3)}</td>`;
    tbody.appendChild(tr);
  }
}

function renderPoleHeatmap(pole) {
  const img = document.getElementById("heatmapImg");
  img.src = `assets/heatmap_${pole}.png`;
}

function populateActorSelect(actorSel, stats, pole) {
  const filtered = stats.filter(x => x.pole === pole).sort((a,b)=>a.actor.localeCompare(b.actor));
  actorSel.innerHTML = "";
  for (const r of filtered) {
    const opt = document.createElement("option");
    opt.value = r.actor;
    opt.textContent = r.actor;
    actorSel.appendChild(opt);
  }
}

async function main() {
  const data = await loadJSON("data/markov_results.json");
  const report = await loadText("data/report.md");

  setText("klCL", data.divergence["KL_conservative||liberal"].toFixed(4));
  setText("klLC", data.divergence["KL_liberal||conservative"].toFixed(4));
  document.getElementById("reportBox").textContent = report;

  const viewMode = document.getElementById("viewMode");
  const poleSel = document.getElementById("poleSel");
  const actorSel = document.getElementById("actorSel");

  function updateUI() {
    const mode = viewMode.value;
    const pole = poleSel.value;

    if (mode === "pole") {
      actorSel.disabled = true;

      const poleObj = data[pole];
      const states = poleObj.states;
      const P = poleObj.P;

      setText("seqCount", poleObj.n_sequences ?? "–");
      setText("meanEntropy", mean(poleObj.entropy).toFixed(3));
      setText("meanLoop", mean(poleObj.loop_strength).toFixed(3));

      renderPoleHeatmap(pole);
      renderTransitions("transTable", topTransitions(P, states, 12));
      return;
    }

    actorSel.disabled = false;
    populateActorSelect(actorSel, data.actor_stats, pole);

    const actor = actorSel.value || actorSel.options?.[0]?.value;
    if (!actor) return;

    const row = data.actor_stats.find(x => x.pole === pole && x.actor === actor);
    setText("seqCount", row?.n_sequences ?? "–");
    setText("meanEntropy", (row?.mean_entropy ?? 0).toFixed(3));
    setText("meanLoop", (row?.mean_loop ?? 0).toFixed(3));

    renderPoleHeatmap(pole);

    const poleObj = data[pole];
    renderTransitions("transTable", topTransitions(poleObj.P, poleObj.states, 12));
  }

  viewMode.addEventListener("change", updateUI);
  poleSel.addEventListener("change", updateUI);
  actorSel.addEventListener("change", updateUI);

  updateUI();
}

main().catch(err => {
  console.error(err);
  document.getElementById("reportBox").textContent = `Error: ${err.message}`;
});
