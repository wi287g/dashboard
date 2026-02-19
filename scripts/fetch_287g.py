"""
fetch_287g.py
=============
Fetches ICE's published list of active 287(g) Memoranda of Agreement (MOAs)
and extracts rows relevant to Wisconsin, emitting a normalized CSV for the
merge step.

Sources
-------
  - ICE 287(g) participant list (XLSX, discovered via the ICE page):
    https://www.ice.gov/identify-and-arrest/287g
    The page links to a file like:
      /doclib/about/offices/ero/287g/participatingAgencies<date>.xlsx
  - Fallback: manually downloaded XLSX placed at docs/data/raw/287g_raw.xlsx

Output
------
  docs/data/raw/287g_wi.csv
    Columns: fips, county_name, agency, model, effective_date, status

Usage
-----
  python scripts/fetch_287g.py [--out docs/data/raw/287g_wi.csv]
  python scripts/fetch_287g.py --force-cache   # re-parse cached XLSX, no HTTP

Dependencies
------------
  pip install requests beautifulsoup4 lxml pandas openpyxl

Notes
-----
  - ICE can change page structure without notice. The script searches the page
    HTML for any .xlsx link matching 'participatingAgencies', then downloads it.
  - Use --force-cache to skip the HTTP fetch and reparse the saved XLSX.
  - FIPS look-up uses the WI county name → FIPS map in scripts/wi_fips.py.
  - Run idempotently; overwrites output each time.
"""

import argparse
import csv
import json
import logging
import sys
from datetime import date
from pathlib import Path

import re

import requests
from bs4 import BeautifulSoup
import pandas as pd

from wi_fips import WI_COUNTY_FIPS, normalize_county_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ICE_287G_URL = "https://www.ice.gov/identify-and-arrest/287g"
ICE_BASE_URL = "https://www.ice.gov"
HEADERS = {
    "User-Agent": (
        "wi287g-dashboard/0.1 "
        "(public research; https://github.com/wi287g/dashboard)"
    )
}
# Column name aliases: keys are lowercase normalised; values are canonical names
COL_ALIASES = {
    "state":            ["state"],
    "agency":           ["law enforcement agency", "agency", "participating agency", "lea"],
    "county":           ["county"],
    "model":            ["support type", "model", "287(g) model", "program model", "moa type"],
    "effective_date":   ["signed", "effective date", "date", "moa effective date"],
    "status":           ["status", "active"],
}


def fetch_html(url: str, timeout: int = 30) -> str:
    log.info("Fetching %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def find_xlsx_url(html: str) -> str | None:
    """Search page HTML for a participatingAgencies*.xlsx link."""
    soup = BeautifulSoup(html, "lxml")
    pattern = re.compile(r'participatingAgencies.*?\.xlsx', re.I)
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if pattern.search(href):
            if href.startswith("http"):
                return href
            return ICE_BASE_URL + href
    # Fallback: regex directly on raw HTML (handles JS-rendered or escaped hrefs)
    match = re.search(r'["\']([^"\']*participatingAgencies[^"\']*\.xlsx)["\']', html, re.I)
    if match:
        path = match.group(1)
        return path if path.startswith("http") else ICE_BASE_URL + path
    return None


def download_xlsx(url: str, dest: Path, timeout: int = 60) -> None:
    log.info("Downloading XLSX: %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=65536):
            fh.write(chunk)
    log.info("Saved XLSX → %s (%d KB)", dest, dest.stat().st_size // 1024)


def _resolve_col(df_cols_lower: dict[str, str], canonical: str) -> str | None:
    """Return the actual DataFrame column name for a canonical field."""
    for alias in COL_ALIASES.get(canonical, [canonical]):
        if alias in df_cols_lower:
            return df_cols_lower[alias]
    return None


def parse_xlsx(xlsx_path: Path) -> list[dict]:
    """Parse the ICE participating-agencies XLSX into a list of row dicts."""
    df = pd.read_excel(xlsx_path, engine="openpyxl", dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    log.debug("XLSX columns: %s", list(df.columns))

    # Build lower-case → real-name map for flexible column lookup
    cols_lower = {c.lower(): c for c in df.columns}

    state_col   = _resolve_col(cols_lower, "state")
    agency_col  = _resolve_col(cols_lower, "agency")
    county_col  = _resolve_col(cols_lower, "county")
    model_col   = _resolve_col(cols_lower, "model")
    eff_col     = _resolve_col(cols_lower, "effective_date")
    status_col  = _resolve_col(cols_lower, "status")

    if not state_col:
        log.warning("Could not find 'state' column. Available: %s", list(df.columns))
    if not agency_col:
        log.warning("Could not find 'agency' column. Available: %s", list(df.columns))

    rows = []
    for _, r in df.iterrows():
        row = {
            "state":          str(r[state_col]).strip()  if state_col  else "",
            "agency":         str(r[agency_col]).strip() if agency_col else "",
            "county_field":   str(r[county_col]).strip() if county_col else "",
            "model":          str(r[model_col]).strip()  if model_col  else "",
            "effective_date": str(r[eff_col]).strip()    if eff_col    else "",
            "status":         str(r[status_col]).strip() if status_col else "active",
        }
        rows.append(row)

    log.info("Parsed %d rows from XLSX", len(rows))
    return rows


def filter_wisconsin(rows: list[dict]) -> list[dict]:
    """Keep only Wisconsin rows; normalize county name → FIPS."""
    wi_rows = []
    not_found = []

    for row in rows:
        state = row.get("state", "").strip().upper()
        if state not in ("WI", "WISCONSIN"):
            continue

        agency  = row.get("agency", "").strip()
        model   = row.get("model", "").strip()
        eff_dt  = row.get("effective_date", "").strip()
        # Normalise "2025-01-01 00:00:00" → "2025-01-01"
        if " " in eff_dt:
            eff_dt = eff_dt.split(" ")[0]
        status  = row.get("status", "active").strip().lower()
        if not status or status == "nan":
            status = "active"

        # Prefer COUNTY field for FIPS lookup; fall back to agency name
        county_raw = row.get("county_field", "").strip()
        county_norm = normalize_county_name(county_raw) if county_raw and county_raw != "nan" \
                      else normalize_county_name(agency)
        fips = WI_COUNTY_FIPS.get(county_norm)
        if not fips:
            # Second attempt: try agency name directly
            fips = WI_COUNTY_FIPS.get(normalize_county_name(agency))
        if not fips:
            not_found.append(f"{agency} (county_field={county_raw!r})")
            log.warning("Could not resolve FIPS for agency: %s", agency)

        wi_rows.append({
            "fips":           fips or "",
            "county_name":    county_norm,
            "agency":         agency,
            "model":          model,
            "effective_date": eff_dt,
            "status":         status,
            "fetched_date":   str(date.today()),
        })

    if not_found:
        log.warning(
            "FIPS lookup failed for %d agencies: %s. "
            "Update wi_fips.py or the county-name mapping.",
            len(not_found), not_found,
        )

    log.info("Found %d Wisconsin 287(g) entries", len(wi_rows))
    return wi_rows


def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        log.warning("No rows to write; output file will be empty.")
        out_path.write_text("")
        return

    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows → %s", len(rows), out_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch ICE 287(g) WI data.")
    parser.add_argument(
        "--out",
        default="docs/data/raw/287g_wi.csv",
        help="Output CSV path (default: docs/data/raw/287g_wi.csv)",
    )
    parser.add_argument(
        "--force-cache",
        action="store_true",
        help="Skip HTTP fetch; reparse the cached XLSX file.",
    )
    parser.add_argument(
        "--xlsx-cache",
        default="docs/data/raw/287g_raw.xlsx",
        help="Cached XLSX path (written on fetch, read when --force-cache).",
    )
    parser.add_argument(
        "--html-cache",
        default="docs/data/raw/ice_287g_raw.html",
        help="Cached HTML of the ICE 287(g) page (written on fetch).",
    )
    args = parser.parse_args(argv)

    xlsx_cache = Path(args.xlsx_cache)

    if args.force_cache:
        if not xlsx_cache.exists():
            log.error("XLSX cache not found: %s — run without --force-cache first.", xlsx_cache)
            sys.exit(1)
        log.info("--force-cache: reusing %s", xlsx_cache)
    else:
        # 1. Fetch the ICE page (use saved HTML cache if it exists)
        html_cache = Path(args.html_cache)
        if html_cache.exists():
            log.info("Using existing HTML cache: %s", html_cache)
            html = html_cache.read_text(encoding="utf-8")
        else:
            try:
                html = fetch_html(ICE_287G_URL)
                html_cache.parent.mkdir(parents=True, exist_ok=True)
                html_cache.write_text(html, encoding="utf-8")
            except Exception as exc:
                log.error("Page fetch failed: %s", exc)
                sys.exit(1)

        # 2. Find and download the participating-agencies XLSX
        xlsx_url = find_xlsx_url(html)
        if not xlsx_url:
            log.error(
                "Could not find a participatingAgencies*.xlsx link on the ICE page.\n"
                "The page may have changed. Check %s and update find_xlsx_url().",
                ICE_287G_URL,
            )
            sys.exit(1)

        try:
            download_xlsx(xlsx_url, xlsx_cache)
        except Exception as exc:
            if xlsx_cache.exists():
                log.warning("XLSX download failed (%s); falling back to cached %s", exc, xlsx_cache)
            else:
                log.error("XLSX download failed and no cache exists: %s", exc)
                sys.exit(1)

    rows = parse_xlsx(xlsx_cache)
    wi_rows = filter_wisconsin(rows)
    write_csv(wi_rows, Path(args.out))


if __name__ == "__main__":
    main()
