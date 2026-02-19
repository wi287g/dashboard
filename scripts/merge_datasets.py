"""
merge_datasets.py
=================
Joins ICE 287(g) data and ACLU/SCAAP parsed CSVs into the final JSON files
consumed by the dashboard.

Inputs (all under docs/data/raw/)
----------------------------------
  287g_wi.csv         — from fetch_287g.py
  aclu_detainers.csv  — from parse_aclu_reports.py
  aclu_scaap.csv      — from parse_aclu_reports.py

Additionally reads existing docs/data/287g_status.json so that manual
annotations (notes, sources, last_updated overrides) are preserved.

Outputs (under docs/data/)
--------------------------
  287g_status.json            — cooperation status keyed by FIPS
  detainers_by_county_year.json
  scaap_by_county_year.json

Cooperation classification logic
---------------------------------
  1. If FIPS appears in 287g_wi.csv with status="active"  → "287g"
  2. Else if FIPS has any detainer records                 → "detainers"
  3. Else if FIPS is in the status file as "none"          → "none"
  4. Else                                                  → "unknown"

Usage
-----
  python scripts/merge_datasets.py [--dry-run] [--year-min 2018] [--year-max 2024]

Dependencies
------------
  pip install pandas

Notes
-----
  - Idempotent: safe to run repeatedly.
  - Preserves existing manual `notes` and `sources` entries from the
    current docs/data/287g_status.json.
  - Prints a summary diff of changed FIPS statuses at the end.
"""

import argparse
import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from wi_fips import WI_COUNTY_FIPS, FIPS_WI_COUNTY

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT       = Path(__file__).parent.parent
DOCS_DATA  = ROOT / "docs" / "data"
RAW        = DOCS_DATA / "raw"

STATUS_OUT   = DOCS_DATA / "287g_status.json"
DET_OUT      = DOCS_DATA / "detainers_by_county_year.json"
SCAAP_OUT    = DOCS_DATA / "scaap_by_county_year.json"

RAW_287G     = RAW / "287g_wi.csv"
RAW_DET      = RAW / "aclu_detainers.csv"
RAW_SCAAP    = RAW / "aclu_scaap.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_csv_or_empty(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        log.warning("Raw file not found: %s — treating as empty.", path)
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, **kwargs)


def _load_existing_status() -> dict:
    if STATUS_OUT.exists():
        with STATUS_OUT.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _write_json(obj: dict | list, path: Path, dry_run: bool) -> None:
    payload = json.dumps(obj, indent=2, ensure_ascii=False)
    if dry_run:
        log.info("[DRY RUN] Would write %d chars → %s", len(payload), path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    log.info("Wrote → %s", path)


# ── Core logic ────────────────────────────────────────────────────────────────

def build_status(
    df_287g: pd.DataFrame,
    df_det:  pd.DataFrame,
    existing: dict,
    today: str,
) -> dict:
    """
    Build the 287g_status.json dict.

    Preserves existing manual fields (notes, sources with non-placeholder
    values) from the current status file.
    """
    status: dict[str, dict] = {}

    # Active 287(g) FIPS
    active_287g_fips: set[str] = set()
    if not df_287g.empty and "fips" in df_287g.columns:
        mask = df_287g.get("status", pd.Series(dtype=str)).str.lower().isin(
            ["active", ""]
        )
        active_287g_fips = set(df_287g.loc[mask, "fips"].dropna())

    # FIPS with any detainer record
    fips_with_detainers: set[str] = set()
    if not df_det.empty and "fips" in df_det.columns:
        fips_with_detainers = set(df_det["fips"].dropna())

    for fips in sorted(WI_COUNTY_FIPS.values()):
        prev  = existing.get(fips, {})
        coop  = prev.get("cooperation", "unknown")

        # Determine cooperation from raw data
        if fips in active_287g_fips:
            coop = "287g"
        elif fips in fips_with_detainers:
            if coop not in ("none", "287g"):
                coop = "detainers"
        # "none" and "287g" from existing manual classification are preserved

        # Preserve non-placeholder sources; append pipeline source
        prev_sources = [
            s for s in (prev.get("sources") or []) if s != "placeholder"
        ]
        new_sources = []
        if fips in active_287g_fips:
            new_sources.append("ICE 287(g) MOA list (automated fetch)")
        if fips in fips_with_detainers:
            new_sources.append("ACLU-WI report (parsed)")
        sources = list(dict.fromkeys(prev_sources + new_sources)) or ["pipeline — awaiting source data"]

        entry: dict = {
            "cooperation":  coop,
            "last_updated": today,
            "sources":      sources,
        }

        # Preserve manual notes
        if prev.get("notes"):
            entry["notes"] = prev["notes"]

        status[fips] = entry

    # Preserve top-level metadata
    status["_note"] = (
        "Generated by scripts/merge_datasets.py. "
        "Manual annotations preserved. Last run: " + today
    )
    return status


def build_timeseries(df: pd.DataFrame, value_col: str, year_min: int, year_max: int) -> dict:
    """
    Build a FIPS-keyed dict of year/value arrays.

    value_col is "count" (detainers) or "amount" (SCAAP).
    """
    if df.empty or "fips" not in df.columns:
        return {}

    result: dict[str, list] = {}
    df = df.copy()
    df["year"]       = pd.to_numeric(df.get("year", pd.Series()), errors="coerce")
    df[value_col]    = pd.to_numeric(df.get(value_col, pd.Series()), errors="coerce").fillna(0)
    df = df.dropna(subset=["fips", "year"])
    df = df[(df["year"] >= year_min) & (df["year"] <= year_max)]

    for fips, group in df.groupby("fips"):
        agg = (
            group.groupby("year")[value_col]
            .sum()
            .reset_index()
            .sort_values("year")
        )
        result[fips] = [
            {
                "year":     int(r["year"]),
                value_col:  round(float(r[value_col]), 2),
            }
            for _, r in agg.iterrows()
        ]

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge pipeline data → dashboard JSONs.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing.")
    parser.add_argument("--year-min", type=int, default=2018)
    parser.add_argument("--year-max", type=int, default=date.today().year)
    args = parser.parse_args(argv)

    today    = str(date.today())
    existing = _load_existing_status()

    df_287g  = _load_csv_or_empty(RAW_287G)
    df_det   = _load_csv_or_empty(RAW_DET)
    df_scaap = _load_csv_or_empty(RAW_SCAAP)

    # Build outputs
    status   = build_status(df_287g, df_det, existing, today)
    det_ts   = build_timeseries(df_det,   "count",  args.year_min, args.year_max)
    scaap_ts = build_timeseries(df_scaap, "amount", args.year_min, args.year_max)

    # Diff summary
    changed = []
    for fips, entry in status.items():
        if fips.startswith("_"):
            continue
        prev_coop = (existing.get(fips) or {}).get("cooperation", "unknown")
        new_coop  = entry["cooperation"]
        if prev_coop != new_coop:
            name = FIPS_WI_COUNTY.get(fips, fips)
            changed.append(f"  {fips} ({name}): {prev_coop} → {new_coop}")

    if changed:
        log.info("Status changes (%d):\n%s", len(changed), "\n".join(changed))
    else:
        log.info("No status changes detected.")

    _write_json(status,   STATUS_OUT,  args.dry_run)
    _write_json(det_ts,   DET_OUT,     args.dry_run)
    _write_json(scaap_ts, SCAAP_OUT,   args.dry_run)

    log.info("Done. Run scripts: fetch_287g.py → parse_aclu_reports.py → merge_datasets.py")


if __name__ == "__main__":
    main()
