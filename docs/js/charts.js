/**
 * charts.js — Chart.js bar charts for detainers and SCAAP payments.
 *
 * Public API:
 *   updateCharts(fips, detainersData, scaapData)
 *   clearCharts()
 */

/** @type {Chart|null} */
let detainersChartInstance = null;

/** @type {Chart|null} */
let scaapChartInstance = null;

const CHART_DEFAULTS = {
  responsive: true,
  plugins: {
    legend: { display: false },
  },
  scales: {
    y: { beginAtZero: true },
  },
};

// ── Public ────────────────────────────────────────────────────────────────────

/**
 * Render (or re-render) both charts for the given county FIPS.
 *
 * @param {string}  fips
 * @param {Object.<string, {year:number,count:number}[]>}  detainersData
 * @param {Object.<string, {year:number,amount:number}[]>} scaapData
 */
function updateCharts(fips, detainersData, scaapData) {
  const detSeries  = (detainersData[fips] || []).slice().sort((a, b) => a.year - b.year);
  const scaapSeries = (scaapData[fips]    || []).slice().sort((a, b) => a.year - b.year);

  const noData = detSeries.length === 0 && scaapSeries.length === 0;
  document.getElementById("no-chart-data").hidden = !noData;
  document.getElementById("charts").style.display = noData ? "none" : "";

  if (noData) {
    clearCharts();
    return;
  }

  _renderBar(
    "detainersChart",
    "Detainers by year",
    detSeries.map((d) => String(d.year)),
    detSeries.map((d) => d.count),
    "ICE detainer requests (count)",
    "#3b82f6"
  );

  _renderBar(
    "scaapChart",
    "SCAAP payments by year",
    scaapSeries.map((d) => String(d.year)),
    scaapSeries.map((d) => d.amount),
    "SCAAP award (USD)",
    "#10b981",
    /* formatAsDollar= */ true
  );
}

/**
 * Destroy existing chart instances (called when no data is available).
 */
function clearCharts() {
  if (detainersChartInstance) {
    detainersChartInstance.destroy();
    detainersChartInstance = null;
  }
  if (scaapChartInstance) {
    scaapChartInstance.destroy();
    scaapChartInstance = null;
  }
}

// ── Private ───────────────────────────────────────────────────────────────────

function _renderBar(canvasId, title, labels, values, datasetLabel, color, formatAsDollar = false) {
  const ctx = document.getElementById(canvasId);

  // Destroy previous instance for this canvas
  if (canvasId === "detainersChart" && detainersChartInstance) {
    detainersChartInstance.destroy();
    detainersChartInstance = null;
  }
  if (canvasId === "scaapChart" && scaapChartInstance) {
    scaapChartInstance.destroy();
    scaapChartInstance = null;
  }

  const instance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label:           datasetLabel,
          data:            values,
          backgroundColor: color,
          borderRadius:    3,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        title: {
          display: true,
          text:    title,
          font:    { size: 13 },
        },
        tooltip: {
          callbacks: {
            label: (ctx) =>
              formatAsDollar
                ? ` ${_usd(ctx.parsed.y)}`
                : ` ${ctx.parsed.y.toLocaleString()}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (v) =>
              formatAsDollar ? _usd(v, true) : v.toLocaleString(),
          },
        },
      },
    },
  });

  if (canvasId === "detainersChart") detainersChartInstance = instance;
  else scaapChartInstance = instance;
}

function _usd(value, compact = false) {
  return new Intl.NumberFormat("en-US", {
    style:    "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 0,
  }).format(value);
}
