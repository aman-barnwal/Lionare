# Lionare Desktop UI Redesign

This update refreshes the native PySide6 desktop dashboard toward a compact institutional terminal layout.

## Changed files

- `apps/lionare_desktop/app.py`
  - Reworked the Qt stylesheet to a near-black terminal palette.
  - Tightened the top application chrome and navigation spacing.
  - Connected the dashboard's new source-health panels to existing backend responses.
- `apps/lionare_desktop/widgets/panels.py`
  - Rebuilt the dashboard into a three-column terminal workspace.
  - Added Market Pulse, Data Lake snapshot, and Company Focus panels.
  - Kept global indices, company watchlist, SEC fundamentals history, and news/events.
  - Reduced table row heights and card padding for higher information density.

## Data integrity

No live quotes, market returns, sentiment scores, gainers, or losers were fabricated. The UI continues to show quote availability as `NOT CONNECTED` until a validated quote/OHLCV feed is configured. Company facts, data-lake counts, news counts, and health states are populated from the existing local backend responses.

## Apply the patch

Extract `lionare-ui-redesign-patch.zip` into the Lionare project root, overwriting the two matching files. The patch preserves the existing backend, API routes, data lake, and other workspace pages.

Alternatively, use Windows PowerShell:

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\lionare-ui-redesign-patch.zip" -DestinationPath "C:\lionare" -Force
```

Then relaunch the desktop app using the existing Windows desktop virtual environment:

```powershell
Set-Location C:\lionare
$env:LIONARE_API_URL = "http://127.0.0.1:8765"
$env:LIONARE_DATA_LAKE = "\\wsl.localhost\Ubuntu\home\ishendra\lionare-data"
& ".\.venv-desktop\Scripts\python.exe" "apps\lionare_desktop\main.py"
```
