/**
 * config.js — Global constants and configuration.
 * Edit values here; do not hard-code them elsewhere.
 */

const CONFIG = Object.freeze({
  /** Rough geographic center of Wisconsin */
  defaultMapCenter: [44.5, -89.5],
  defaultMapZoom: 6,

  /** Fill colors keyed by cooperation status */
  colors: {
    "287g":      "#ef4444", // red
    detainers:   "#f97316", // orange
    none:        "#d1d5db", // light grey
    unknown:     "#9ca3af", // medium grey
  },

  /** Paths relative to docs/ */
  dataPaths: {
    countiesGeoJson: "data/counties.geojson",
    status:          "data/287g_status.json",
    detainers:       "data/detainers_by_county_year.json",
    scaap:           "data/scaap_by_county_year.json",
  },

  /** Human-readable labels for cooperation statuses */
  statusLabels: {
    "287g":    "Active 287(g) agreement with ICE",
    detainers: "Honors ICE detainers / some cooperation",
    none:      "No known cooperation with ICE",
    unknown:   "Status unknown / not yet documented",
  },

  /** CSS class suffix used on .status-badge elements */
  statusBadgeClass: {
    "287g":    "s-287g",
    detainers: "s-detainers",
    none:      "s-none",
    unknown:   "s-unknown",
  },
});
