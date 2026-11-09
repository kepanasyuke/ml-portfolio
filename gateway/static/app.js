// Кабинет: сводка по моделям и промо-контуру, данные — из API разделов.
function badge(status) {
  const labels = { ok: "норма", warn: "внимание", bad: "алерт" };
  return `<span class="badge ${status}">${labels[status] || status}</span>`;
}

function renderCard(item) {
  return `
    <div class="card kpi ${item.status === "ok" ? "good" : "alert"}">
      <div class="label">${item.title}</div>
      <div class="value" style="font-size:22px">${item.value}</div>
      <p class="hint" style="margin:6px 0 0">${item.label}</p>
      <p class="muted" style="margin:8px 0 12px">${item.detail}</p>
      <div style="display:flex;justify-content:space-between;align-items:center">
        ${badge(item.status)}
        <a href="${item.href}">Открыть раздел →</a>
      </div>
    </div>`;
}

function render(data) {
  document.getElementById("kpi-sections").textContent = data.sections;
  document.getElementById("kpi-alerts").textContent = data.alerts;
  document.getElementById("kpi-state").textContent = data.alerts ? "есть сигналы" : "в норме";
  document.getElementById("kpi-time").textContent = data.generated_at;
  document.getElementById("cards").innerHTML = data.cards.map(renderCard).join("");
}

async function load(refresh) {
  const button = document.getElementById("refresh");
  button.disabled = true;
  button.textContent = refresh ? "Считаю…" : "Обновить сводку";
  try {
    const data = await fetch("api/overview" + (refresh ? "?refresh=true" : "")).then(r => r.json());
    render(data);
  } finally {
    button.disabled = false;
    button.textContent = "Обновить сводку";
  }
}

document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("refresh").addEventListener("click", function () { load(true); });
  load(false);
});
