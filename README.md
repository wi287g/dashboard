# Wisconsin 287(g) & ICE Detainer Dashboard

A static, public-interest dashboard tracking county-level ICE cooperation
across Wisconsin — including 287(g) Memoranda of Agreement, detainer
compliance, and federal SCAAP reimbursement payments.

**Live site:** https://wi287g.github.io/dashboard/

> **Data status:** All values are currently **placeholders**. The pipeline
> scripts need to be run (or the GH Actions workflow triggered) to populate
> real data. See [Running the pipeline](#running-the-pipeline) below.

---

## What is 287(g)?

Section 287(g) of the Immigration and Nationality Act allows ICE to
deputize local law enforcement to perform immigration enforcement functions
through a Memorandum of Agreement (MOA). Participating sheriffs can check
immigration status from jails, issue civil detainer requests, and begin
deportation paperwork.

A **detainer** is a civil request — not a judicial warrant — asking a jail
to hold someone beyond their lawful release date for ICE. Counties can
honor detainers without a formal 287(g) MOA.

**SCAAP** (State Criminal Alien Assistance Program) provides federal
reimbursements to localities that incarcerated people with certain
immigration statuses.

---

## Cooperation statuses

| Status | Meaning |
|---|---|
| `287g` | Active 287(g) Memorandum of Agreement with ICE |
| `detainers` | Honors ICE civil detainers / informal cooperation, no formal MOA |
| `none` | No documented cooperation with ICE |
| `unknown` | Insufficient data; open-records requests may be pending |

---

## Data sources

| Source | URL | Notes |
|---|---|---|
| ICE 287(g) participant list | https://www.ice.gov/identify-and-arrest/287g | Scraped by `scripts/fetch_287g.py` |
| ACLU-WI reports | https://www.aclu-wi.org | PDFs/CSVs parsed by `scripts/parse_aclu_reports.py` |
| BJS SCAAP award data | https://bjs.ojp.gov/programs/scaap | Download county-level CSV annually |
| Census TIGER county shapefiles | https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html | Replace placeholder `docs/data/counties.geojson` |

### Known limitations

- ICE can change page structure, URLs, or move data to PDFs without notice,
  causing pipeline fetch failures. The workflow falls back to cached data.
- SCAAP data is published annually with 12–18 month lag.
- Detainer counts from ACLU or open-records responses may have coverage
  gaps — not all counties report, and practices change between sheriffs.
- Manual annotations (notes, sources) in `287g_status.json` are preserved
  across automated pipeline runs.

---

## Project structure

```
dashboard/
  docs/                   # GitHub Pages root (static site)
    index.html
    css/styles.css
    js/
      config.js           # Constants and color palette
      dataLoader.js       # fetch() wrappers for JSON files
      map.js              # Leaflet map, county styling, filter, search
      charts.js           # Chart.js bar charts
      main.js             # Entry point, toolbar wiring, county-click handler
    data/
      counties.geojson    # WI county polygons (replace with TIGER data)
      287g_status.json    # Cooperation status keyed by FIPS
      detainers_by_county_year.json
      scaap_by_county_year.json
      raw/                # Gitignored pipeline intermediates
  scripts/
    wi_fips.py            # Shared county-name → FIPS lookup
    fetch_287g.py         # Scrape ICE 287(g) list → raw CSV
    parse_aclu_reports.py # Parse ACLU/watchdog PDFs or CSVs → raw CSVs
    merge_datasets.py     # Join all sources → docs/data/ JSONs
  .github/workflows/
    update-data.yml       # Scheduled weekly automation
  requirements.txt
  README.md
```

---

## Running the pipeline locally

```bash
# 1. Clone and set up
git clone https://github.com/wi287g/dashboard.git
cd dashboard
pip install -r requirements.txt

# 2. Fetch 287(g) list
python scripts/fetch_287g.py

# 3. Parse ACLU/watchdog reports (place PDFs or CSVs in reports/)
python scripts/parse_aclu_reports.py --input-dir reports/

# 4. Merge → update dashboard JSONs
python scripts/merge_datasets.py

# 5. Preview locally (any static server)
cd docs && python -m http.server 8000
# Then open http://localhost:8000
```

### Getting real county geometry

Download Wisconsin county shapefiles from Census TIGER and convert to GeoJSON:

```bash
# Using ogr2ogr (GDAL)
wget "https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/tl_2023_55_county.zip"
unzip tl_2023_55_county.zip
ogr2ogr \
  -f GeoJSON \
  -t_srs EPSG:4326 \
  -where "STATEFP='55'" \
  docs/data/counties.geojson \
  tl_2023_55_county.shp
```

Or use the [Census Cartographic Boundary Files](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html)
for a pre-simplified version that loads faster.

---

## GitHub Actions automation

The workflow in `.github/workflows/update-data.yml` runs weekly and:

1. Fetches the current ICE 287(g) participant list.
2. Parses any new reports in `reports/`.
3. Merges and writes updated JSONs.
4. Commits and pushes if files changed.

**Required:** The default `GITHUB_TOKEN` with `contents: write` permission
(already configured in the workflow). No additional secrets are needed
unless you add failure notifications.

---

## Contributing

- **Data corrections:** Open an issue with the county name, the incorrect
  value, and a source URL or document reference.
- **New report files:** Open a PR adding PDFs/CSVs to `reports/` and
  running the pipeline locally to verify output.
- **Code changes:** PRs welcome. Keep `docs/` as vanilla JS with no build
  step required.

---

## Licenses

- **Code** (`docs/js/`, `scripts/`, workflow): Mozilla Public License 2.0
  (see `LICENSE`).
- **Data** (`docs/data/`): Creative Commons Attribution 4.0 International
  (CC BY 4.0). Attribute as: *Wisconsin 287(g) & ICE Detainer Dashboard,
  wi287g, [year].*
- Source documents (ICE, ACLU-WI, BJS) retain their own licenses/terms.
