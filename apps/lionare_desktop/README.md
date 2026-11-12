# Lionare Desktop 0.1.0

A native PySide6 desktop workstation shell for Lionare. It is intentionally separate from the existing `apps/lionare_terminal` browser UI and does not replace the LQIE or data-lake packages.

## Current capabilities

- Native Qt desktop window; no browser is launched.
- Dockable, floatable, closable panels with workspace presets.
- Dashboard, Markets, Equity, Portfolio, News, Quant Lab, Data Lake and System workspaces.
- Asynchronous connection to the existing local API (`/api/health`, `/api/overview`, `/api/companies`, `/api/news`, `/api/datasets`).
- Local Parquet inventory from `~/lionare-data`.
- Local layout persistence using Qt settings.
- Desktop log at `~/lionare-data/operations/desktop/logs/lionare_desktop.log`.
- Explicitly does not invent prices, candles, market breadth or portfolio performance.

## Terminal 1 — start the existing Lionare service in WSL Ubuntu

```bash
cd /mnt/c/lionare
source venv/bin/activate
python3 apps/lionare_terminal/server.py
```

Keep this process running. It currently exposes the existing local service at `http://127.0.0.1:8765`.

## Terminal 2 — run the native Windows desktop

Open **Windows PowerShell** (not the WSL shell) and run:

```powershell
cd C:\lionare
py -3.12 -m venv .venv-desktop
.\.venv-desktop\Scripts\python.exe -m pip install --upgrade pip
.\.venv-desktop\Scripts\python.exe -m pip install -r apps\lionare_desktop\requirements.txt
$env:LIONARE_API_URL = "http://127.0.0.1:8765"
.\.venv-desktop\Scripts\python.exe apps\lionare_desktop\main.py
```

This keeps the Qt desktop dependencies out of the existing LQIE `venv`. The desktop uses Windows Python and communicates with the WSL service over localhost. If the API is not reachable, check `http://127.0.0.1:8765/api/health` from Windows first.

## Run inside WSLg (alternative)

```bash
cd /mnt/c/lionare
python3 -m venv .venv-desktop
source .venv-desktop/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/lionare_desktop/requirements.txt
python apps/lionare_desktop/main.py
```

This requires a working WSLg graphical display. Prefer the Windows PowerShell instructions for a native Windows window.

## Environment variables

- `LIONARE_API_URL` — backend base URL, defaults to `http://127.0.0.1:8765`.
- `LIONARE_DATA_LAKE` — data lake root, defaults to `~/lionare-data` for the desktop user's home directory.
- `LIONARE_REFRESH_INTERVAL_MS` — refresh cadence in milliseconds, defaults to 10000 (minimum 3000).

When running the desktop under Windows, set `LIONARE_DATA_LAKE` to the actual data-lake path visible to Windows if you also want its local storage inventory. The default is the Windows user's home directory, not the WSL home directory.

## Current limitations / next integration steps

- The central chart is an honest placeholder. It is not a candlestick chart until a permitted OHLCV feed is integrated.
- Watchlist rows show company identity and a pending price feed; no fake last prices are generated.
- The app displays news and company names only when returned by the existing API in a recognised JSON list shape.
- LQIE is detected as an installed package but is not executed in the GUI process. It must remain in the separate engine/service process.
- The trendline detector still has a PyTrendline/pandas compatibility issue recorded in the project history; this UI does not patch it.
- API routes `/api/health`, `/api/companies`, `/api/news` are expected from the current service. If your `server.py` changes route schema, update `services/backend_client.py` and panel adapters.

## Design and licences

This is an original Lionare layout, not a reproduction of Fincept or Bloomberg assets or branding. PySide6 is Qt's official Python binding. Review Qt's licensing obligations before distributing a commercial desktop binary.
