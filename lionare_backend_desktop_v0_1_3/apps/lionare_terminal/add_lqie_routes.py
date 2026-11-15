from __future__ import annotations

import csv
import json
import re
from pathlib import Path


def main() -> None:
    server_path = Path("apps/lionare_terminal/server.py")
    source = server_path.read_text(encoding="utf-8")
    marker = "# LIONARE_LQIE_API_V1"
    if marker in source:
        print("LQIE routes already installed; no change made.")
        return

    if "import csv\n" not in source:
        source = source.replace("import json\n", "import json\nimport csv\n", 1)

    helper = r'''# LIONARE_LQIE_API_V1
LQIE_ARCHIVE_ROOT = LAKE.root / "operations" / "lqie"
LQIE_GOLD_ROOT = LAKE.gold / "features" / "patterns"


def read_lqie_runs(limit=30):
    index_path = LQIE_ARCHIVE_ROOT / "index.csv"
    records = []
    if index_path.is_file():
        try:
            with index_path.open("r", newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    records.append(row)
        except (OSError, csv.Error):
            records = []
    records.sort(key=lambda item: str(item.get("started_utc", "")), reverse=True)
    return records[:max(1, min(int(limit), 100))]


def read_lqie_status():
    engine_available = False
    engine_version = "unknown"
    try:
        from lqie.patterns.engine import PatternEngine
        engine_available = True
        engine_version = str(getattr(PatternEngine, "VERSION", "available"))
    except Exception:
        pass

    runs = read_lqie_runs(30)
    outputs = []
    if LQIE_GOLD_ROOT.is_dir():
        for item in sorted(LQIE_GOLD_ROOT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
            try:
                stat = item.stat()
                outputs.append({"name": item.name, "path": str(item), "size_bytes": stat.st_size, "modified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime))})
            except OSError:
                continue

    diagnostic = {"status": "not_checked", "pandas_version": None, "pytrendline_version": None}
    try:
        import importlib.metadata as package_metadata
        diagnostic["pandas_version"] = package_metadata.version("pandas")
        diagnostic["pytrendline_version"] = package_metadata.version("pytrendline")
        import pytrendline
        detector_file = Path(pytrendline.__file__).resolve().parent / "detect.py"
        if detector_file.exists():
            found = any(re.search(r"\b\w+\s*=\s*trends_df\.append\s*\(", line) for line in detector_file.read_text(encoding="utf-8", errors="replace").splitlines())
            diagnostic["status"] = "compatibility_warning" if found else "no_known_append_call_found"
    except Exception as exc:
        diagnostic["status"] = "diagnostic_unavailable"
        diagnostic["error"] = f"{type(exc).__name__}: {exc}"

    return {
        "engine_available": engine_available,
        "engine_version": engine_version,
        "run_archive_root": str(LQIE_ARCHIVE_ROOT),
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "recent_runs": runs,
        "gold_output_root": str(LQIE_GOLD_ROOT),
        "gold_output_count": len(outputs),
        "recent_gold_outputs": outputs[:20],
        "trendline_compatibility": diagnostic,
    }


'''
    anchor = "class Handler(BaseHTTPRequestHandler):"
    if anchor not in source:
        raise SystemExit("Could not find Handler class anchor; backend file unchanged.")
    source = source.replace(anchor, helper + anchor, 1)

    route_anchor = '            if path == "/api/news":\n'
    route_code = '''            if path == "/api/lqie/status":
                self.send_json(read_lqie_status())
                return

            if path == "/api/lqie/runs":
                try:
                    limit = int(params.get("limit", ["30"])[0])
                except (TypeError, ValueError):
                    limit = 30
                self.send_json({"runs": read_lqie_runs(limit)})
                return

'''
    if route_anchor not in source:
        raise SystemExit("Could not find /api/news route anchor; backend file unchanged.")
    source = source.replace(route_anchor, route_code + route_anchor, 1)
    server_path.write_text(source, encoding="utf-8")
    print("Installed /api/lqie/status and /api/lqie/runs routes.")


if __name__ == "__main__":
    main()
