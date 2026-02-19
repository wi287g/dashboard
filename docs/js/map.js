/**
 * map.js — Leaflet map initialisation and interaction.
 *
 * Public API:
 *   initMap(geojson, statusData)            — called once by main.js on boot
 *   applyStatusFilter(statusValue)          — called by toolbar filter
 *   highlightCountyByName(partialName)      — called by search box
 */

/** @type {L.Map} */
let map;

/** @type {L.GeoJSON} */
let countyLayer;

// ── Init ──────────────────────────────────────────────────────────────────────

/**
 * Create the Leaflet map and render county polygons.
 *
 * @param {object} geojson      - GeoJSON FeatureCollection for WI counties.
 * @param {object} statusData   - Keyed by FIPS → { cooperation, ... }
 */
function initMap(geojson, statusData) {
  map = L.map("map").setView(CONFIG.defaultMapCenter, CONFIG.defaultMapZoom);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
  }).addTo(map);

  countyLayer = L.geoJSON(geojson, {
    style: (feature) => countyStyle(feature, statusData),
    onEachFeature: (feature, layer) => bindFeature(feature, layer, statusData),
  }).addTo(map);

  addLegend();
}

// ── Style helpers ─────────────────────────────────────────────────────────────

/**
 * Return Leaflet path style for a county feature.
 */
function countyStyle(feature, statusData) {
  const fips = getFips(feature);
  const entry = statusData[fips] || { cooperation: "unknown" };
  return {
    fillColor:   CONFIG.colors[entry.cooperation] || CONFIG.colors.unknown,
    fillOpacity: 0.78,
    weight:      1,
    opacity:     1,
    color:       "#fff",
  };
}

function getFips(feature) {
  return feature.properties.GEOID || feature.properties.FIPS || "";
}

// ── Interactions ──────────────────────────────────────────────────────────────

/** Currently selected layer — kept to reset hover style. */
let _selectedLayer = null;

function bindFeature(feature, layer, statusData) {
  const name = feature.properties.NAME || feature.properties.name || "Unknown";
  const fips = getFips(feature);

  layer.bindTooltip(name, { sticky: true, direction: "top" });

  layer.on("mouseover", function () {
    if (this !== _selectedLayer) {
      this.setStyle({ fillOpacity: 0.95, weight: 2 });
    }
  });

  layer.on("mouseout", function () {
    if (this !== _selectedLayer) {
      countyLayer.resetStyle(this);
    }
  });

  layer.on("click", function () {
    // Reset previous selection
    if (_selectedLayer && _selectedLayer !== this) {
      countyLayer.resetStyle(_selectedLayer);
    }
    _selectedLayer = this;
    this.setStyle({ weight: 3, fillOpacity: 1 });

    handleCountySelect(fips, name);
  });

  // Keyboard / focus support
  layer.on("keydown", (e) => {
    if (e.originalEvent.key === "Enter" || e.originalEvent.key === " ") {
      handleCountySelect(fips, name);
    }
  });
}

// ── Legend ────────────────────────────────────────────────────────────────────

function addLegend() {
  const div = document.getElementById("map-legend");
  const entries = [
    ["287g",      "287(g) agreement"],
    ["detainers", "Detainers / cooperation"],
    ["none",      "No known cooperation"],
    ["unknown",   "Unknown / no data"],
  ];

  div.innerHTML =
    "<strong>County status</strong><br/>" +
    entries
      .map(
        ([key, label]) =>
          `<span class="swatch" style="background:${CONFIG.colors[key]}"></span>${label}`
      )
      .join("<br/>");
}

// ── Filter ────────────────────────────────────────────────────────────────────

/**
 * Dim (reduce opacity of) counties that do not match `statusValue`.
 * Pass "all" to reset.
 *
 * @param {string} statusValue
 * @param {object} statusData
 */
function applyStatusFilter(statusValue, statusData) {
  countyLayer.eachLayer((layer) => {
    const fips = getFips(layer.feature);
    const entry = statusData[fips] || { cooperation: "unknown" };
    const match = statusValue === "all" || entry.cooperation === statusValue;
    layer.setStyle({
      fillOpacity: match ? 0.78 : 0.12,
      weight:      match ? 1 : 0.5,
    });
  });
}

// ── Search ────────────────────────────────────────────────────────────────────

/**
 * Pan and zoom to the first county whose NAME contains `query` (case-insensitive).
 * Fires a click event on it.
 *
 * @param {string} query
 * @param {object} statusData
 */
function highlightCountyByName(query, statusData) {
  if (!query.trim()) return;
  const lq = query.toLowerCase();

  countyLayer.eachLayer((layer) => {
    const name = (
      layer.feature.properties.NAME ||
      layer.feature.properties.name ||
      ""
    ).toLowerCase();

    if (name.includes(lq)) {
      const fips = getFips(layer.feature);
      const displayName =
        layer.feature.properties.NAME || layer.feature.properties.name || fips;

      map.fitBounds(layer.getBounds(), { maxZoom: 9 });

      if (_selectedLayer) countyLayer.resetStyle(_selectedLayer);
      _selectedLayer = layer;
      layer.setStyle({ weight: 3, fillOpacity: 1 });

      handleCountySelect(fips, displayName);
    }
  });
}
