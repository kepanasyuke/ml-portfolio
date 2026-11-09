// Дашборд проекта 7: готовые SQL-запросы, редактор и таблица результата.
function renderResult(payload) {
  document.getElementById("error").textContent = payload.error || "";
  document.getElementById("meta").textContent = payload.error
    ? ""
    : `${payload.count} строк · ${payload.ms} мс`;
  document.getElementById("head").innerHTML = payload.columns.length
    ? "<tr>" + payload.columns.map(c => `<th>${c}</th>`).join("") + "</tr>"
    : "";
  document.getElementById("body").innerHTML = (payload.rows || []).map(row =>
    "<tr>" + row.map(cell => `<td class="num">${cell === null ? "—" : cell}</td>`).join("") + "</tr>"
  ).join("");
}

async function runSql() {
  document.getElementById("run").disabled = true;
  try {
    const payload = await fetch("api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql: document.getElementById("sql").value })
    }).then(r => r.json());
    renderResult(payload);
  } finally {
    document.getElementById("run").disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async function () {
  const meta = await fetch("api/queries").then(r => r.json());
  document.getElementById("presets").innerHTML = meta.presets.map((preset, index) =>
    `<button class="ghost" data-index="${index}">${preset.name}</button>`).join("");
  document.getElementById("schema").innerHTML = meta.schema
    .map(row => `<tr><td>${row.name}</td><td class="num">${row.type}</td></tr>`).join("");

  document.querySelectorAll("#presets button").forEach(button => {
    button.addEventListener("click", function () {
      const preset = meta.presets[Number(button.dataset.index)];
      document.getElementById("sql").value = preset.sql;
      runSql();
    });
  });

  document.getElementById("run").addEventListener("click", runSql);
  runSql();
});
