"""
parse_aclu_reports.py
=====================
Parse ACLU-WI (or similar watchdog) reports for Wisconsin county-level
detainer counts and SCAAP payment data. Emits CSVs for the merge step.

Supported input formats
-----------------------
  1. CSV (preferred): Reports already exported as spreadsheets.
  2. PDF: Tables extracted via pdfplumber. May need manual column-name
     adjustment if report layout changes between years.

Output
------
  docs/data/raw/aclu_detainers.csv
    Columns: fips, county_name, year, count

  docs/data/raw/aclu_scaap.csv
    Columns: fips, county_name, year, amount

Usage
-----
  # Parse a specific PDF
  python scripts/parse_aclu_reports.py --input reports/aclu_wi_2024.pdf --year 2024

  # Parse a CSV directly
  python scripts/parse_aclu_reports.py --input reports/aclu_wi_2023.csv --year 2023

  # Parse all files in a directory
  python scripts/parse_aclu_reports.py --input-dir reports/

Dependencies
------------
  pip install pdfplumber pandas

Notes
-----
  - Column names in ACLU reports are not guaranteed stable across years.
    See COLUMN_ALIASES below to add mappings for new layouts.
  - SCAAP payment source is separately BJS / DOJ; the ACLU may or may not
    include it. See scripts/fetch_scaap.py for direct BJS data.
"""

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

import pdfplumber
import pandas as pd

from wi_fips import fips_from_raw

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Column name aliases ────────────────────────────────────────────────────────
# Maps raw column names (lower-cased) found in reports → canonical name.
# Add new mappings here when report layouts change.

DETAINER_COL_ALIASES: dict[str, str] = {
    "detainers":              "count",
    "ice detainers":          "count",
    "detainer requests":      "count",
    "# detainers":            "count",
    "total detainers":        "count",
    "detainer count":         "count",
}

SCAAP_COL_ALIASES: dict[str, str] = {
    "scaap":                  "amount",
    "scaap award":            "amount",
    "scaap payment":          "amount",
    "scaap payments":         "amount",
    "scaap amount":           "amount",
    "federal scaap":          "amount",
    "reimbursement":          "amount",
}

COUNTY_COL_ALIASES: dict[str, str] = {
    "county":                 "county",
    "county name":            "county",
    "sheriff":                "county",
    "agency":                 "county",
    "jail":                   "county",
}


# ── PDF parsing ───────────────────────────────────────────────────────────────

def extract_tables_from_pdf(pdf_path: Path) -> list[pd.DataFrame]:
    """Extract all tables from a PDF, return as list of DataFrames."""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            raw = page.extract_tables()
            for tbl in raw:
                if not tbl or len(tbl) < 2:
                    continue
                df = pd.DataFrame(tbl[1:], columns=tbl[0])
                df.columns = [str(c).strip().lower() for c in df.columns]
                tables.append(df)
                log.debug("Page %d: table with columns %s", page_num, list(df.columns))
    log.info("Extracted %d tables from %s", len(tables), pdf_path.name)
    return tables


# ── Column resolution ─────────────────────────────────────────────────────────

def _resolve_col(df: pd.DataFrame, aliases: dict[str, str]) -> str | None:
    for col in df.columns:
        target = aliases.get(col.lower().strip())
        if target:
            return col
    return None


# ── Parsing logic ─────────────────────────────────────────────────────────────

def parse_dataframe(df: pd.DataFrame, year: int) -> tuple[list[dict], list[dict]]:
    """
    Given a DataFrame (from CSV or PDF table), extract detainer and SCAAP rows.

    Returns (detainer_rows, scaap_rows) — either list may be empty.
    """
    detainer_rows: list[dict] = []
    scaap_rows: list[dict]    = []

    county_col   = _resolve_col(df, COUNTY_COL_ALIASES)
    detainer_col = _resolve_col(df, DETAINER_COL_ALIASES)
    scaap_col    = _resolve_col(df, SCAAP_COL_ALIASES)

    if not county_col:
        log.warning("Could not find county column in DataFrame. "
                    "Columns: %s. Update COUNTY_COL_ALIASES.", list(df.columns))
        return [], []

    for _, row in df.iterrows():
        raw_county = str(row[county_col]).strip()
        if not raw_county or raw_county.lower() in ("county", "total", "nan", ""):
            continue

        fips = fips_from_raw(raw_county)
        if not fips:
            log.warning("FIPS not found for: %r", raw_county)
            continue

        base = {"fips": fips, "county_name": raw_county, "year": year}

        if detainer_col:
            try:
                count = int(re.sub(r"[^\d]", "", str(row[detainer_col])) or 0)
                detainer_rows.append({**base, "count": count})
            except (ValueError, TypeError):
                log.debug("Could not parse detainer value for %s: %r", raw_county, row.get(detainer_col))

        if scaap_col:
            try:
                amount = float(re.sub(r"[^\d.]", "", str(row[scaap_col])) or 0)
                scaap_rows.append({**base, "amount": amount})
            except (ValueError, TypeError):
                log.debug("Could not parse SCAAP value for %s: %r", raw_county, row.get(scaap_col))

    return detainer_rows, scaap_rows


def load_input(path: Path, year: int) -> tuple[list[dict], list[dict]]:
    """Load a single CSV or PDF input file."""
    if path.suffix.lower() == ".pdf":
        tables = extract_tables_from_pdf(path)
        all_det, all_scaap = [], []
        for df in tables:
            det, scaap = parse_dataframe(df, year)
            all_det.extend(det)
            all_scaap.extend(scaap)
        return all_det, all_scaap
    else:
        df = pd.read_csv(path, dtype=str)
        df.columns = [c.strip().lower() for c in df.columns]
        return parse_dataframe(df, year)


def write_csv(rows: list[dict], out_path: Path, fieldnames: list[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows → %s", len(rows), out_path)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="Parse ACLU-WI report files.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Single PDF or CSV report file.")
    group.add_argument("--input-dir", help="Directory of report files (PDF/CSV).")

    parser.add_argument(
        "--year", type=int, default=None,
        help="Year for the data (required if not inferrable from filename)."
    )
    parser.add_argument(
        "--det-out", default="docs/data/raw/aclu_detainers.csv",
        help="Output path for detainer CSV."
    )
    parser.add_argument(
        "--scaap-out", default="docs/data/raw/aclu_scaap.csv",
        help="Output path for SCAAP CSV."
    )
    args = parser.parse_args(argv)

    all_det, all_scaap = [], []

    def _year_from_filename(p: Path) -> int | None:
        m = re.search(r"(20\d{2})", p.stem)
        return int(m.group(1)) if m else None

    if args.input:
        input_path = Path(args.input)
        year = args.year or _year_from_filename(input_path)
        if not year:
            log.error("Cannot infer year from %s; pass --year.", input_path.name)
            sys.exit(1)
        det, scaap = load_input(input_path, year)
        all_det.extend(det)
        all_scaap.extend(scaap)
    else:
        input_dir = Path(args.input_dir)
        for p in sorted(input_dir.glob("*")):
            if p.suffix.lower() not in (".pdf", ".csv"):
                continue
            year = args.year or _year_from_filename(p)
            if not year:
                log.warning("Skipping %s — cannot infer year; pass --year or embed year in filename.", p.name)
                continue
            det, scaap = load_input(p, year)
            all_det.extend(det)
            all_scaap.extend(scaap)

    write_csv(all_det,   Path(args.det_out),   ["fips", "county_name", "year", "count"])
    write_csv(all_scaap, Path(args.scaap_out),  ["fips", "county_name", "year", "amount"])


if __name__ == "__main__":
    main()
