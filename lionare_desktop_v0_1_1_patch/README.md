# Lionare Desktop v0.1.1 integration patch

This patch corrects the first native desktop integration against the actual `apps/lionare_terminal/server.py` response shapes shared by the project owner.

## Fixes

- Removes the nonexistent `/api/datasets` request. Dataset inventory and storage information are already included in `/api/overview`.
- Adds the missing main-window handlers for backend responses, errors, company selection, workspace switching, layout persistence, reset, and About.
- Sets the desktop package version to 0.1.1.
- Avoids repeatedly scanning the WSL data lake over a Windows UNC path on the GUI thread; uses `/api/overview` for summary/inventory.
- Correctly renders company summary fields (`revenue_latest`, `net_income_latest`, `assets_latest`, `history_start`, `history_end`, `revenue_years`).
- Correctly consumes the news response shape `{ "headlines": [...], "events": [...] }`.
- Adds explicit workspace visibility rules and exclusive workspace buttons.
- Keeps market prices and candles explicitly unavailable until a permitted OHLCV feed is connected.
- Backs up the replaced files before installing the patch.

## Apply from WSL Ubuntu

1. Extract this ZIP in `/mnt/c/lionare` so the folder `lionare_desktop_v0_1_1_patch` appears in the repository root.
2. Run:

```bash
cd /mnt/c/lionare
bash lionare_desktop_v0_1_1_patch/apply_patch.sh
```

3. Launch the native app from Windows PowerShell using the separate desktop environment, or from WSL if Qt is available there.

```powershell
cd C:\lionare
$env:LIONARE_API_URL = "http://127.0.0.1:8765"
$env:LIONARE_DATA_LAKE = "\\wsl.localhost\Ubuntu\home\ishendra\lionare-data"
.\.venv-desktop\Scripts\python.exe apps\lionare_desktop\main.py
```

The backend should be running in the first WSL terminal. This patch does not add an OHLCV feed or execute LQIE analysis inside the GUI process.
