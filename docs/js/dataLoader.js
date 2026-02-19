/**
 * dataLoader.js — Fetches and validates all JSON data files.
 * Returns a single `AppData` object consumed by map.js and charts.js.
 */

/**
 * @typedef {{
 *   geo: object,
 *   status: Object.<string, StatusEntry>,
 *   detainers: Object.<string, DetainerEntry[]>,
 *   scaap: Object.<string, ScaapEntry[]>
 * }} AppData
 *
 * @typedef {{ cooperation: string, last_updated: string, sources: string[], notes?: string }} StatusEntry
 * @typedef {{ year: number, count: number }} DetainerEntry
 * @typedef {{ year: number, amount: number }} ScaapEntry
 */

/**
 * Fetch + parse a single JSON file.
 * @param {string} path - URL relative to the page.
 * @returns {Promise<any>}
 */
async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} loading ${path}`);
  }
  return res.json();
}

/**
 * Load all four data files in parallel.
 * @returns {Promise<AppData>}
 */
async function loadAllData() {
  const [geo, status, detainers, scaap] = await Promise.all([
    loadJson(CONFIG.dataPaths.countiesGeoJson),
    loadJson(CONFIG.dataPaths.status),
    loadJson(CONFIG.dataPaths.detainers),
    loadJson(CONFIG.dataPaths.scaap),
  ]);

  return { geo, status, detainers, scaap };
}
