/**
 * main.js — App entry point.
 *
 * Orchestrates data loading → map initialisation → UI wire-up.
 * handleCountySelect() is called from map.js (county click/keyboard).
 */

/** Module-level cache for loaded data, shared with map/chart handlers. */
let globalData = null;

// ── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  const overlay = document.getElementById("loading-overlay");

  try {
    const data = await loadAllData();
    globalData  = data;

    initMap(data.geo, data.status);
    wireToolbar();

    // Expose latest-update date from any status entry if present
    const dates = Object.values(data.status)
      .map((e) => e.last_updated)
      .filter(Boolean)
      .sort();
    if (dates.length) {
      document.getElementById("last-updated-label").textContent =
        `Data last updated: ${dates[dates.length - 1]}`;
    }
  } catch (err) {
    console.error("Dashboard init failed:", err);
    const summary = document.getElementById("county-summary");
    summary.innerHTML = `
      <p style="color:#b91c1c;font-weight:600;">Failed to load dashboard data.</p>
      <p>Please check the browser console for details, or
         <a href="https://github.com/wi287g/dashboard/issues">file an issue</a>.</p>`;
  } finally {
    overlay.classList.add("hidden");
  }
});

// ── Toolbar wiring ────────────────────────────────────────────────────────────

function wireToolbar() {
  const filterEl = document.getElementById("status-filter");
  filterEl.addEventListener("change", () => {
    if (!globalData) return;
    applyStatusFilter(filterEl.value, globalData.status);
  });

  const searchEl = document.getElementById("county-search");
  let searchTimeout;
  searchEl.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      if (!globalData) return;
      highlightCountyByName(searchEl.value, globalData.status);
    }, 300);
  });

  searchEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && globalData) {
      highlightCountyByName(searchEl.value, globalData.status);
    }
  });
}

// ── County selection (called by map.js) ───────────────────────────────────────

/**
 * Update the sidebar summary panel and charts for the selected county.
 *
 * @param {string} fips
 * @param {string} name
 */
function handleCountySelect(fips, name) {
  if (!globalData) return;

  const entry  = globalData.status[fips] || { cooperation: "unknown" };
  const coop   = entry.cooperation || "unknown";
  const label  = CONFIG.statusLabels[coop] || "Unknown";
  const badge  = CONFIG.statusBadgeClass[coop] || "s-unknown";
  const updated = entry.last_updated || "Unknown";
  const sources = Array.isArray(entry.sources) && entry.sources.length
    ? entry.sources.join("; ")
    : "Not yet annotated";
  const notes  = entry.notes ? `<p><strong>Notes:</strong> ${_esc(entry.notes)}</p>` : "";

  document.getElementById("county-summary").innerHTML = `
    <h3>${_esc(name)} County</h3>
    <p>
      <strong>Cooperation status:</strong>&nbsp;
      <span class="status-badge ${badge}">${_esc(coop)}</span>
      ${_esc(label)}
    </p>
    <p><strong>Last updated:</strong> ${_esc(updated)}</p>
    <p><strong>Sources:</strong> ${_esc(sources)}</p>
    ${notes}
    <p class="muted" style="font-size:0.75rem;">FIPS: ${_esc(fips)}</p>
  `;

  updateCharts(fips, globalData.detainers, globalData.scaap);

  // Scroll sidebar into view on mobile
  document.getElementById("sidebar").scrollTop = 0;
}

// ── Utility ───────────────────────────────────────────────────────────────────

/** Minimal HTML-escaping for untrusted string interpolation. */
function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
