// Дашборд проекта 5: CLV, сегменты и клиенты с максимальной ценностью.
document.addEventListener("DOMContentLoaded", async function () {
  const summary = await fetch("api/summary").then(r => r.json());
  document.getElementById("kpi-total").textContent = MiniChart.money(summary.total_clv);
  document.getElementById("kpi-avg").textContent = MiniChart.money(summary.avg_clv);
  document.getElementById("kpi-risk").textContent = MiniChart.money(summary.at_risk_clv);
  document.getElementById("kpi-retention").textContent = MiniChart.pct(summary.retention);

  const segments = await fetch("api/segments").then(r => r.json());
  MiniChart.bars(document.getElementById("segment-chart"), {
    series: [{ name: "CLV сегмента", color: "#feb622" }],
    groups: segments.map(s => ({ label: s.segment, values: [s.total_clv] }))
  });

  document.getElementById("segments").innerHTML = segments.map(s => `
    <tr>
      <td>${s.segment}</td>
      <td class="num">${s.customers.toLocaleString("ru-RU")}</td>
      <td class="num">${MiniChart.money(s.avg_clv)}</td>
      <td class="num">${MiniChart.pct(s.churn_rate)}</td>
      <td class="num">${MiniChart.pct(s.retention)}</td>
    </tr>`).join("");

  const customers = await fetch("api/customers?limit=10").then(r => r.json());
  document.getElementById("customers").innerHTML = customers.map(c => `
    <tr>
      <td>${c.user_id}</td>
      <td>${c.segment}</td>
      <td class="num">${c.orders_30d}</td>
      <td class="num">${c.days_since_order}</td>
      <td class="num">${MiniChart.pct(c.retention)}</td>
      <td class="num">${MiniChart.money(c.clv)}</td>
    </tr>`).join("");
});
