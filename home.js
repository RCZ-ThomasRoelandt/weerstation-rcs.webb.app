/* =====================================================================
   HOME.JS  —  huidig weer + trendgrafieken (24 u / 7 d / 30 d)
   ===================================================================== */

// Welke grafieken er op de homepagina komen.
// "lines" = welke feeds (uit config.js) in dezelfde grafiek komen.
const TRENDS = [
  { title: "Buitentemperatuur", icon: "thermo", unit: "°C",
    lines: [{ id: "buitenTemp", name: "Buiten", color: "#c86b02" }] },
  { title: "Groen dak vs gewoon dak", icon: "leaf", unit: "°C",
    lines: [{ id: "groenDak", name: "Groen dak", color: "#d6ad00" },
            { id: "gewoonDak", name: "Gewoon dak", color: "#555555" }] },
  { title: "Luchtvochtigheid", icon: "drops", unit: "%",
    lines: [{ id: "vochtigheid", name: "Vochtigheid", color: "#d6ad00" }] },
  { title: "Luchtdruk", icon: "gauge", unit: "hPa",
    lines: [{ id: "luchtdruk", name: "Luchtdruk", color: "#555555" }] },
  { title: "Windsnelheid", icon: "wind", unit: "km/u",
    lines: [{ id: "windsnelheid", name: "Wind", color: "#c86b02" }] },
  { title: "Neerslag", icon: "rain", unit: "mm", bar: true,
    lines: [{ id: "neerslag", name: "Neerslag", color: "#d6ad00" }] },
];

const charts = [];
let hours = 24;

/* ---------- Huidig weer (rechtsboven) ---------- */
async function loadNow() {
  const get = id => getLast(id).catch(() => null);
  const [t, h, p, w, wr, r] = await Promise.all(
    ["buitenTemp", "vochtigheid", "luchtdruk", "windsnelheid", "windrichting", "neerslag"].map(get));

  document.getElementById("now-temp").innerHTML = `${t ? fmt(t.value) : "–"}<span>°C</span>`;
  document.getElementById("now-time").textContent = t ? `Gemeten ${timeAgo(t.time)}` : "Geen verbinding met de Pico";
  document.getElementById("now-hum").textContent  = h ? `${fmt(h.value, 0)} %` : "–";
  document.getElementById("now-pres").textContent = p ? `${fmt(p.value, 0)} hPa` : "–";
  document.getElementById("now-wind").textContent = w ? `${fmt(w.value)} km/u ${wr ? windName(wr.value) : ""}` : "–";
  document.getElementById("now-rain").textContent = r ? `${fmt(r.value)} mm` : "–";
}

/* ---------- Kaarten voor de grafieken aanmaken ---------- */
function buildCards() {
  const box = document.getElementById("charts");
  TRENDS.forEach((tr, i) => {
    const card = document.createElement("div");
    card.className = "card chart-card";
    card.innerHTML = `
      <h3>${icon(tr.icon)}${tr.title}</h3>
      <div class="stats" id="stats-${i}">&nbsp;</div>
      <div class="chart-wrap"><canvas id="chart-${i}"></canvas></div>`;
    box.appendChild(card);
  });
}

/* ---------- Grafieken laden voor de gekozen periode ---------- */
async function loadTrends() {
  // Schoolkleuren: goud #D6AD00, oranje #C86B02, grijs #555555
  Chart.defaults.color = "#8a8a8a";
  Chart.defaults.font.family = "Fira Sans, system-ui, sans-serif";

  for (let i = 0; i < TRENDS.length; i++) {
    const tr = TRENDS[i];
    const series = await Promise.all(tr.lines.map(l => getHistory(l.id, hours).catch(() => [])));

    // Min / max / gemiddelde van de eerste lijn
    const vals = series[0].map(p => p.v).filter(v => !isNaN(v));
    const statsEl = document.getElementById(`stats-${i}`);
    if (!vals.length) {
      statsEl.textContent = "Nog geen data voor deze periode";
    } else if (tr.bar) {
      const total = vals.reduce((a, b) => a + b, 0);
      statsEl.innerHTML = `Max <b>${fmt(Math.max(...vals))} ${tr.unit}</b>
                           <span>Metingen met regen <b>${vals.filter(v => v > 0).length}</b></span>`;
    } else if (tr.lines.length === 2 && series[1].length) {
      const avg = a => a.reduce((x, y) => x + y, 0) / a.length;
      const diff = avg(series[1].map(p => p.v)) - avg(vals);
      statsEl.innerHTML = `Gem. groen <b>${fmt(avg(vals))} °C</b>
        <span>Gem. gewoon <b>${fmt(avg(series[1].map(p => p.v)))} °C</b></span>
        <span>Verschil <b style="color:var(--orange)">${diff >= 0 ? "−" : "+"}${fmt(Math.abs(diff))} °C</b></span>`;
    } else {
      const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
      statsEl.innerHTML = `Min <b>${fmt(Math.min(...vals))}</b>
        <span>Max <b>${fmt(Math.max(...vals))}</b></span>
        <span>Gem. <b>${fmt(avg)} ${tr.unit}</b></span>`;
    }

    // Labels op de x-as
    const labels = series[0].map(p => hours <= 24
      ? p.t.toLocaleTimeString("nl-BE", { hour: "2-digit", minute: "2-digit" })
      : p.t.toLocaleDateString("nl-BE", { day: "numeric", month: "short" }));

    if (charts[i]) charts[i].destroy();
    charts[i] = new Chart(document.getElementById(`chart-${i}`), {
      type: tr.bar ? "bar" : "line",
      data: {
        labels,
        datasets: tr.lines.map((l, k) => ({
          label: l.name,
          data: series[k].map(p => p.v),
          borderColor: l.color,
          backgroundColor: tr.bar ? l.color : l.color + "22",
          fill: !tr.bar && tr.lines.length === 1,
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2,
          borderRadius: 4,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: tr.lines.length > 1, labels: { boxWidth: 12 } },
          tooltip: { callbacks: { label: c => `${c.dataset.label}: ${fmt(c.parsed.y)} ${tr.unit}` } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 7, maxRotation: 0 } },
          y: { grid: { color: "#eeeeee" }, beginAtZero: !!tr.bar },
        },
      },
    });
  }
}

/* ---------- Knoppen 24 u / 7 d / 30 d ---------- */
document.querySelectorAll("#period button").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll("#period button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    hours = parseInt(btn.dataset.h);
    loadTrends();
  };
});

buildCards();
loadNow();
loadTrends();
setInterval(loadNow, CONFIG.REFRESH_SECONDS * 1000);
