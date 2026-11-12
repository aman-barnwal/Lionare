#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="$HOME/lionare-data/operations/desktop/backups/v0.1.2_$(date -u +%Y%m%dT%H%M%SZ)"

for rel in \
  "apps/lionare_desktop/app.py" \
  "apps/lionare_desktop/widgets/panels.py" \
  "apps/lionare_desktop/services/backend_client.py" \
  "apps/lionare_desktop/config.py"; do
  if [[ ! -f "$ROOT/$rel" ]]; then
    echo "ERROR: Expected existing file missing: $ROOT/$rel" >&2
    exit 1
  fi
done

mkdir -p "$BACKUP_ROOT"
for rel in \
  "apps/lionare_desktop/app.py" \
  "apps/lionare_desktop/widgets/panels.py" \
  "apps/lionare_desktop/services/backend_client.py" \
  "apps/lionare_desktop/config.py"; do
  mkdir -p "$BACKUP_ROOT/$(dirname "$rel")"
  cp -p "$ROOT/$rel" "$BACKUP_ROOT/$rel"
done

cp "$PATCH_DIR/apps/lionare_desktop/app.py" "$ROOT/apps/lionare_desktop/app.py"
cp "$PATCH_DIR/apps/lionare_desktop/widgets/panels.py" "$ROOT/apps/lionare_desktop/widgets/panels.py"
cp "$PATCH_DIR/apps/lionare_desktop/services/backend_client.py" "$ROOT/apps/lionare_desktop/services/backend_client.py"
cp "$PATCH_DIR/apps/lionare_desktop/config.py" "$ROOT/apps/lionare_desktop/config.py"

printf '\nPatch applied. Backup: %s\n' "$BACKUP_ROOT"
