"""One-time fetch of the NCRB city-wise cyber crime baseline dataset.

Source: "Cyber Crime (City-wise) - 2021-2023", published via
data.opencity.in (mirrors NCRB's "Crime in India 2023" report), publicly
downloadable with no login required:
https://data.opencity.in/dataset/crime-in-india-2023

This is run once (or whenever NCRB publishes an updated year) to produce a
static data/external/ncrb_cybercrime_city.json -- the rest of the
geospatial pipeline reads that file, not the PDF, so a slow/flaky
government PDF download is never on the runtime path.

Usage:
    python -m src.graph.fetch_ncrb_data
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber
import requests

PDF_URL = (
    "https://data.opencity.in/dataset/40449a25-7fb3-4e38-91b9-f834af6078e2"
    "/resource/a08751e9-c4fa-44e5-a9ed-05864d2fbb0e"
    "/download/d00a835d-d3e9-4ef1-955e-9cf3f5c8302d.pdf"
)
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "external" / "ncrb_cybercrime_city.json"

# NCRB's table packs every field into one PDF column per row, e.g.
# "1 Agra 0 0 171 17.5 9.8 92.8" -- this splits it back into fields.
_ROW_PATTERN = re.compile(
    r"^\d+\s+(?P<city>.+?)\s+(?P<y2021>\d+)\s+(?P<y2022>\d+)\s+(?P<y2023>\d+)\s+"
    r"(?P<population_lakhs>[\d.]+)\s+(?P<rate_2023>[\d.]+)\s+(?P<chargesheeting_rate>[\d.]+|-)$"
)


def _parse_table(rows: list[list[str | None]]) -> list[dict]:
    records = []
    for row in rows:
        cell = row[0]
        if not cell:
            continue
        match = _ROW_PATTERN.match(cell.replace("\n", " ").strip())
        if not match:
            continue  # skips the header row and the TOTAL row
        records.append(
            {
                "city": match["city"],
                "cases_2021": int(match["y2021"]),
                "cases_2022": int(match["y2022"]),
                "cases_2023": int(match["y2023"]),
                "population_lakhs_2011": float(match["population_lakhs"]),
                "crime_rate_2023": float(match["rate_2023"]),
                "chargesheeting_rate_2023": None
                if match["chargesheeting_rate"] == "-"
                else float(match["chargesheeting_rate"]),
            }
        )
    return records


def main() -> None:
    response = requests.get(PDF_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()

    pdf_path = OUTPUT_PATH.parent / "_ncrb_cybercrime_city.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(response.content)

    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[0].extract_tables()
    records = _parse_table(tables[0])

    OUTPUT_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    pdf_path.unlink()
    print(f"Parsed {len(records)} cities -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
