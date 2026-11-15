# Lionare desktop UI redesign v2

This patch refines the native PySide6 desktop UI based on the user's Fincept Terminal reference screenshot.

## Changes

- Replaces the four large KPI cards with a compact inline terminal status strip.
- Reorganizes the dashboard into three resizable columns: global indices + portfolio summary; company watchlist + SEC financial history; market/data status + company fundamentals.
- Adds nested vertical splitters so dashboard panels can be resized by dragging separators.
- Moves the workspace navigation above the reference-watch ticker strip to more closely match the target terminal chrome.
- Increases legibility of table rows, column headings, panel titles and status text.
- Removes mojibaked dash/separator strings from the desktop UI.
- Uses shorter financial values in watchlist and company-focus panels to prevent fiscal-year text from being clipped.
- Gives the financial chart an explicit empty-state message when fewer than two valid SEC annual points can be parsed, and accepts a year derived from date/period_end as a fallback.
- Adds a portfolio summary that explicitly reports no configured portfolio rather than making up balances.

## Data integrity

No market prices, returns, gainers/losers or portfolio balances are fabricated. The existing UI continues to say that live quotes are not connected. All company facts and news remain sourced from the existing Lionare backend.

## Files changed

- `apps/lionare_desktop/app.py`
- `apps/lionare_desktop/widgets/panels.py`

## Apply from WSL

After downloading `lionare-ui-redesign-v2-patch.zip`, find it in the Windows Downloads folder and run:

```bash
cd /mnt/c/lionare
PATCH="$(find /mnt/c/Users -path '*/Downloads/lionare-ui-redesign-v2-patch.zip' -type f -print -quit)"
test -n "$PATCH" && test -s "$PATCH"
unzip -tq "$PATCH"
BACKUP="$HOME/lionare-ui-v1-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
cp -a apps/lionare_desktop/app.py "$BACKUP/"
mkdir -p "$BACKUP/widgets"
cp -a apps/lionare_desktop/widgets/panels.py "$BACKUP/widgets/"
unzip -o "$PATCH" -d /mnt/c/lionare
python -m py_compile apps/lionare_desktop/app.py apps/lionare_desktop/widgets/panels.py
```

Restart the desktop process after applying. The backend and data lake are not changed by this UI-only patch.
