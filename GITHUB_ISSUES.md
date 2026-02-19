# GitHub Issues — Copy-Paste Backlog

Use this file to quickly create the project's initial GitHub Issues.
Copy each block, paste into GitHub → Issues → New Issue, and set the
label shown in the `Labels:` line.

> Issues are grouped by milestone. Suggested milestones:
> **M1 Bootstrap**, **M2 Real Data**, **M3 Automation**, **M4 Polish**

---

## M1 — Bootstrap

---

### Issue B-1

**Title:** Replace placeholder counties.geojson with real Census TIGER geometry

**Labels:** `data`, `M1-bootstrap`

**Body:**
The current `docs/data/counties.geojson` contains rough bounding-box polygons
for 10 counties only, sufficient for development testing.

**Tasks:**
- [ ] Download WI county shapefile from Census TIGER 2023:
  `https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/tl_2023_55_county.zip`
- [ ] Convert to GeoJSON (WGS84) and slim to only `GEOID`, `NAME`, `STATEFP` properties:
  ```bash
  ogr2ogr -f GeoJSON -t_srs EPSG:4326 \
    -select GEOID,NAME,STATEFP \
    -where "STATEFP='55'" \
    docs/data/counties.geojson tl_2023_55_county.shp
  ```
- [ ] Verify all 72 counties load and color correctly in the dashboard.
- [ ] Commit the file (check size; simplify geometry if > 1 MB using mapshaper).

**Acceptance criteria:**
All 72 Wisconsin counties render with correct FIPS-keyed colors. Map loads in < 3 s on a mobile connection.

---

### Issue B-2

**Title:** Verify GitHub Pages deployment and CDN reachability

**Labels:** `infra`, `M1-bootstrap`

**Body:**
Confirm the site loads correctly from GitHub Pages and all CDN assets are reachable.

**Tasks:**
- [ ] Set repo → Settings → Pages → Source: Deploy from branch `main`, folder `/docs`.
- [ ] Confirm `index.html` loads at `https://wi287g.github.io/dashboard/`.
- [ ] Verify Leaflet map tiles load (check Network tab for 200s from `tile.openstreetmap.org`).
- [ ] Verify Chart.js CDN loads (no console errors).
- [ ] Verify all four data JSON files return 200 (not 404).
- [ ] Test on mobile viewport.

---

### Issue B-3

**Title:** Add FIPS ↔ county name mapping validation test

**Labels:** `pipeline`, `testing`, `M1-bootstrap`

**Body:**
The `scripts/wi_fips.py` mapping is used by all pipeline scripts. Add a
simple test to catch any regression.

**Tasks:**
- [ ] Create `scripts/test_wi_fips.py` using `unittest` or `pytest`.
- [ ] Assert all 72 WI county FIPS codes are present.
- [ ] Assert `normalize_county_name("Dane County Sheriff's Office")` → `"dane"`.
- [ ] Assert `fips_from_raw("Milwaukee Co. Jail")` → `"55079"`.
- [ ] Add `pytest scripts/` step to the GH Actions workflow.

---

## M2 — Real Data

---

### Issue D-1

**Title:** Populate 287g_status.json from ICE MOA list

**Labels:** `data`, `pipeline`, `M2-real-data`

**Body:**
Run `scripts/fetch_287g.py` and `scripts/merge_datasets.py` to replace
placeholders with real ICE 287(g) data for Wisconsin counties.

**Tasks:**
- [ ] Run `python scripts/fetch_287g.py` and check `docs/data/raw/287g_wi.csv`.
- [ ] Review output for any FIPS lookup failures (logged as warnings).
- [ ] Update `scripts/wi_fips.py` ALIASES if any agency names don't match.
- [ ] Run `python scripts/merge_datasets.py` and verify `287g_status.json`.
- [ ] Manually review diff — confirm statuses look correct against public ICE list.
- [ ] Commit and open a PR for review before merging.

---

### Issue D-2

**Title:** Source and parse ACLU-WI detainer data

**Labels:** `data`, `pipeline`, `M2-real-data`

**Body:**
Identify available ACLU-WI (or equivalent) reports for Wisconsin detainer
counts by county and year, and run `parse_aclu_reports.py`.

**Tasks:**
- [ ] Identify available reports at https://www.aclu-wi.org and note years covered.
- [ ] Download PDFs/CSVs into `reports/` (gitignored; document sources in a `reports/SOURCES.md`).
- [ ] Run `python scripts/parse_aclu_reports.py --input-dir reports/`.
- [ ] Check for FIPS lookup failures and update column aliases if needed.
- [ ] Confirm `docs/data/raw/aclu_detainers.csv` has reasonable values.
- [ ] Run merge step and verify `detainers_by_county_year.json`.

---

### Issue D-3

**Title:** Source and ingest BJS SCAAP payment data

**Labels:** `data`, `pipeline`, `M2-real-data`

**Body:**
SCAAP award data is published annually by BJS. Download and process it.

**Tasks:**
- [ ] Download county-level SCAAP award tables from https://bjs.ojp.gov/programs/scaap.
  (Look for "local" or "county" breakdowns — note these may be state-aggregated only;
  county-level may require FOIA.)
- [ ] If county-level is not directly available, document that gap in `287g_status.json`
  notes and as a known limitation in README.
- [ ] If available: format as `docs/data/raw/aclu_scaap.csv` (columns: fips, county_name, year, amount).
- [ ] Run merge step and verify `scaap_by_county_year.json`.

---

### Issue D-4

**Title:** Add `_data_version` and `_generated_at` metadata to all JSON outputs

**Labels:** `pipeline`, `data`, `M2-real-data`

**Body:**
The dashboard should surface when data was last generated, and scripts should
stamp a version for cache-busting and auditability.

**Tasks:**
- [ ] Add `_generated_at` (ISO 8601 UTC) and `_data_version` (semver or date string)
  top-level keys to all three output JSONs in `merge_datasets.py`.
- [ ] In `main.js`, read `_generated_at` from the status JSON and display it in
  the `#last-updated-label` element (already wired; just needs the key).
- [ ] Document the versioning scheme in README.

---

## M3 — Automation & Ops

---

### Issue A-1

**Title:** Enable and test weekly GH Actions data update

**Labels:** `infra`, `automation`, `M3-automation`

**Body:**
The `.github/workflows/update-data.yml` workflow is scaffolded but needs
a live test.

**Tasks:**
- [ ] Trigger the workflow manually via Actions → "Update dashboard data" → Run workflow.
- [ ] Confirm all three pipeline steps succeed (or fail gracefully with stale-cache fallback).
- [ ] Confirm commit-and-push step fires only when data changed.
- [ ] Confirm GitHub Pages re-deploys after the commit.
- [ ] Review workflow logs and fix any path or permission issues.

---

### Issue A-2

**Title:** Add failure notification (Slack or email) to the GH Actions workflow

**Labels:** `infra`, `automation`, `M3-automation`

**Body:**
If the automated pipeline fails, maintainers should be alerted.

**Tasks (choose one path):**
- [ ] **Slack:** Create a `SLACK_WEBHOOK_URL` repo secret and uncomment the
  `slackapi/slack-github-action` step in `update-data.yml`.
- [ ] **Email / GH notification:** Enable "Send email notifications for failed workflows"
  in repo notification settings (simplest option, no secrets needed).
- [ ] Confirm a deliberate failure (e.g. bad URL) triggers the alert.

---

### Issue A-3

**Title:** Cache the ICE page HTML to avoid repeated fetches during development

**Labels:** `pipeline`, `M3-automation`

**Body:**
Every local run currently fetches from ICE's server. Add a `--force-cache`
flow and document it.

**Tasks:**
- [ ] Verify `fetch_287g.py --force-cache --cache-path docs/data/raw/287g_raw.html` works.
- [ ] Add a `Makefile` (or `scripts/run_pipeline.sh`) that shows the end-to-end
  local run with `--force-cache` as the default to be polite to ICE's server.
- [ ] Document in README.

---

## M4 — Polish & Accessibility

---

### Issue F-1

**Title:** Year filter — dropdown to recompute charts by year range

**Labels:** `enhancement`, `ux`, `M4-polish`

**Body:**
Allow users to filter charts to a specific year or range.

**Tasks:**
- [ ] Add a `<select id="year-filter">` to the sidebar (or toolbar).
- [ ] On change, re-call `updateCharts(fips, ...)` with a filtered slice of the
  time-series data.
- [ ] Show "No data for selected year" message when series is empty.
- [ ] Optionally: update map choropleth to show detainer rate for the selected year.

---

### Issue F-2

**Title:** Time-lapse map slider — show 287(g)/detainer spread by year

**Labels:** `enhancement`, `ux`, `M4-polish`

**Body:**
A year slider that animates county color changes over time would be a powerful
accountability tool.

**Tasks:**
- [ ] Add `<input type="range">` year slider to the toolbar.
- [ ] On change, re-color the county layer based on detainer data for that year.
- [ ] Add play/pause button to auto-advance the slider.
- [ ] Add a "snapshot" permalink (`?year=2023`) so journalists can link to a specific year.

---

### Issue F-3

**Title:** Accessibility audit — keyboard navigation and color contrast

**Labels:** `accessibility`, `M4-polish`

**Body:**
The dashboard uses color coding and map interactions that may not be accessible
to keyboard or screen reader users.

**Tasks:**
- [ ] Verify all interactive elements (county search, filter, map counties) are
  keyboard-navigable (Tab + Enter/Space).
- [ ] Check color contrast ratios for status badge text (WCAG AA minimum 4.5:1).
- [ ] Add `aria-label` and `role` attributes where missing (map div, legend, charts).
- [ ] Test with a screen reader (NVDA/VoiceOver) and fix announced county summaries.
- [ ] Add a high-contrast mode toggle (optional but valuable for colorblind users —
  replace red/orange with pattern fills or icons).

---

### Issue F-4

**Title:** "About the data" expandable panel and methodology notes

**Labels:** `documentation`, `ux`, `M4-polish`

**Body:**
Non-expert users need context for what the statuses mean and how confident
we are in the data.

**Tasks:**
- [ ] Expand the existing `.about-box` section in the sidebar with:
  - Explanation of each cooperation status.
  - Note on data lag (SCAAP is 12–18 months delayed).
  - "Unknown ≠ cooperating" clarification.
  - Link to open-records how-to guide.
- [ ] Add a "How to contribute a correction" link pointing to the GitHub issue template.
- [ ] Consider a collapsible `<details>` element to keep the sidebar from getting too long.

---

### Issue F-5

**Title:** Static JSON API endpoints — document for downstream consumers

**Labels:** `enhancement`, `data`, `M4-polish`

**Body:**
The dashboard's JSON files are already public static files on GitHub Pages,
usable as simple API endpoints. Document and version them.

**Tasks:**
- [ ] Document the three endpoint URLs and their schemas in README under a new
  "API" section.
- [ ] Add a `_schema_version` key to each JSON (already planned in D-4).
- [ ] Add a `docs/api.md` page linked from the footer.
- [ ] Create a GitHub issue asking if CORS headers are needed (GH Pages sets
  permissive CORS by default — confirm this).

---

*Template file generated by project scaffold. Delete or archive this file
once issues have been created in GitHub.*
