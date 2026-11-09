// Дашборд проекта 2: пересчёт плана распределения промокодов под ограничения.
function runPlan() {
  const budget = Number(document.getElementById("budget").value);
  const cpo = Number(document.getElementById("cpo").value);
  document.getElementById("run").disabled = true;
  return fetch("api/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ budget: budget, cpo_cap: cpo })
  }).then(r => r.json()).then(render).finally(() => {
    document.getElementById("run").disabled = false;
  });
}

function render(data) {
  const plan = data.plan;
  document.getElementById("kpi-cm2").textContent = MiniChart.money(plan.incremental_cm2);
  document.getElementById("kpi-cpo").textContent = MiniChart.money(plan.cpo);
  document.getElementById("kpi-users").textContent = plan.users.toLocaleString("ru-RU");
  document.getElementById("kpi-roi").textContent = "×" + plan.roi.toFixed(2);

  const rows = [["Оптимизатор", plan], ["Всем по 300 ₽", data.blanket]];
  document.getElementById("compare").innerHTML = rows.map(([name, row]) => `
    <tr>
      <td>${name}</td>
      <td class="num">${row.users.toLocaleString("ru-RU")}</td>
      <td class="num">${MiniChart.money(row.spend)}</td>
      <td class="num">${row.incremental_orders.toFixed(0)}</td>
      <td class="num">${MiniChart.money(row.incremental_gmv)}</td>
      <td class="num">${MiniChart.money(row.incremental_cm2)}</td>
      <td class="num">${MiniChart.money(row.cpo)}</td>
      <td class="num">${row.roi.toFixed(2)}</td>
    </tr>`).join("");

  MiniChart.bars(document.getElementById("compare-chart"), {
    series: [
      { name: "CM2 оптимизатора", color: "#feb622" },
      { name: "CM2 «всем по 300»", color: "#c9c4ba" }
    ],
    groups: [{ label: "Инкрементальная CM2", values: [plan.incremental_cm2, data.blanket.incremental_cm2] },
             { label: "Инкрементальный GMV", values: [plan.incremental_gmv, data.blanket.incremental_gmv] }]
  });
  MiniChart.legend(document.getElementById("compare-legend"), [
    { name: "Оптимизатор", color: "#feb622" },
    { name: "Всем по 300 ₽", color: "#c9c4ba" }
  ]);

  document.getElementById("mix").innerHTML = data.by_promo.map(row => `
    <tr><td class="num">${row.promo}</td><td class="num">${row.users}</td>
    <td class="num">${MiniChart.money(row.spend)}</td><td class="num">${MiniChart.money(row.incremental_cm2)}</td></tr>`).join("");

  document.getElementById("top").innerHTML = data.top.map(row => `
    <tr><td>${row.user_id}</td><td>${row.segment}</td><td class="num">${row.promo}</td>
    <td class="num">${MiniChart.pct(row.tau)}</td><td class="num">${MiniChart.money(row.exp_cm2)}</td></tr>`).join("");
}

document.addEventListener("DOMContentLoaded", async function () {
  const limits = await fetch("api/limits").then(r => r.json());
  document.getElementById("budget").value = limits.budget;
  document.getElementById("cpo").value = limits.cpo_cap;
  document.getElementById("limits").textContent =
    `${limits.users.toLocaleString("ru-RU")} клиентов, ${limits.candidates.toLocaleString("ru-RU")} вариантов «клиент × номинал»`;
  document.getElementById("run").addEventListener("click", runPlan);
  runPlan();
});
