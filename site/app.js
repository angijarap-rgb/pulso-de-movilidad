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

function drawChart(rows) {
  const canvas = byId("chart");
  const { width, height } = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const left = 50;
  const right = width - 12;
  const top = 12;
  const bottom = height - 33;
  const max = Math.max(1, ...rows.flatMap((row) => row.slice(2)));
  const unit = 10 ** Math.floor(Math.log10(max));
  const ceiling = Math.ceil(max / unit) * unit;
  const x = (index) => left + index * (right - left) / Math.max(rows.length - 1, 1);
  const y = (value) => bottom - value / ceiling * (bottom - top);
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#49615a";
  for (let tick = 0; tick <= 4; tick++) {
    const value = ceiling * tick / 4;
    const position = y(value);
    ctx.strokeStyle = "#d5dfd7";
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
    ctx.fillText(rows[index][0], x(index), bottom + 20);
  }
  const series = [[2, "#125f4b", []], [3, "#aa5c21", [5, 4]], [4, "#5b4ca3", [2, 3]]];
  for (const [column, color, dash] of series) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash(dash);
    rows.forEach((row, index) => {
      if (index === 0) ctx.moveTo(x(index), y(row[column]));
      else ctx.lineTo(x(index), y(row[column]));
    });
    ctx.stroke();
  }
}

function dashboard(report) {
  const selector = byId("zone");
  const { decision, metrics, monitoring, windows } = report;
  byId("source").textContent = "Perú · Línea 1 del Metro de Lima";
  byId("period").textContent = windows.test.map((day) => day.slice(0, 7)).join(" a ");
  byId("active").textContent = names[decision.active];
  byId("decision").textContent = decision.active === "challenger" ? "Candidato promovido en validación" : "Se conserva el baseline estacional";
  byId("mae").textContent = format.format(metrics.test[decision.active].mae);
  byId("alerts").textContent = monitoring.filter((row) => row.drift_alert || row.performance_alert).length;
  byId("run").textContent = "Ejecución " + report.run_id;
  byId("promotion").textContent =
    "Mejora del candidato en validación: " + format.format(100 * decision.validation_improvement) +
    "%. Mínimo requerido: 3%. Estaciones con regresión sobre el umbral: " +
    (decision.regressed_zones.map((zone) => report.zones[zone]).join(", ") || "ninguna") + ".";
  tableBody("comparison", [["Validación", metrics.validation], ["Prueba", metrics.test]].map(([label, group]) => [
    label, format.format(group.baseline.mae), format.format(group.challenger.mae),
  ]));
  for (const [id, label] of Object.entries(report.zones)) selector.add(new Option(label, id));

  function update() {
    const zone = Number(selector.value);
    const rows = report.predictions.filter((row) => row[1] === zone);
    tableBody("series", rows.map(([day, , actual, baseline, challenger]) => [
      day, format.format(actual), format.format(baseline), format.format(challenger),
    ]));
    tableBody("monitor", monitoring.filter((row) => row.zone === zone).map((row) => [
      row.period,
      format.format(row.drift_score),
      format.format(row.mae) + " / " + format.format(row.reference_mae),
      [row.drift_alert && "Drift", row.performance_alert && "Error alto"].filter(Boolean).join(" y ") || "Sin alerta",
    ]));
    drawChart(rows);
  }
  byId("dashboard").hidden = false;
  selector.addEventListener("change", update);
  window.addEventListener("resize", update);
  update();
}

try {
  const response = await fetch("./report.json");
  if (!response.ok) throw new Error("Reporte no disponible");
  dashboard(await response.json());
} catch (error) {
  byId("status").textContent = "No se pudo cargar el reporte. Abre la demo desde el servidor local indicado en el README.";
}
