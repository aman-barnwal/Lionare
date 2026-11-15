# Lionare dashboard visibility fix v3

## Fixes
- Data tables reset vertical and horizontal scrollbars to the beginning after every data refresh, preventing the watchlist from opening on its last row.
- Reduced table row and header density while retaining readability.
- Increased minimum watchlist panel/table height and rebalanced the center splitter.
- Reduced the chart minimum height slightly to give the watchlist more room.
- Made the dashboard news panel compact so the three main columns retain more vertical space.
- News lists now scroll to the first/newest item after refresh.

## Files
- `apps/lionare_desktop/app.py`
- `apps/lionare_desktop/widgets/panels.py`

No backend routes, data sources, or data files were modified.
