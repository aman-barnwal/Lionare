"""Historical public-data ingestion for Lionare LQIE 0.4."""

import csv
import io
import json
import math
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import polars as pl

from lqie.data.lake import (
    LakePaths,
    ManifestManager,
    SourceDefinition,
    SourceRegistry,
    write_parquet,
)

START_YEAR = 2010
END_YEAR = date.today().year
TODAY = date.today().isoformat()

lake = LakePaths().ensure()
registry = SourceRegistry(lake=lake)
manifest = ManifestManager(lake=lake)

BLS_SERIES = {
    "CUUR0000SA0": "CPI all items, not seasonally adjusted",
    "CUSR0000SA0": "CPI all items, seasonally adjusted",
    "LNS14000000": "Unemployment rate",
    "LNS11300000": "Labor force participation rate",
    "LNS12000000": "Civilian employment level",
    "CES0000000001": "Total nonfarm payroll employment",
    "CES0500000003": "Average hourly earnings, private sector",
    "WPUFD4": "Producer price index, final demand",
}

WB_COUNTRIES = [
    "USA", "IND", "CHN", "GBR", "DEU",
    "JPN", "CAN", "AUS", "FRA", "BRA",
]

WB_INDICATORS = [
    "NY.GDP.MKTP.CD",
    "NY.GDP.PCAP.CD",
    "FP.CPI.TOTL.ZG",
    "SL.UEM.TOTL.ZS",
    "NE.EXP.GNFS.ZS",
    "NE.IMP.GNFS.ZS",
    "GC.DOD.TOTL.GD.ZS",
]

ECB_CURRENCIES = ["USD", "GBP", "JPY", "INR", "CHF", "AUD", "CAD", "CNY"]


def request_bytes(url, data=None, headers=None, attempts=4):
    request_headers = {
        "User-Agent": "Lionare-LQIE/0.4 public-data research",
        "Accept": "*/*",
    }
    if headers:
        request_headers.update(headers)

    req = Request(url, data=data, headers=request_headers)

    for attempt in range(attempts):
        try:
            with urlopen(req, timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        time.sleep(2 ** attempt)

    raise RuntimeError(f"Could not download {url}")


def write_raw(path, payload, source_id, dataset):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_bytes(payload)
    temp.replace(path)

    manifest.record_file(
        path,
        source_id=source_id,
        dataset=dataset,
        retrieval_method="official public download",
    )
    return path


def is_cached(path, hours=None):
    path = Path(path)
    if not path.is_file():
        return False
    if hours is None:
        return True
    return (time.time() - path.stat().st_mtime) < hours * 3600


def register_sources():
    sources = [
        SourceDefinition(
            source_id="bls",
            name="US Bureau of Labor Statistics",
            homepage="https://www.bls.gov/",
            license_name="US government statistical data; retain BLS attribution",
            terms_url="https://www.bls.gov/developers/",
            access_method="public_endpoint",
            update_frequency="Monthly / release schedule",
            categories=("inflation", "employment", "wages", "producer_prices"),
            api_key_required=False,
        ),
        SourceDefinition(
            source_id="world_bank",
            name="World Bank Open Data",
            homepage="https://data.worldbank.org/",
            license_name="CC-BY-4.0 default for World Bank-produced datasets; verify each dataset",
            terms_url="https://datacatalog.worldbank.org/public-licenses",
            access_method="public_endpoint",
            update_frequency="Indicator dependent",
            categories=("global_macro", "countries", "development"),
            api_key_required=False,
            attribution="World Bank",
        ),
        SourceDefinition(
            source_id="treasury",
            name="US Treasury Interest Rate Statistics",
            homepage="https://home.treasury.gov/",
            license_name="US government information; retain Treasury attribution and check notices",
            terms_url="https://home.treasury.gov/interest-rates-data-csv-archive/",
            access_method="public_endpoint",
            update_frequency="Business day",
            categories=("government_bonds", "yield_curve", "rates"),
            api_key_required=False,
            attribution="US Department of the Treasury",
        ),
        SourceDefinition(
            source_id="ecb",
            name="European Central Bank Exchange Rates",
            homepage="https://data.ecb.europa.eu/",
            license_name="ECB website reuse terms; attribution required",
            terms_url="https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html",
            access_method="public_endpoint",
            update_frequency="Daily",
            categories=("fx", "reference_rates"),
            api_key_required=False,
            attribution="European Central Bank",
            notes="Reference rates, not executable trading quotes.",
        ),
        SourceDefinition(
            source_id="cftc",
            name="US Commodity Futures Trading Commission",
            homepage="https://www.cftc.gov/",
            license_name="US government report data; acknowledge CFTC",
            terms_url="https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",
            access_method="public_download",
            update_frequency="Weekly",
            categories=("derivatives", "futures", "positioning"),
            api_key_required=False,
            attribution="US Commodity Futures Trading Commission",
        ),
    ]

    for source in sources:
        registry.register(source)

    print(f"Registered {len(sources)} historical-data sources.")


def ingest_bls():
    print("\n========== BLS: 2010–2026 ==========")
    endpoint = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    raw_dir = lake.bronze / "us" / "bls"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    windows = [(2010, 2019), (2020, END_YEAR)]

    for start_year, end_year in windows:
        raw_path = raw_dir / f"series_{start_year}_{end_year}.json"

        if is_cached(raw_path):
            payload = raw_path.read_bytes()
            print(f"Using cached BLS window {start_year}-{end_year}")
        else:
            body = json.dumps({
                "seriesid": list(BLS_SERIES),
                "startyear": str(start_year),
                "endyear": str(end_year),
            }).encode("utf-8")

            payload = request_bytes(
                endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            write_raw(
                raw_path, payload, "bls",
                f"bls_series_{start_year}_{end_year}",
            )

        result = json.loads(payload)

        if result.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS request failed: {result.get('message')}")

        for series in result.get("Results", {}).get("series", []):
            series_id = series.get("seriesID", "")

            for observation in series.get("data", []):
                try:
                    value = float(observation["value"])
                    year = int(observation["year"])
                except (KeyError, TypeError, ValueError):
                    continue

                if not math.isfinite(value):
                    continue

                period = observation.get("period", "")
                month = None
                observation_date = None

                if period.startswith("M") and period[1:].isdigit():
                    month_number = int(period[1:])
                    if 1 <= month_number <= 12:
                        month = month_number
                        observation_date = f"{year}-{month:02d}-01"
                    elif month_number == 13:
                        observation_date = f"{year}-12-31"

                rows.append({
                    "series_id": series_id,
                    "series_name": BLS_SERIES.get(series_id, series_id),
                    "year": year,
                    "period": period,
                    "period_name": observation.get("periodName"),
                    "month": month,
                    "observation_date": observation_date,
                    "value": value,
                    "footnotes_json": json.dumps(
                        observation.get("footnotes", [])
                    ),
                    "source": "BLS",
                })

    if not rows:
        raise RuntimeError("BLS returned no usable observations.")

    destination = lake.silver / "macro" / "bls_observations.parquet"
    write_parquet(pl.DataFrame(rows, infer_schema_length=None), destination)
    manifest.record_file(
        destination, "bls", "bls_observations",
        "Normalised BLS API observations",
        {"start_year": START_YEAR, "end_year": END_YEAR, "rows": len(rows)},
    )
    print("BLS observations:", len(rows))


def ingest_world_bank():
    print("\n========== WORLD BANK: 2010–2026 ==========")

    countries = ";".join(WB_COUNTRIES)
    indicators = ";".join(WB_INDICATORS)

    url = (
        f"https://api.worldbank.org/v2/country/{countries}"
        f"/indicator/{indicators}"
        f"?{urlencode({'format': 'json', 'date': f'{START_YEAR}:{END_YEAR}', 'per_page': 20000})}"
    )

    raw_path = lake.bronze / "global" / "worldbank" / "selected_indicators.json"

    if is_cached(raw_path, hours=168):
        payload = raw_path.read_bytes()
        print("Using cached World Bank response.")
    else:
        payload = request_bytes(url)
        write_raw(
            raw_path, payload, "world_bank",
            "world_bank_selected_indicators",
        )

    result = json.loads(payload)
    if not isinstance(result, list) or len(result) < 2:
        raise RuntimeError(f"Unexpected World Bank response: {result}")

    records = result[1] or []
    rows = []

    for item in records:
        value = item.get("value")
        if value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

        try:
            year = int(item.get("date"))
        except (TypeError, ValueError):
            continue

        rows.append({
            "country_code": (item.get("countryiso3code") or ""),
            "country": (item.get("country") or {}).get("value", ""),
            "indicator_code": (item.get("indicator") or {}).get("id", ""),
            "indicator": (item.get("indicator") or {}).get("value", ""),
            "year": year,
            "value": value,
            "unit": item.get("unit", ""),
            "obs_status": item.get("obs_status", ""),
            "decimal": item.get("decimal"),
            "source": "World Bank",
        })

    if not rows:
        raise RuntimeError("World Bank returned no usable observations.")

    destination = (
        lake.silver / "macro" / "world_bank_selected_indicators.parquet"
    )
    write_parquet(pl.DataFrame(rows, infer_schema_length=None), destination)
    manifest.record_file(
        destination, "world_bank", "selected_country_indicators",
        "Normalised World Bank API observations",
        {"countries": WB_COUNTRIES, "indicators": WB_INDICATORS, "rows": len(rows)},
    )
    print("World Bank observations:", len(rows))


def xml_local_name(tag):
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def ingest_treasury():
    print("\n========== US TREASURY YIELD CURVE: 2010–2026 ==========")

    endpoint = (
        "https://home.treasury.gov/resource-center/data-chart-center/"
        "interest-rates/pages/xml"
    )

    rows = []
    raw_dir = lake.bronze / "us" / "treasury"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for year in range(START_YEAR, END_YEAR + 1):
        raw_path = raw_dir / f"daily_yield_curve_{year}.xml"

        if is_cached(raw_path, hours=24 if year == END_YEAR else None):
            payload = raw_path.read_bytes()
        else:
            query = urlencode({
                "data": "daily_treasury_yield_curve",
                "field_tdr_date_value": str(year),
            })
            payload = request_bytes(f"{endpoint}?{query}")
            write_raw(
                raw_path, payload, "treasury",
                f"daily_yield_curve_{year}",
            )

        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            print(f"Treasury XML error for {year}: {exc}")
            continue

        year_count = 0

        for entry in root.iter():
            if xml_local_name(entry.tag) != "entry":
                continue

            properties = next(
                (
                    node for node in entry.iter()
                    if xml_local_name(node.tag) == "properties"
                ),
                None,
            )
            if properties is None:
                continue

            values = {
                xml_local_name(child.tag): (child.text or "").strip()
                for child in properties
            }

            raw_date = values.get("NEW_DATE", "")
            try:
                observation_date = date.fromisoformat(raw_date[:10]).isoformat()
            except ValueError:
                continue

            if not observation_date.startswith(str(year)):
                continue

            for field, raw_value in values.items():
                if not field.startswith("BC_") or not raw_value:
                    continue

                try:
                    value = float(raw_value)
                except ValueError:
                    continue

                if not math.isfinite(value):
                    continue

                rows.append({
                    "date": observation_date,
                    "tenor": field[3:],
                    "yield_percent": value,
                    "source": "US Treasury",
                })
                year_count += 1

        print(f"Treasury {year}: {year_count} tenor observations")
        time.sleep(0.15)

    if not rows:
        raise RuntimeError("Treasury returned no usable yield observations.")

    destination = (
        lake.silver / "rates" / "treasury_daily_yield_curve.parquet"
    )
    write_parquet(pl.DataFrame(rows, infer_schema_length=None), destination)
    manifest.record_file(
        destination, "treasury", "daily_treasury_yield_curve",
        "Normalised official Treasury XML feed",
        {"start_year": START_YEAR, "end_year": END_YEAR, "rows": len(rows)},
    )
    print("Treasury observations:", len(rows))


def ingest_ecb():
    print("\n========== ECB DAILY FX REFERENCE RATES: 2010–2026 ==========")

    endpoint = "https://data-api.ecb.europa.eu/service/data/EXR"
    raw_dir = lake.bronze / "global" / "ecb"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for currency in ECB_CURRENCIES:
        raw_path = raw_dir / f"daily_{currency}_against_eur.csv"

        if is_cached(raw_path, hours=24 if currency else None):
            payload = raw_path.read_bytes()
        else:
            query = urlencode({
                "startPeriod": f"{START_YEAR}-01-01",
                "endPeriod": TODAY,
                "format": "csvdata",
            })
            url = f"{endpoint}/D.{currency}.EUR.SP00.A?{query}"
            payload = request_bytes(url)
            write_raw(
                raw_path, payload, "ecb",
                f"daily_reference_rate_{currency}_eur",
            )

        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))

        if not reader.fieldnames:
            print(f"ECB {currency}: empty response")
            continue

        count = 0

        for item in reader:
            period = (item.get("TIME_PERIOD") or "").strip()
            raw_value = (item.get("OBS_VALUE") or "").strip()

            if not period or not raw_value:
                continue

            try:
                value = float(raw_value)
                date.fromisoformat(period[:10])
            except ValueError:
                continue

            if not math.isfinite(value):
                continue

            rows.append({
                "date": period[:10],
                "currency": currency,
                "base_currency": "EUR",
                "reference_rate": value,
                "frequency": "daily",
                "source": "ECB",
            })
            count += 1

        print(f"ECB {currency}/EUR: {count} observations")
        time.sleep(0.15)

    if not rows:
        raise RuntimeError("ECB returned no usable FX observations.")

    destination = (
        lake.silver / "fx" / "ecb_daily_reference_rates.parquet"
    )
    write_parquet(pl.DataFrame(rows, infer_schema_length=None), destination)
    manifest.record_file(
        destination, "ecb", "daily_reference_fx",
        "Normalised ECB SDMX CSV observations",
        {"currencies": ECB_CURRENCIES, "rows": len(rows)},
    )
    print("ECB observations:", len(rows))


def ingest_cftc():
    print("\n========== CFTC DISAGGREGATED FUTURES: 2010–2026 ==========")

    raw_dir = lake.bronze / "global" / "cftc"
    silver_dir = lake.silver / "derivatives"
    raw_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    total_rows = 0

    for year in range(START_YEAR, END_YEAR + 1):
        archive_path = raw_dir / f"fut_disagg_txt_{year}.zip"
        parquet_path = silver_dir / f"cftc_disagg_futures_{year}.parquet"

        if parquet_path.is_file():
            print(f"CFTC {year}: already ingested")
            completed += 1
            continue

        try:
            if not archive_path.is_file():
                url = (
                    "https://www.cftc.gov/files/dea/history/"
                    f"fut_disagg_txt_{year}.zip"
                )
                payload = request_bytes(url)
                if not payload.startswith(b"PK"):
                    raise ValueError("CFTC response is not a ZIP archive")
                write_raw(
                    archive_path, payload, "cftc",
                    f"disaggregated_futures_only_{year}",
                )

            frames = []

            with zipfile.ZipFile(archive_path) as archive:
                members = [
                    name for name in archive.namelist()
                    if name.lower().endswith((".txt", ".csv"))
                ]

                for member in members:
                    raw = archive.read(member)
                    if not raw.strip():
                        continue

                    frame = pl.read_csv(
                        io.BytesIO(raw),
                        separator=",",
                        infer_schema_length=0,
                        ignore_errors=True,
                        truncate_ragged_lines=True,
                        encoding="utf8-lossy",
                    )
                    if frame.width > 1 and frame.height > 0:
                        frames.append(frame)

            if not frames:
                raise ValueError("No readable CFTC text data found in ZIP")

            frame = pl.concat(frames, how="diagonal_relaxed")

            report_date_column = next(
                (
                    column for column in frame.columns
                    if "report_date" in column.lower()
                ),
                None,
            )

            if report_date_column:
                year_filter = (
                    pl.col(report_date_column)
                    .cast(pl.Utf8)
                    .str.slice(0, 4)
                    == str(year)
                )
                frame = frame.filter(year_filter)

            if frame.height == 0:
                raise ValueError("No rows for requested report year")

            frame = frame.with_columns(
                pl.lit(year).alias("archive_year"),
                pl.lit("CFTC").alias("source"),
            )

            write_parquet(frame, parquet_path)

            manifest.record_file(
                parquet_path,
                "cftc",
                f"disaggregated_futures_{year}",
                "Normalised CFTC annual futures-only archive",
                {"year": year, "rows": frame.height},
            )

            print(f"CFTC {year}: {frame.height:,} records")
            completed += 1
            total_rows += frame.height
            time.sleep(0.25)

        except Exception as exc:
            print(f"CFTC {year} ERROR: {type(exc).__name__}: {exc}")

    print(f"CFTC archive years completed: {completed}")
    print(f"CFTC records processed this run: {total_rows}")


def main():
    print("LIONARE LQIE 0.4 — HISTORICAL OPEN DATA")
    print("Period:", START_YEAR, "to", END_YEAR)
    print("Data lake:", lake.root)

    register_sources()

    tasks = [
        ("BLS", ingest_bls),
        ("World Bank", ingest_world_bank),
        ("US Treasury", ingest_treasury),
        ("ECB FX", ingest_ecb),
        ("CFTC", ingest_cftc),
    ]

    successes = 0

    for name, task in tasks:
        try:
            task()
            successes += 1
        except Exception as exc:
            print(f"\n{name} FAILED: {type(exc).__name__}: {exc}")

    total_bytes = sum(
        path.stat().st_size
        for path in lake.root.rglob("*")
        if path.is_file()
    )

    print("\n========== HISTORICAL INGESTION SUMMARY ==========")
    print("Source families successful:", successes, "/", len(tasks))
    print(f"Data lake size: {total_bytes / 1024 / 1024:.2f} MB")
    print("Manifest entries:", len(manifest.entries()))
    print("Data lake root:", lake.root)

    if successes == 0:
        raise SystemExit("No historical source completed successfully.")


if __name__ == "__main__":
    main()
