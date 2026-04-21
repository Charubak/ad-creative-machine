"""
Parses uploaded performance CSVs from ad platforms.
Normalises columns to the internal schema. Column mapping is saved per platform.
"""
import csv
import io
import json
import os
from pathlib import Path

PLATFORM_COLUMN_DEFAULTS = {
    "meta": {
        "impressions": "Impressions",
        "clicks": "Link Clicks",
        "spend": "Amount Spent (USD)",
        "conversions": "Results",
        "ctr": "CTR (Link Click-Through Rate)",
        "days_running": None,
    },
    "google": {
        "impressions": "Impressions",
        "clicks": "Clicks",
        "spend": "Cost",
        "conversions": "Conversions",
        "ctr": "CTR",
        "days_running": None,
    },
    "x": {
        "impressions": "Impressions",
        "clicks": "Link clicks",
        "spend": "Billed charge (USD)",
        "conversions": None,
        "ctr": "CTR",
        "days_running": None,
    },
    "linkedin": {
        "impressions": "Impressions",
        "clicks": "Clicks",
        "spend": "Amount Spent (USD)",
        "conversions": "Conversions",
        "ctr": "CTR",
        "days_running": None,
    },
}

MAPPING_DIR = os.getenv("COLUMN_MAPPING_DIR", "/tmp/ad-machine-column-mappings")


def parse_csv(
    content: bytes,
    platform: str,
    column_mapping: dict | None = None,
    pairing_id_column: str | None = None,
) -> list[dict]:
    mapping = column_mapping or _load_saved_mapping(platform) or PLATFORM_COLUMN_DEFAULTS.get(platform, {})

    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows = []

    for raw_row in reader:
        row = {}
        for internal_key, csv_col in mapping.items():
            if csv_col and csv_col in raw_row:
                raw_val = raw_row[csv_col].replace(",", "").replace("%", "").strip()
                try:
                    if internal_key in ("impressions", "clicks", "days_running", "conversions"):
                        row[internal_key] = int(float(raw_val)) if raw_val else 0
                    elif internal_key in ("spend", "ctr", "cpa"):
                        row[internal_key] = float(raw_val) if raw_val else 0.0
                    else:
                        row[internal_key] = raw_val
                except (ValueError, TypeError):
                    row[internal_key] = 0

        if "ctr" not in row or row.get("ctr", 0) == 0:
            impressions = row.get("impressions", 0)
            clicks = row.get("clicks", 0)
            row["ctr"] = round(clicks / impressions, 4) if impressions else 0.0

        if pairing_id_column and pairing_id_column in raw_row:
            row["pairing_id"] = raw_row[pairing_id_column]
        else:
            row["pairing_id"] = ""

        row["platform"] = platform
        row["days_running"] = row.get("days_running", 0) or 7
        row.setdefault("spend", 0.0)
        row.setdefault("impressions", 0)
        row.setdefault("clicks", 0)
        rows.append(row)

    return rows


def save_column_mapping(platform: str, mapping: dict) -> None:
    Path(MAPPING_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(MAPPING_DIR) / f"{platform}_mapping.json"
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2)


def _load_saved_mapping(platform: str) -> dict | None:
    path = Path(MAPPING_DIR) / f"{platform}_mapping.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None
