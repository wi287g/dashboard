"""
fetch_287g.py
=============
Fetches ICE's published list of active 287(g) Memoranda of Agreement (MOAs)
and extracts rows relevant to Wisconsin, emitting a normalized CSV for the
merge step.

Sources
-------
  - ICE 287(g) participant list (HTML table):
    https://www.ice.gov/identify-and-arrest/287g
  - Fallback: manually downloaded CSV placed at data/raw/287g_raw.csv

Output
------
  data/raw/287g_wi.csv
    Columns: fips, county_name, agency, model, effective_date, status

Usage
-----
  python scripts/fetch_287g.py [--out docs/data/raw/287g_wi.csv]

Dependencies
------------
  pip install requests beautifulsoup4 lxml

Notes
-----
  - ICE can change page structure or move PDFs without notice; add
    --force-cache to skip fetch and use a previously saved raw file.
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

import requests
from bs4 import BeautifulSoup

from wi_fips import WI_COUNTY_FIPS, normalize_county_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ICE_287G_URL = "https://www.ice.gov/identify-and-arrest/287g"
HEADERS = {
    "User-Agent": (
        "wi287g-dashboard/0.1 "
        "(public research; https://github.com/wi287g/dashboard)"
    )
}


def fetch_html(url: str, timeout: int = 30) -> str:
    log.info("Fetching %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_287g_table(html: str) -> list[dict]:
    """
    Parse the ICE 287(g) participant HTML table.

    The table structure may change; this targets the first <table> on the
    page. Adjust the selector if ICE redesigns the page.

    Returns list of dicts with keys:
        state, agency, model, effective_date, status
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        raise RuntimeError("Could not find a <table> on the ICE 287(g) page. "
                           "The page structure may have changed.")

    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    log.debug("Table headers: %s", headers)

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < len(headers):
            continue
        row = dict(zip(headers, cells))
        rows.append(row)

    log.info("Parsed %d rows from ICE table", len(rows))
    return rows


def filter_wisconsin(rows: list[dict]) -> list[dict]:
    """Keep only Wisconsin rows; normalize county name → FIPS."""
    wi_rows = []
    not_found = []

    for row in rows:
        state = row.get("state", "").strip().upper()
        if state not in ("WI", "WISCONSIN"):
            continue

        agency = row.get("agency", row.get("participating agency", "")).strip()
        model  = row.get("model", row.get("287(g) model", "")).strip()
        eff_dt = row.get("effective date", row.get("date", "")).strip()
        status = row.get("status", "active").strip().lower()

        county_norm = normalize_county_name(agency)
        fips = WI_COUNTY_FIPS.get(county_norm)
        if not fips:
            not_found.append(agency)
            log.warning("Could not resolve FIPS for agency: %s", agency)
            fips = ""

        wi_rows.append({
            "fips":           fips,
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
        help="Skip HTTP fetch; load from --cache-path instead.",
    )
    parser.add_argument(
        "--cache-path",
        default="docs/data/raw/287g_raw.html",
        help="Cached HTML file path for --force-cache.",
    )
    args = parser.parse_args(argv)

    if args.force_cache:
        cache = Path(args.cache_path)
        if not cache.exists():
            log.error("Cache file not found: %s", cache)
            sys.exit(1)
        html = cache.read_text(encoding="utf-8")
        log.info("Using cached HTML from %s", cache)
    else:
        try:
            html = fetch_html(ICE_287G_URL)
            # Save cache for debugging
            cache = Path(args.cache_path)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(html, encoding="utf-8")
        except Exception as exc:
            log.error("Fetch failed: %s", exc)
            # If cached version exists, fall back
            cache = Path(args.cache_path)
            if cache.exists():
                log.warning("Using stale cache: %s", cache)
                html = cache.read_text(encoding="utf-8")
            else:
                sys.exit(1)

    rows = parse_287g_table(html)
    wi_rows = filter_wisconsin(rows)
    write_csv(wi_rows, Path(args.out))


if __name__ == "__main__":
    main()
