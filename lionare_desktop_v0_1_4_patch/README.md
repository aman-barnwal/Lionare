# Lionare Desktop v0.1.4 — usability refresh

This patch replaces the cramped dock-heavy interface with a native multi-workspace desktop layout.

## Changes

- Dedicated stacked workspaces: Dashboard, Markets, Equity, Portfolio, News, Quant Lab, Data Lake, System.
- Dashboard hierarchy: KPI cards, global reference markets, financial history chart, company watchlist, news preview.
- Equity research: company selector, four summary metrics, selectable SEC metric chart, annual filing table and experimental fundamental forecast.
- News: separate official headline and GDELT tabs with double-click source opening.
- Quant Lab: LQIE engine/version/run/output summary, trendline compatibility details and archived run table.
- Data Lake: full registered dataset inventory and storage summary.
- System: backend and source-health summary.
- Responsive splitters, readable typography, consistent card hierarchy and simpler navigation.
- No fabricated prices. All SEC financial graphs are explicitly labeled reported fundamentals, not stock prices.

## Apply

Extract this folder to the Lionare repository root, so it appears as `lionare_desktop_v0_1_4_patch/`.

From WSL Ubuntu at `/mnt/c/lionare`:

```bash
bash lionare_desktop_v0_1_4_patch/apply_patch.sh
```

The script backs up the three replaced files to `~/lionare-data/operations/desktop/backups/` and compiles the package.

The backend API and data lake are not modified by this patch. It uses the existing endpoints from v0.1.3.

## Launch

Keep the WSL backend running in Terminal 1. Launch from Windows PowerShell:

```powershell
cd C:\lionare
$env:LIONARE_API_URL = "http://127.0.0.1:8765"
$env:LIONARE_DATA_LAKE = "\\wsl.localhost\Ubuntu\home\ishendra\lionare-data"
.\.venv-desktop\Scripts\python.exe apps\lionare_desktop\main.py
```

## Limitations

- Equity charts visualize annual SEC financial fundamentals; they are not OHLCV candles.
- Global index quote and market breadth panels remain explicitly unavailable until a permitted market-price data source is integrated.
- Portfolio tracking remains a placeholder pending portfolio ledger implementation.
- This patch has been syntax-compiled but requires launch validation on the target Windows installation.
