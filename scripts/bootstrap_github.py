"""
bootstrap_github.py
===================
One-shot script that creates all milestones, labels, and issues for the
wi287g/dashboard repo via the GitHub REST API.

Simply run after fixing the PAT permissions (see README or instructions below).

Usage
-----
  # Token from .env (auto-loaded), or pass explicitly:
  python scripts/bootstrap_github.py

  # Dry run (print what would be created, make no requests):
  python scripts/bootstrap_github.py --dry-run

  # Skip issues already created (safe to re-run):
  python scripts/bootstrap_github.py --skip-existing

Requirements
------------
  No third-party packages needed — stdlib only (urllib, json).

PAT permissions required
------------------------
  Fine-grained PAT → wi287g/dashboard:
    - Issues: Read and Write
    - Contents: Read and Write  (for git push)
    - Pull requests: Read and Write  (optional, future use)
  Generate at: https://github.com/settings/tokens?type=beta
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

REPO  = "wi287g/dashboard"
BASE  = "https://api.github.com"

def _load_token() -> str:
    """Load GITHUB_PERSONAL_ACCESS_TOKEN from .env or environment."""
    # Environment variable takes priority
    tok = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    if tok:
        return tok
    # Try .env in repo root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GITHUB_PERSONAL_ACCESS_TOKEN=") and not line.startswith("#"):
                tok = line.split("=", 1)[1].strip()
                if tok:
                    return tok
    raise SystemExit(
        "ERROR: GITHUB_PERSONAL_ACCESS_TOKEN not found.\n"
        "Set it in .env or as an environment variable.\n"
        "Generate a fine-grained PAT at https://github.com/settings/tokens?type=beta\n"
        "Required permissions: Issues (read+write), Contents (read+write)"
    )

# ── GitHub API helpers ────────────────────────────────────────────────────────

def _request(method: str, path: str, payload: dict | None, token: str, dry_run: bool) -> dict | None:
    url = f"{BASE}{path}"
    if dry_run:
        print(f"  [DRY RUN] {method} {url}" + (f" → {payload}" if payload else ""))
        return {"id": 0, "number": 0, "name": "", "title": ""}
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url, method=method, data=data,
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type":         "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()) if r.status not in (204,) else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body).get("message", body)
        except Exception:
            msg = body[:200]
        if e.code == 422 and "already_exists" in body:
            return None  # Signal: already exists
        raise RuntimeError(f"GitHub API {method} {url} → {e.code}: {msg}") from e


def _get_all(path: str, token: str) -> list[dict]:
    results, page = [], 1
    sep = "&" if "?" in path else "?"
    while True:
        req = urllib.request.Request(
            f"{BASE}{path}{sep}per_page=100&page={page}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            batch = json.loads(r.read())
        if not batch:
            break
        results.extend(batch)
        page += 1
    return results

# ── Milestones ─────────────────────────────────────────────────────────────────

MILESTONES = [
    {"title": "M1 · Bootstrap",    "description": "Repo live, real geometry, placeholder data renders correctly on GitHub Pages."},
    {"title": "M2 · Real Data",    "description": "ICE 287(g) list and ACLU/SCAAP data ingested; all 72 counties have sourced statuses."},
    {"title": "M3 · Automation",   "description": "Weekly GitHub Actions pipeline running; failure notifications wired."},
    {"title": "M4 · Polish",       "description": "Year filter, accessibility audit, time-lapse slider, about panel expanded."},
    {"title": "M5 · Shipping",     "description": "SEO, discoverability, social preview, search console, outreach, API docs."},
]

def create_milestones(token: str, dry_run: bool) -> dict[str, int]:
    """Create milestones; return title → number map."""
    existing = {m["title"]: m["number"] for m in _get_all(f"/repos/{REPO}/milestones?state=all", token)} if not dry_run else {}
    result = {}
    for ms in MILESTONES:
        if ms["title"] in existing:
            print(f"  [skip] milestone already exists: {ms['title']}")
            result[ms["title"]] = existing[ms["title"]]
            continue
        r = _request("POST", f"/repos/{REPO}/milestones", ms, token, dry_run)
        num = (r or {}).get("number", 0)
        result[ms["title"]] = num
        print(f"  ✓ milestone: {ms['title']} (#{num})")
        time.sleep(0.3)
    return result

# ── Labels ─────────────────────────────────────────────────────────────────────

LABELS = [
    # Type
    {"name": "data",          "color": "0075ca", "description": "Data values, sources, or coverage"},
    {"name": "pipeline",      "color": "e4e669", "description": "Python scripts that fetch/parse/merge data"},
    {"name": "ux",            "color": "d93f0b", "description": "User experience and map/chart interaction"},
    {"name": "infra",         "color": "1d76db", "description": "GitHub Actions, Pages, deployment"},
    {"name": "automation",    "color": "0052cc", "description": "Scheduled workflows and CI"},
    {"name": "accessibility", "color": "7057ff", "description": "a11y: keyboard, screen reader, contrast"},
    {"name": "seo",           "color": "006b75", "description": "Search engine optimisation and discoverability"},
    {"name": "documentation", "color": "bfd4f2", "description": "README, methodology, data dictionary"},
    {"name": "testing",       "color": "bfe5bf", "description": "Tests and validation scripts"},
    {"name": "open-records",  "color": "f9d0c4", "description": "FOIA / Wisconsin open-records requests"},
    {"name": "shipping",      "color": "e3d76b", "description": "Launch, outreach, distribution"},
    # Flags
    {"name": "missing-data",  "color": "ee0701", "description": "County status or time-series data is unknown"},
    {"name": "good first issue", "color": "7fc97f", "description": "Great for newcomers"},
    {"name": "help wanted",   "color": "159818", "description": "Extra attention needed"},
    # Milestones (for quick filter)
    {"name": "M1-bootstrap",  "color": "c5def5", "description": "Milestone 1: Bootstrap"},
    {"name": "M2-real-data",  "color": "c5def5", "description": "Milestone 2: Real Data"},
    {"name": "M3-automation", "color": "c5def5", "description": "Milestone 3: Automation"},
    {"name": "M4-polish",     "color": "c5def5", "description": "Milestone 4: Polish"},
    {"name": "M5-shipping",   "color": "c5def5", "description": "Milestone 5: Shipping"},
]

def create_labels(token: str, dry_run: bool) -> None:
    existing = {lb["name"] for lb in _get_all(f"/repos/{REPO}/labels", token)} if not dry_run else set()
    for lb in LABELS:
        if lb["name"] in existing:
            # Update description/color in case it changed
            _request("PATCH", f"/repos/{REPO}/labels/{urllib.parse.quote(lb['name'])}", lb, token, dry_run)
            print(f"  [update] label: {lb['name']}")
        else:
            r = _request("POST", f"/repos/{REPO}/labels", lb, token, dry_run)
            if r is None:
                print(f"  [skip] label exists: {lb['name']}")
            else:
                print(f"  ✓ label: {lb['name']}")
        time.sleep(0.2)

# ── Issues ─────────────────────────────────────────────────────────────────────

def _issues(milestones: dict[str, int]) -> list[dict]:
    M = milestones  # shorthand

    return [
        # ── M1 Bootstrap ──────────────────────────────────────────────────────
        {
            "title":     "[DATA] Replace placeholder counties.geojson with real Census TIGER geometry",
            "labels":    ["data", "M1-bootstrap", "good first issue"],
            "milestone": M.get("M1 · Bootstrap"),
            "body": """\
The current `docs/data/counties.geojson` was fetched from Census TIGERweb REST API (72 counties, ~156 KB gzipped) but geometry may still be lower resolution than the cartographic boundary files.

**Tasks**
- [ ] Compare TIGERweb source against Census Cartographic Boundary Files (20m resolution) — CB files are pre-simplified and often preferred for choropleth maps
- [ ] If CB files look better: download `cb_2023_55_county_20m.zip` from https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
- [ ] Convert: `ogr2ogr -f GeoJSON -t_srs EPSG:4326 -select GEOID,NAME docs/data/counties.geojson cb_2023_55_county_20m.shp`
- [ ] Verify all 72 counties render and FIPS codes align with `287g_status.json`
- [ ] Check gzipped transfer size stays under 250 KB

**Current state:** TIGERweb data in place. 156 KB gzipped. All 72 counties present.
""",
        },
        {
            "title":     "[INFRA] Enable GitHub Pages and verify live deployment",
            "labels":    ["infra", "M1-bootstrap"],
            "milestone": M.get("M1 · Bootstrap"),
            "body": """\
**Steps**
1. GitHub → repo → **Settings** → **Pages**
2. Source: **Deploy from a branch** → branch `main` → folder `/docs` → **Save**
3. Wait ~60 s, confirm URL appears: `https://wi287g.github.io/dashboard/`
4. Open DevTools → Network: confirm all 4 JSON data files return **200**
5. Console: confirm no JS errors
6. Test on mobile viewport

**Custom domain (optional)**
- Settings → Pages → Custom domain: `wi287g.org`
- Add CNAME DNS record: `wi287g.org` → `wi287g.github.io`
- Create `docs/CNAME` file containing just: `wi287g.org`
- Tick **Enforce HTTPS** after propagation

**Repo social preview**
- Settings → Social preview → upload `docs/img/social-preview.png` (1200×630 px)
""",
        },
        {
            "title":     "[PIPELINE] Add pytest suite for wi_fips.py FIPS lookup",
            "labels":    ["pipeline", "testing", "M1-bootstrap", "good first issue"],
            "milestone": M.get("M1 · Bootstrap"),
            "body": """\
Add a `scripts/test_wi_fips.py` test file and wire it into the GitHub Actions workflow.

**Tasks**
- [ ] Create `scripts/test_wi_fips.py` using `unittest` or `pytest`
- [ ] Assert all 72 WI county FIPS codes are present in `WI_COUNTY_FIPS`
- [ ] Assert `normalize_county_name("Dane County Sheriff's Office")` → `"dane"`
- [ ] Assert `fips_from_raw("Milwaukee Co. Jail")` → `"55079"`
- [ ] Assert `fips_from_raw("St. Croix County")` → `"55109"`
- [ ] Add `python -m pytest scripts/test_wi_fips.py` step to `update-data.yml`

**Why:** Any regression in FIPS lookup causes silent data drops in the pipeline.
""",
        },

        # ── M2 Real Data ──────────────────────────────────────────────────────
        {
            "title":     "[DATA] Populate 287g_status.json from ICE MOA list",
            "labels":    ["data", "pipeline", "M2-real-data"],
            "milestone": M.get("M2 · Real Data"),
            "body": """\
Run `scripts/fetch_287g.py` to pull the live ICE 287(g) participant list and update `docs/data/287g_status.json`.

**Tasks**
- [ ] `pip install -r requirements.txt`
- [ ] `python scripts/fetch_287g.py` — check `docs/data/raw/287g_wi.csv` output
- [ ] Review WARN lines for FIPS lookup failures; update `scripts/wi_fips.py` aliases as needed
- [ ] `python scripts/merge_datasets.py` — review diff against current `287g_status.json`
- [ ] Manually verify 3–5 counties against the ICE list PDF directly
- [ ] Commit `docs/data/287g_status.json` with source attribution
- [ ] Open follow-up issues for any county where ICE list conflicts with local reports
""",
        },
        {
            "title":     "[DATA] Source and parse ACLU-WI detainer data",
            "labels":    ["data", "pipeline", "M2-real-data"],
            "milestone": M.get("M2 · Real Data"),
            "body": """\
Identify available ACLU-WI (or equivalent) reports for Wisconsin detainer counts by county and year.

**Tasks**
- [ ] Identify reports at https://www.aclu-wi.org — note years covered
- [ ] Download PDFs/CSVs into `reports/` (gitignored — also add to `reports/SOURCES.md`)
- [ ] `python scripts/parse_aclu_reports.py --input-dir reports/`
- [ ] Review WARN lines for column-name mismatches; update `DETAINER_COL_ALIASES` in `parse_aclu_reports.py`
- [ ] Confirm `docs/data/raw/aclu_detainers.csv` has reasonable values (spot-check 3 counties)
- [ ] Run merge step and verify `docs/data/detainers_by_county_year.json`

**Alternative sources if ACLU data is unavailable:**
- Wisconsin DOJ open-records request for jail bookings with ICE hold codes
- Transactional Records Access Clearinghouse (TRAC) at https://trac.syr.edu
""",
        },
        {
            "title":     "[DATA] Source and ingest BJS SCAAP payment data by county",
            "labels":    ["data", "pipeline", "M2-real-data"],
            "milestone": M.get("M2 · Real Data"),
            "body": """\
SCAAP awards are published annually by BJS. County-level breakdowns may require FOIA.

**Tasks**
- [ ] Check https://bjs.ojp.gov/programs/scaap for downloadable county-level tables
- [ ] If county-level available: format as `docs/data/raw/aclu_scaap.csv` (fips, county_name, year, amount)
- [ ] If only state-aggregate: document gap in `287g_status.json` notes + README known limitations
- [ ] File FOIA with DOJ/BJS if county-level not publicly posted
- [ ] Run merge step and verify `docs/data/scaap_by_county_year.json`

**Note:** SCAAP data typically lags 12–18 months. 2024 data may not be available until late 2025.
""",
        },
        {
            "title":     "[DATA] Add _generated_at and _data_version metadata to all JSON outputs",
            "labels":    ["data", "pipeline", "M2-real-data"],
            "milestone": M.get("M2 · Real Data"),
            "body": """\
Stamp every generated JSON with when it was built and a version string, for auditability and cache-busting.

**Tasks**
- [ ] In `scripts/merge_datasets.py`: add `_generated_at` (ISO 8601 UTC) and `_data_version` (date string `YYYYMMDD`) to all three output JSON dicts
- [ ] In `docs/js/main.js`: read `_generated_at` from status JSON (already wired to `#last-updated-label`) — confirm it works end-to-end
- [ ] Document versioning scheme in README under "Running the pipeline"
""",
        },

        # ── M3 Automation ─────────────────────────────────────────────────────
        {
            "title":     "[INFRA] Enable and test weekly GitHub Actions data pipeline",
            "labels":    ["infra", "automation", "M3-automation"],
            "milestone": M.get("M3 · Automation"),
            "body": """\
The `.github/workflows/update-data.yml` workflow is scaffolded but needs a live test.

**Tasks**
- [ ] Actions → "Update dashboard data" → **Run workflow** (manual trigger)
- [ ] Confirm all three pipeline steps succeed (or fail gracefully with stale-cache fallback)
- [ ] Confirm commit-and-push fires only when data changed
- [ ] Confirm GitHub Pages redeploys after the commit
- [ ] Review logs; fix any path or permission issues

**Required:** workflow needs `contents: write` permission — already set in `update-data.yml`.
""",
        },
        {
            "title":     "[INFRA] Add failure notification to GitHub Actions pipeline",
            "labels":    ["infra", "automation", "M3-automation"],
            "milestone": M.get("M3 · Automation"),
            "body": """\
If the automated pipeline fails, maintainers should be alerted without checking Actions manually.

**Options (choose one):**

**A — Email (zero config):**
Repo → Settings → Notifications → enable "Send email notifications for failed workflows."

**B — Slack:**
1. Create a `SLACK_WEBHOOK_URL` repo secret
2. Uncomment the `slackapi/slack-github-action` step in `update-data.yml`
3. Confirm a deliberate failure triggers the alert

**Tasks**
- [ ] Pick an option and implement
- [ ] Confirm alert fires on a deliberately broken run (e.g. bad URL for ICE fetch)
""",
        },
        {
            "title":     "[PIPELINE] Add --force-cache mode and local dev Makefile",
            "labels":    ["pipeline", "documentation", "M3-automation"],
            "milestone": M.get("M3 · Automation"),
            "body": """\
Prevent hammering ICE/ACLU servers during local development.

**Tasks**
- [ ] Verify `python scripts/fetch_287g.py --force-cache` works end-to-end (html already saved by first run)
- [ ] Add a `Makefile` (or `scripts/run_pipeline.sh`) with:
  - `make fetch` — live fetch, save cache
  - `make local` — `--force-cache` only (fast, no network)
  - `make merge` — run merge step
  - `make all` — full pipeline
- [ ] Document in README under "Running the pipeline locally"
""",
        },

        # ── M4 Polish ─────────────────────────────────────────────────────────
        {
            "title":     "[UX] Year filter — sidebar dropdown to recompute charts by year",
            "labels":    ["ux", "M4-polish"],
            "milestone": M.get("M4 · Polish"),
            "body": """\
Let users narrow charts to a specific year without reloading.

**Tasks**
- [ ] Add `<select id=\"year-filter\">` to sidebar or toolbar, populated from available years in loaded data
- [ ] On change, call `updateCharts(fips, ...)` with a filtered slice of time-series data
- [ ] Show "No data for selected year" message when series is empty (toggle `#no-chart-data`)
- [ ] Optional: update map choropleth shade intensity based on detainer rate for that year
""",
        },
        {
            "title":     "[UX] Time-lapse map slider — animate 287(g)/detainer spread by year",
            "labels":    ["ux", "M4-polish"],
            "milestone": M.get("M4 · Polish"),
            "body": """\
A year slider that animates county color changes over time — a powerful accountability and journalism tool.

**Tasks**
- [ ] Add `<input type=\"range\">` year slider to toolbar
- [ ] On change, re-color county layer based on detainer data for that year
- [ ] Add play/pause button to auto-advance slider (setTimeout loop)
- [ ] Add a snapshot permalink (`?year=2023`) so journalists can link to a specific year
- [ ] Ensure the slider year state is reflected in chart views too
""",
        },
        {
            "title":     "[ACCESSIBILITY] Keyboard navigation and color contrast audit",
            "labels":    ["accessibility", "M4-polish"],
            "milestone": M.get("M4 · Polish"),
            "body": """\
Make the dashboard usable for people who don't use a mouse or have color vision differences.

**Tasks**
- [ ] Verify all interactive elements (search, filter, map counties) are Tab + Enter/Space navigable
- [ ] Check color contrast ratios for status badge text — WCAG AA minimum 4.5:1
- [ ] Add `aria-label` and `role` where missing (map div, legend, charts canvas elements)
- [ ] Test with NVDA or VoiceOver — confirm county summary is announced on selection
- [ ] Add a high-contrast/pattern-fill option for colorblind users (replace red/orange with textures or icons)
- [ ] Run Lighthouse accessibility audit; target ≥ 90
""",
        },
        {
            "title":     "[UX] Expand About the data panel with methodology and contribution prompt",
            "labels":    ["ux", "documentation", "M4-polish"],
            "milestone": M.get("M4 · Polish"),
            "body": """\
Non-expert users need context on what statuses mean and how confident we are in the data.

**Tasks**
- [ ] Expand `.about-box` in sidebar:
  - Clarify: "Unknown ≠ cooperating" explicitly
  - Note data lag (SCAAP 12–18 months, ICE list updated irregularly)
  - Note that coverage is incomplete — open-records requests may be pending
  - Link to how-to guide for filing WI open-records requests
- [ ] Add "How to submit a correction" link → GitHub issue template
- [ ] Wrap in `<details>` element to keep sidebar compact by default
""",
        },
        {
            "title":     "[DATA] Document static JSON endpoints as a public API",
            "labels":    ["data", "documentation", "M4-polish"],
            "milestone": M.get("M4 · Polish"),
            "body": """\
The dashboard JSON files are already public static endpoints. Document them for downstream consumers (researchers, journalists, other tools).

**Tasks**
- [ ] Add "API / Data endpoints" section to README with:
  - URL pattern: `https://wi287g.github.io/dashboard/data/<file>.json`
  - Schema for each file (already documented in `_schema` keys within the JSON)
  - Note: GitHub Pages serves with permissive CORS by default — confirm no header changes needed
  - Note on `_data_version` for cache-busting
- [ ] Create `docs/api.md` with the same info, linked from footer
- [ ] Open issue or PR to list the dataset on a directory (see M5 issues)
""",
        },

        # ── M5 Shipping ───────────────────────────────────────────────────────
        {
            "title":     "[SEO] Create social preview image (og:image / twitter:image)",
            "labels":    ["seo", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
Every link share on social media shows no preview image until this is created.

**Spec**
- Size: **1200 × 630 px** PNG (og:image standard)
- File path: `docs/img/social-preview.png`
- Already referenced in `index.html`

**Suggested content**
Screenshot of the dashboard map with county colors visible + title text overlay:
`"Wisconsin 287(g) & ICE Detainer Dashboard — wi287g.github.io/dashboard"`

**Also needed for `docs/img/`**
- `favicon.png` — 32×32 px PNG (export from `favicon.svg`)
- `apple-touch-icon.png` — 180×180 px (iOS home screen)

**Tooling**
Figma (free), GIMP, Canva, or screenshot + annotate in any image editor.

Once created, also upload to: **repo → Settings → Social preview** (separate from og:image — controls what GitHub shows when the _repo_ link is shared).
""",
        },
        {
            "title":     "[SEO] Submit to Google Search Console and request indexing",
            "labels":    ["seo", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
Get the site crawled and indexed as fast as possible.

**Tasks**
- [ ] Go to https://search.google.com/search-console → Add property → URL prefix → `https://wi287g.github.io/dashboard/`
- [ ] Verify ownership via HTML tag method: add `<meta name="google-site-verification" content="...">` to `index.html` `<head>`
- [ ] Submit sitemap: Sitemaps → enter `https://wi287g.github.io/dashboard/sitemap.xml`
- [ ] Use URL Inspection tool on the homepage URL → Request Indexing
- [ ] Check back in 48–72 hours for indexing status

**Note:** The JSON-LD Dataset schema in `index.html` makes the site eligible for [Google Dataset Search](https://datasetsearch.research.google.com/) — a high-value discovery channel for journalists and researchers.
""",
        },
        {
            "title":     "[SEO] Add GitHub repo topics and polish the About section",
            "labels":    ["seo", "infra", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
The GitHub repo page itself ranks in search. Topics are indexed by both GitHub search and external search engines.

**Tasks**
- [ ] Repo → **About** (gear icon top-right of repo): add a one-line description
  e.g. "Interactive county-level map of ICE 287(g) agreements, detainer compliance, and SCAAP payments in Wisconsin."
- [ ] Add topics: `287g` `ice` `immigration` `immigration-enforcement` `wisconsin` `open-data` `leaflet` `data-journalism` `public-records`
- [ ] Set website: `https://wi287g.github.io/dashboard/`
- [ ] Confirm README renders well on GitHub (images, tables, code blocks)
""",
        },
        {
            "title":     "[SHIPPING] Register dataset on Hugging Face and/or data.gov",
            "labels":    ["shipping", "data", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
The JSON files are public static endpoints usable as a dataset. Listing on data directories dramatically increases research-community reach.

**Options (do one or all)**

**Hugging Face Datasets**
- Create an account; upload a dataset card pointing to the JSON endpoints
- URL: https://huggingface.co/new-dataset
- The dataset card markdown should describe schema, source, update frequency, license (CC BY 4.0)

**Data.gov**
- Requires a US government or affiliated organization account — may not apply here
- Alternative: include in the **Open Data Network** or **CKAN** instances that harvest GitHub

**Socrata / other state portals**
- Check if Wisconsin has an open data portal and whether this qualifies for listing

**Tasks**
- [ ] Determine which platform(s) are viable
- [ ] Create/submit listing with schema, description, and endpoint URLs
- [ ] Link from README "Data sources" section
""",
        },
        {
            "title":     "[SHIPPING] Outreach — journalists, researchers, advocacy orgs",
            "labels":    ["shipping", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
Distribution strategy for the dashboard launch.

**Primary targets**
- [ ] ACLU-WI — contact about data collaboration + share dashboard link
- [ ] Wisconsin Watch (investigative journalism nonprofit)
- [ ] Milwaukee Journal Sentinel data/investigations desk
- [ ] UW-Madison law or immigration clinic researchers
- [ ] Voces de la Frontera (immigrant rights org, WI)
- [ ] Local journalists covering immigration or sheriff races in key counties (Brown, Kenosha, Waukesha, Racine)

**Social / community**
- [ ] Post to Mastodon (data journalism, journalism, immigration hashtags)
- [ ] Post to relevant subreddits: r/wisconsin, r/dataisbeautiful, r/ImmigrationNews
- [ ] Submit to Data Is Plural newsletter (https://www.data-is-plural.com/survey/)
- [ ] Submit to Source (OpenNews): https://source.opennews.org/articles/

**Framing for outreach**
"We built a free, county-level dashboard showing which Wisconsin sheriffs cooperate with ICE — including 287(g) agreements, detainer counts, and how much federal money they received. Data is public record and updated automatically."
""",
        },
        {
            "title":     "[SHIPPING] Enable GitHub Discussions for community Q&A",
            "labels":    ["shipping", "infra", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
GitHub Discussions is friendlier for non-technical contributors (journalists, lawyers, researchers, residents) than Issues, which has a "bug report" connotation.

**Tasks**
- [ ] Repo → Settings → Features → tick **Discussions**
- [ ] Create categories:
  - 📣 Announcements (locked, maintainer-only)
  - 🙋 Q&A (county data questions, source questions)
  - 📊 Data contributions (share new PDFs, open-records responses)
  - 💡 Ideas (feature suggestions from non-technical contributors)
- [ ] Pin a welcome post explaining what the dashboard is and how to contribute data
- [ ] Link to Discussions from the dashboard's "About" sidebar section
""",
        },
        {
            "title":     "[SHIPPING] PAT fix — grant Contents:Write and Issues:Write permissions",
            "labels":    ["infra", "M5-shipping"],
            "milestone": M.get("M5 · Shipping"),
            "body": """\
The current fine-grained PAT in `.env` is **read-only** — it cannot push code or create issues via API.

**Fix (takes 2 minutes)**
1. Go to https://github.com/settings/tokens?type=beta
2. Find the token for `wi287g/dashboard` (or create a new one)
3. Edit → Repository access: `wi287g/dashboard`
4. Under **Permissions**, set:
   - **Contents**: Read and write (enables `git push`)
   - **Issues**: Read and write (enables milestone/label/issue creation via API)
   - **Pull requests**: Read and write (optional, for future PR automation)
5. **Generate token** → copy the new value → update `.env`

**After fixing**
```bash
python scripts/bootstrap_github.py   # creates all milestones, labels, issues
git push origin main                  # ships the code
```

**Note:** Keep `.env` in `.gitignore` (it already is). Never commit the token.
""",
        },
    ]

# ── Main ───────────────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="Bootstrap GitHub milestones, labels, and issues.")
    parser.add_argument("--dry-run",       action="store_true", help="Print what would happen; make no API calls.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip issues whose title already exists (default: always skips).")
    parser.add_argument("--milestones-only", action="store_true")
    parser.add_argument("--labels-only",     action="store_true")
    parser.add_argument("--issues-only",     action="store_true")
    args = parser.parse_args(argv)

    token = _load_token()

    run_all = not (args.milestones_only or args.labels_only or args.issues_only)

    # 1. Milestones
    if run_all or args.milestones_only:
        print("\n── Milestones ────────────────────────────────────")
        milestone_map = create_milestones(token, args.dry_run)
    else:
        # Still need the map for issue creation
        existing_ms = _get_all(f"/repos/{REPO}/milestones?state=all", token) if not args.dry_run else []
        milestone_map = {m["title"]: m["number"] for m in existing_ms}

    # 2. Labels
    if run_all or args.labels_only:
        print("\n── Labels ────────────────────────────────────────")
        create_labels(token, args.dry_run)

    # 3. Issues
    if run_all or args.issues_only:
        print("\n── Issues ────────────────────────────────────────")
        existing_titles = set()
        if not args.dry_run:
            existing_issues = _get_all(f"/repos/{REPO}/issues?state=all", token)
            existing_titles = {i["title"] for i in existing_issues}

        issues = _issues(milestone_map)
        created = skipped = 0
        for issue in issues:
            if issue["title"] in existing_titles:
                print(f"  [skip] #{issue['title'][:70]}")
                skipped += 1
                continue
            payload = {
                "title":  issue["title"],
                "body":   issue.get("body", ""),
                "labels": issue.get("labels", []),
            }
            if issue.get("milestone"):
                payload["milestone"] = issue["milestone"]
            r = _request("POST", f"/repos/{REPO}/issues", payload, token, args.dry_run)
            if r:
                num = (r or {}).get("number", "?")
                print(f"  ✓ #{num}: {issue['title'][:70]}")
                created += 1
            time.sleep(0.5)  # be polite to the API

        print(f"\nDone. Created: {created} | Skipped (existing): {skipped}")

    print("\n✓ Bootstrap complete.")
    if not args.dry_run:
        print(f"  View issues:     https://github.com/{REPO}/issues")
        print(f"  View milestones: https://github.com/{REPO}/milestones")


if __name__ == "__main__":
    main()
