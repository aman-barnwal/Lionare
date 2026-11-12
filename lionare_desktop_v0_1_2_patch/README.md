# Lionare Desktop v0.1.2 — Visual and Dock Layout Patch

This is a targeted patch for an existing Lionare Desktop installation. It replaces:

- `apps/lionare_desktop/app.py`
- `apps/lionare_desktop/widgets/panels.py`
- `apps/lionare_desktop/services/backend_client.py`
- `apps/lionare_desktop/config.py` (version bump to 0.1.2)

## What changes

- Reduces the Dashboard to five essential visible panels: Global Markets, Company Research, Watchlist, Market Pulse, and News & Events.
- Moves Quant Lab, Data Lake, System Status, Portfolio and Performance into dedicated workspaces / tabbed docks.
- Removes duplicate internal panel headings; the dock title is now the only panel title.
- Adds a separate navigation row so workspace buttons do not overflow the ticker strip.
- Improves spacing, typography, panel tables, company metrics and chart placeholder styling.
- Reads the actual backend response shapes: company annual records and `/api/news` with `headlines` and `events`.
- Removes the unsupported `/api/datasets` request.
- Adds Qt network error codes, URL and HTTP status to connection diagnostics.
- Does not fabricate price quotes or OHLCV candles.

## Apply (WSL Ubuntu)

Extract this ZIP into `/mnt/c/lionare`, so `lionare_desktop_v0_1_2_patch/` appears in the project root. Then run:

```bash
cd /mnt/c/lionare
bash lionare_desktop_v0_1_2_patch/apply_patch.sh
python -m compileall -q apps/lionare_desktop
```

The installer backs up the three replaced files under:
`~/lionare-data/operations/desktop/backups/`.

## Launch

Keep the WSL backend running in Terminal 1. In Windows PowerShell Terminal 2:

```powershell
cd C:\lionare
$env:LIONARE_API_URL = "http://127.0.0.1:8765"
$env:LIONARE_DATA_LAKE = "\\wsl.localhost\Ubuntu\home\ishendra\lionare-data"
.\.venv-desktop\Scripts\python.exe apps\lionare_desktop\main.py
```

This patch is designed for the current backend contract in `apps/lionare_terminal/server.py`. It changes the desktop UI only; it does not modify LQIE or the backend.
