# Lionare Desktop v0.1.3 — Backend Integration

This patch connects the native desktop to the existing Lionare backend response contracts and adds read-only LQIE run/archive APIs.

## What changes

- Parses query-bearing endpoint paths correctly (`/api/company?symbol=AAPL`, `/api/series?...`).
- Requests company details, historical SEC fundamentals series, and experimental fundamental forecasts.
- Plots annual reported fundamentals in the central chart, clearly labelled as fundamentals and not stock prices.
- Displays official headlines and GDELT events in separate tabs.
- Displays company fundamentals in the watchlist instead of an empty `LAST` quote column.
- Displays the dataset summary returned by `/api/overview` and actual source health structures (`probe_results`, `rss_results`, `gdelt_result`).
- Adds `/api/lqie/status` and `/api/lqie/runs` to expose PatternEngine availability, run-manager index history, Gold output inventory, and the known PyTrendline/pandas compatibility diagnostic.
- Keeps market quotes and OHLCV candles explicitly unavailable until a permitted price source is integrated.
- Keeps network error handling compatible with PySide6 enum values.

## Apply

Extract this folder into the repository root so the structure is:

`lionare_backend_desktop_v0_1_3/apply_patch.sh`

Then in WSL Ubuntu:

```bash
cd /mnt/c/lionare
bash lionare_backend_desktop_v0_1_3/apply_patch.sh
```

The installer backs up all five affected source files under `~/lionare-data/operations/desktop/backups/` before replacing or patching them. It compiles the updated modules before reporting success.

## Restart

Terminal 1 (WSL):

```bash
cd /mnt/c/lionare
source venv/bin/activate
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python apps/lionare_terminal/server.py
```

Terminal 2 (Windows PowerShell):

```powershell
cd C:\lionare
$env:LIONARE_API_URL = "http://127.0.0.1:8765"
$env:LIONARE_DATA_LAKE = "\\wsl.localhost\Ubuntu\home\ishendra\lionare-data"
.\.venv-desktop\Scripts\python.exe apps\lionare_desktop\main.py
```

## Notes

- The desktop uses the existing API; it does not run LQIE calculations in the UI process.
- LQIE history is read from `~/lionare-data/operations/lqie/index.csv` when runs have been archived by `scripts/lqie_run_manager.py`.
- Existing pattern outputs under `gold/features/patterns/` are counted separately.
- No fake market prices or candle data are generated.
