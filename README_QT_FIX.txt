Lionare Qt paint-event fix

Cause:
FundamentalChart subclasses QWidget, which already has a callable metric() method.
Assigning a string to self.metric shadowed that Qt method and caused PySide6 to fail
while constructing QPainter during paintEvent.

Fix:
Renamed the chart's selected financial series attribute from self.metric to
self.metric_name. This does not change the backend, data model, routes, or UI layout.

Apply from WSL in /mnt/c/lionare:
unzip -o /path/to/lionare-qt-metric-fix.zip -d /mnt/c/lionare

Then restart Lionare Desktop.
