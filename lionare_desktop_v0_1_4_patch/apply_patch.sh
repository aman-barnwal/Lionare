#!/usr/bin/env bash
set -euo pipefail

PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$PATCH_DIR/.." && pwd)"
BACKUP_ROOT="$HOME/lionare-data/operations/desktop/backups/v0.1.4_$(date -u +%Y%m%dT%H%M%SZ)"
FILES=(
  "apps/lionare_desktop/app.py"
  "apps/lionare_desktop/config.py"
  "apps/lionare_desktop/widgets/panels.py"
)

for rel in "${FILES[@]}"; do
  [[ -f "$ROOT/$rel" ]] || { echo "ERROR: Missing expected file: $ROOT/$rel" >&2; exit 1; }
done

mkdir -p "$BACKUP_ROOT"
for rel in "${FILES[@]}"; do
  mkdir -p "$BACKUP_ROOT/$(dirname "$rel")"
  cp -p "$ROOT/$rel" "$BACKUP_ROOT/$rel"
done

cp "$PATCH_DIR/apps/lionare_desktop/app.py" "$ROOT/apps/lionare_desktop/app.py"
cp "$PATCH_DIR/apps/lionare_desktop/config.py" "$ROOT/apps/lionare_desktop/config.py"
cp "$PATCH_DIR/apps/lionare_desktop/widgets/panels.py" "$ROOT/apps/lionare_desktop/widgets/panels.py"

(
  cd "$ROOT"
  python -m compileall -q apps/lionare_desktop
)

printf '\nLionare Desktop v0.1.4 UI refresh applied.\n'
printf 'Backup: %s\n' "$BACKUP_ROOT"
printf 'Design: dedicated stacked workspaces, responsive cards, no dock-panel squeezing.\n'
