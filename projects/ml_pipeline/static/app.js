// Дашборд проекта 4: визуализация стадий пайплайна, хешей и объектов бакета.
function renderStages(payload) {
  const stages = payload.stages || [];
  document.getElementById("bucket").textContent = payload.bucket ? "Бакет: " + payload.bucket : "";
  if (!stages.length) {
    document.getElementById("stages").innerHTML =
      '<p class="muted">Пайплайн ещё не запускался. Нажмите «Запустить пайплайн».</p>';
    return;
  }
  document.getElementById("stages").innerHTML = stages.map(stage => `
    <div class="card">
      <div class="status">
        <span class="dot ${stage.status === "cached" ? "warn" : ""}"></span>
        ${stage.name}
      </div>
      <p class="muted" style="margin:8px 0 4px">hash ${stage.hash}</p>
      <p class="muted" style="margin:0">${stage.status === "cached" ? "из кэша" : stage.duration + " c"}</p>
      ${stage.result && Object.keys(stage.result).length
        ? `<pre class="code" style="margin-top:10px">${JSON.stringify(stage.result, null, 2)}</pre>` : ""}
    </div>`).join("");
}

function renderMetrics(metrics) {
  const entries = Object.entries(metrics || {});
  document.getElementById("metrics").innerHTML = entries.length
    ? entries.map(([key, value]) => `<tr><td>${key}</td><td class="num">${value}</td></tr>`).join("")
    : '<tr><td colspan="2" class="muted">Нет метрик: запустите пайплайн.</td></tr>';
}

function renderArtifacts(artifacts) {
  document.getElementById("artifacts").innerHTML = artifacts.length
    ? artifacts.map(item => `<tr><td>${item.key}</td><td class="num">${(item.bytes / 1024).toFixed(1)} КБ</td></tr>`).join("")
    : '<tr><td colspan="2" class="muted">Бакет пуст.</td></tr>';
}

async function refresh(payload) {
  renderStages(payload);
  renderMetrics(payload.metrics);
  const state = await fetch("api/state").then(r => r.json());
  renderArtifacts(state.artifacts || []);
  if (!payload.metrics && state.stages && state.stages.length) {
    const evaluated = state.stages.find(s => s.name === "evaluate");
    renderMetrics(evaluated ? evaluated.result : {});
  }
}

async function run() {
  const force = document.getElementById("force").checked;
  document.getElementById("run").disabled = true;
  try {
    const result = await fetch("api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force: force })
    }).then(r => r.json());
    await refresh(result);
  } finally {
    document.getElementById("run").disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async function () {
  document.getElementById("run").addEventListener("click", run);
  await refresh(await fetch("api/state").then(r => r.json()));
});
