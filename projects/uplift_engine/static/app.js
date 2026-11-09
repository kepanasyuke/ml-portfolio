// Дашборд проекта 1: метрики uplift-модели, кривые Qini и рекомендации по промокодам.
document.addEventListener("DOMContentLoaded", async function () {
  const summary = await fetch("api/summary").then(r => r.json());
  document.getElementById("kpi-auuc").textContent = summary.metrics.two_model.auuc.toFixed(2);
  document.getElementById("kpi-auuc2").textContent = summary.metrics.transformed.auuc.toFixed(2);
  document.getElementById("kpi-uplift").textContent = MiniChart.pct(summary.metrics.two_model.uplift_at_10);
  document.getElementById("kpi-holdout").textContent = summary.holdout_size.toLocaleString("ru-RU");

  const curves = await fetch("api/qini").then(r => r.json());
  const series = [
    { name: "Two-model", color: "#feb622", points: curves.two_model.share.map((x, i) => ({ x: x, y: curves.two_model.qini[i] })) },
    { name: "Transformed outcome", color: "#3b5803", points: curves.transformed.share.map((x, i) => ({ x: x, y: curves.transformed.qini[i] })) },
    { name: "Случайное ранжирование", color: "#c9c4ba", points: [{ x: 0, y: 0 }, { x: 1, y: 0 }] }
  ];
  MiniChart.line(document.getElementById("qini-chart"), { series: series, labels: ["0%", "25%", "50%", "75%", "100%"] });
  MiniChart.legend(document.getElementById("qini-legend"), series.map(s => ({ name: s.name, color: s.color })));

  const segments = await fetch("api/segments").then(r => r.json());
  MiniChart.bars(document.getElementById("segments-chart"), {
    series: [{ name: "Uplift", color: "#ff5858" }],
    groups: segments.map(s => ({ label: s.segment, values: [s.uplift] }))
  });

  const reco = await fetch("api/recommendations?limit=10").then(r => r.json());
  document.getElementById("reco").innerHTML = reco.map(row => `
    <tr>
      <td>${row.user_id}</td>
      <td>${row.segment}</td>
      <td>${row.city}</td>
      <td class="num">${row.promo_value}</td>
      <td class="num">${MiniChart.pct(row.uplift)}</td>
      <td class="num">${MiniChart.money(row.expected_margin)}</td>
    </tr>`).join("");
});
