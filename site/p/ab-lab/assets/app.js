// Дашборд проекта 3: калькулятор дизайна и сравнение наивной/CUPED-оценок эффекта.
function renderDesign(d) {
  document.getElementById("design").innerHTML = `
    <tr><td>MDE в рублях</td><td class="num">${MiniChart.money(d.mde_abs)}</td></tr>
    <tr><td>Группа, пользователей</td><td class="num">${d.sample_per_arm.toLocaleString("ru-RU")}</td></tr>
    <tr><td>Всего трафика</td><td class="num">${d.total.toLocaleString("ru-RU")}</td></tr>
    <tr><td>Длительность</td><td class="num">${d.days} дн.</td></tr>
    <tr><td>Мощность / alpha</td><td class="num">${d.power} / ${d.alpha}</td></tr>`;
}

function renderResult(r) {
  const rows = [
    ["Welch (наивно)", r.naive],
    ["CUPED", r.cuped]
  ];
  document.getElementById("methods").innerHTML = rows.map(([name, row]) => `
    <tr>
      <td>${name}</td>
      <td class="num">${MiniChart.money(row.diff)}</td>
      <td class="num">${MiniChart.money(row.se)}</td>
      <td class="num">${row.p_value.toFixed(4)}</td>
    </tr>`).join("") + `
    <tr>
      <td>mSPRT (sequential)</td>
      <td class="num">${MiniChart.money(r.naive.diff)}</td>
      <td class="num">—</td>
      <td class="num">${r.naive.sequential_p.toFixed(4)}</td>
    </tr>`;

  document.getElementById("kpi-diff").textContent = MiniChart.money(r.cuped.diff);
  document.getElementById("kpi-p").textContent = r.naive.p_value.toFixed(4);
  document.getElementById("kpi-cuped").textContent = r.cuped.p_value.toFixed(4);
  document.getElementById("kpi-reduction").textContent = MiniChart.pct(r.reduction);
  document.getElementById("note").textContent =
    `Контроль: ${r.counts.control.toLocaleString("ru-RU")} чел., ${MiniChart.money(r.means.control)}; ` +
    `тест: ${r.counts.test.toLocaleString("ru-RU")} чел., ${MiniChart.money(r.means.test)}; theta = ${r.cuped.theta}.`;
}

async function calcDesign() {
  const mde = Number(document.getElementById("mde").value) / 100;
  const traffic = Number(document.getElementById("traffic").value);
  renderDesign(await fetch(`api/design?mde=${mde}&traffic=${traffic}`).then(r => r.json()));
}

document.addEventListener("DOMContentLoaded", async function () {
  document.getElementById("calc").addEventListener("click", calcDesign);
  calcDesign();
  renderResult(await fetch("api/result").then(r => r.json()));
});
