// Дашборд проекта 6: PSI/KS по признакам, алерты и дрейф скорингов.
function badge(status) {
  const label = status === "ok" ? "норма" : (status === "warn" ? "внимание" : "алерт");
  return `<span class="badge ${status}">${label}</span>`;
}

function render(data, summary) {
  document.getElementById("kpi-max").textContent = summary.max_psi.toFixed(3);
  document.getElementById("kpi-alerts").textContent = summary.flagged;
  document.getElementById("kpi-scores").textContent = data.scores.psi.toFixed(3);
  document.getElementById("kpi-batches").textContent =
    summary.reference.toLocaleString("ru-RU") + " / " + summary.current.toLocaleString("ru-RU");

  const features = data.features;
  MiniChart.bars(document.getElementById("psi-chart"), {
    series: [{ name: "PSI", color: "#ff5858" }],
    groups: features.map(row => ({ label: row.feature, values: [row.psi] }))
  });

  const alerts = data.alerts.length ? data.alerts : [];
  document.getElementById("alerts").innerHTML = alerts.length
    ? alerts.map(row => `<tr><td>${row.feature}</td><td class="num">${row.psi}</td>
        <td class="num">${row.ks}</td><td>${badge(row.status)}</td></tr>`).join("")
    : '<tr><td colspan="4" class="muted">Дрейф в пределах нормы.</td></tr>';

  document.getElementById("features").innerHTML = features.map(row => `
    <tr>
      <td>${row.feature}</td>
      <td class="num">${row.psi}</td>
      <td class="num">${row.ks}</td>
      <td class="num">${row.ref_mean}</td>
      <td class="num">${row.cur_mean}</td>
      <td>${badge(row.status)}</td>
    </tr>`).join("");
}

async function recalc() {
  const factor = Number(document.getElementById("factor").value);
  document.getElementById("factor-value").textContent = "×" + factor.toFixed(1);
  const [data, summary] = await Promise.all([
    fetch(`api/drift?factor=${factor}`).then(r => r.json()),
    fetch(`api/summary?factor=${factor}`).then(r => r.json())
  ]);
  render(data, summary);
}

document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("recalc").addEventListener("click", recalc);
  document.getElementById("factor").addEventListener("input", recalc);
  recalc();
});
