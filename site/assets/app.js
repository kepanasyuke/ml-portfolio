// Кабинет: сводка по моделям и промо-контуру, данные — из API разделов.
const ICONS = {
  "uplift-engine": "i-uplift",
  "promo-optimizer": "i-promo",
  "ab-lab": "i-ab",
  "ml-pipeline": "i-pipeline",
  "churn-clv": "i-clv",
  "ml-monitor": "i-monitor",
  "sql-lab": "i-sql",
};

function badge(status) {
  const labels = { ok: "норма", warn: "внимание", bad: "алерт" };
  return `<span class="badge ${status}">${labels[status] || status}</span>`;
}

function glyph(slug) {
  return `<svg class="icon" aria-hidden="true"><use href="#${ICONS[slug] || "i-cabinet"}"></use></svg>`;
}

function renderCard(item) {
  return `
    <div class="card project ${item.status === "ok" ? "good" : "alert"}">
      <div class="card-head">
        <span class="card-glyph">${glyph(item.slug)}</span>
        <div>
          <div class="label">${item.title}</div>
          <div class="value">${item.value}</div>
        </div>
      </div>
      <p class="hint">${item.label}</p>
      <p class="muted" style="margin:0 0 12px">${item.detail}</p>
      <div class="card-foot">
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
