const byId = (id) => document.getElementById(id);
const format = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 });
const compact = new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 1 });
const names = { baseline: "Estacional", challenger: "Candidato" };

function tableBody(id, rows) {
  const body = byId(id);
  body.replaceChildren();
  for (const values of rows) {
    const row = body.insertRow();
    for (const value of values) row.insertCell().textContent = value;
  }
}

function drawChart(rows, selected = -1) {
  const canvas = byId("chart");
  const { width, height } = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const left = 52;
  const right = width - 14;
  const top = 12;
  const bottom = height - 33;
  const max = Math.max(1, ...rows.flatMap((row) => row.slice(2)));
  const unit = 10 ** Math.floor(Math.log10(max / 4));
  const step = [1, 2, 2.5, 3, 4, 5, 6, 8, 10].find((value) => value * unit >= max / 4) * unit;
  const ceiling = 4 * step;
  const x = (index) => left + index * (right - left) / Math.max(rows.length - 1, 1);
  const y = (value) => bottom - value / ceiling * (bottom - top);
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#b4bdb1";
  for (let tick = 0; tick <= 4; tick++) {
    const value = ceiling * tick / 4;
    const position = y(value);
    ctx.strokeStyle = "#383f36";
    ctx.beginPath();
    ctx.moveTo(left, position);
    ctx.lineTo(right, position);
    ctx.stroke();
    ctx.fillText(compact.format(value), 1, position + 4);
  }
  const ticks = width < 500 ? 3 : 5;
  for (let tick = 0; tick < ticks; tick++) {
    const index = Math.round(tick * (rows.length - 1) / (ticks - 1));
    ctx.textAlign = tick === 0 ? "left" : tick === ticks - 1 ? "right" : "center";
    ctx.fillText(monthLabel(rows[index][0], false), x(index), bottom + 20);
  }
  if (selected >= 0) {
    ctx.strokeStyle = "#788573";
    ctx.beginPath();
    ctx.moveTo(x(selected), top);
    ctx.lineTo(x(selected), bottom);
    ctx.stroke();
  }
  const series = [[3, "#f0bd8d", [6, 4]], [4, "#b8b5e6", [2, 4]], [2, "#c9edac", []]];
  for (const [column, color, dash] of series) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = column === 2 ? 2.6 : 1.7;
    ctx.setLineDash(dash);
    rows.forEach((row, index) => {
      if (index === 0) ctx.moveTo(x(index), y(row[column]));
      else ctx.lineTo(x(index), y(row[column]));
    });
    ctx.stroke();
    if (selected >= 0) {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x(selected), y(rows[selected][column]), 3.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  return { left, right, x };
}

const shortMonth = new Intl.DateTimeFormat("es-PE", { month: "short", timeZone: "UTC" });
const fullMonth = new Intl.DateTimeFormat("es-PE", { month: "long", year: "numeric", timeZone: "UTC" });
function monthLabel(month, includeYear = true) {
  const date = new Date(month.slice(0, 7) + "-01T00:00:00Z");
  return (includeYear ? fullMonth : shortMonth).format(date);
}

function dashboard(report) {
  const selector = byId("zone");
  const { decision, metrics, monitoring, windows } = report;
  byId("period").textContent = windows.test.map((day) => monthLabel(day)).join(" – ") + " · Horizonte de un mes";
  byId("active").textContent = names[decision.active];
  byId("decision").textContent = decision.active === "challenger" ? "Candidato promovido en validación" : "Se mantuvo la referencia estacional";
  byId("mae").textContent = format.format(metrics.test[decision.active].mae);
  byId("alerts").textContent = monitoring.filter((row) => row.drift_alert || row.performance_alert).length;
  byId("run").textContent = "Ejecución " + report.run_id;
  byId("promotion").textContent =
    "Mejora del candidato en validación: " + format.format(100 * decision.validation_improvement) +
    "%. Mínimo requerido: " + format.format(100 * decision.minimum_improvement) +
    "%. Estaciones con regresión sobre el umbral: " +
    (decision.regressed_zones.map((zone) => report.zones[zone]).join(", ") || "ninguna") + ".";
  tableBody("comparison", [["Validación", metrics.validation], ["Prueba", metrics.test]].map(([label, group]) => [
    label, format.format(group.baseline.mae), format.format(group.challenger.mae),
  ]));
  for (const [id, label] of Object.entries(report.zones)) selector.add(new Option(label, id));
  const gamarra = Object.entries(report.zones).find(([, label]) => label === "Gamarra");
  if (gamarra) selector.value = gamarra[0];

  const canvas = byId("chart");
  const tooltip = byId("chart-tooltip");
  let rows;
  let chart;

  function resetChart() {
    tooltip.hidden = true;
    chart = drawChart(rows);
  }

  function update() {
    const zone = Number(selector.value);
    rows = report.predictions.filter((row) => row[1] === zone);
    byId("monitor-station").textContent = report.zones[zone] + " · Comparación con validación";
    tableBody("series", rows.map(([day, , actual, baseline, challenger]) => [
      monthLabel(day), format.format(actual), format.format(baseline), format.format(challenger),
    ]));
    tableBody("monitor", monitoring.filter((row) => row.zone === zone).map((row) => [
      row.period,
      format.format(row.drift_score),
      format.format(row.mae) + " / " + format.format(row.reference_mae),
      [row.drift_alert && "Drift", row.performance_alert && "Error alto"].filter(Boolean).join(" y ") || "Sin alerta",
    ]));
    for (const row of byId("monitor").rows) {
      if (row.lastElementChild.textContent !== "Sin alerta") row.lastElementChild.classList.add("signal");
    }
    resetChart();
  }
  function showMonth(event) {
    const { left, width } = canvas.getBoundingClientRect();
    const fraction = (event.clientX - left - chart.left) / (chart.right - chart.left);
    const index = Math.round(Math.min(1, Math.max(0, fraction)) * (rows.length - 1));
    const [month, , ...values] = rows[index];
    const title = document.createElement("strong");
    title.textContent = monthLabel(month);
    tooltip.replaceChildren(title);
    for (const [i, label] of ["Observado", "Estacional", "Candidato"].entries()) {
      const line = document.createElement("div");
      const name = document.createElement("span");
      const value = document.createElement("span");
      name.textContent = label;
      value.textContent = format.format(values[i]);
      line.append(name, value);
      tooltip.append(line);
    }
    drawChart(rows, index);
    tooltip.hidden = false;
    const point = chart.x(index);
    const tooltipWidth = tooltip.offsetWidth;
    tooltip.style.left = Math.max(0, Math.min(width - tooltipWidth, point + 12 + tooltipWidth <= width ? point + 12 : point - tooltipWidth - 12)) + "px";
    tooltip.style.top = "12px";
  }

  byId("dashboard").hidden = false;
  byId("status").textContent = "";
  selector.addEventListener("change", update);
  new ResizeObserver(resetChart).observe(canvas);
  canvas.addEventListener("pointermove", showMonth);
  canvas.addEventListener("pointerdown", showMonth);
  canvas.addEventListener("pointerleave", resetChart);
  canvas.addEventListener("pointercancel", resetChart);
  update();
}

try {
  const response = await fetch("./report.json");
  if (!response.ok) throw new Error("Reporte no disponible");
  dashboard(await response.json());
} catch (error) {
  byId("status").textContent = "No se pudo cargar el reporte. Abre la demo desde el servidor local indicado en el README.";
}
