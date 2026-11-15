#!/usr/bin/env bash
set -euo pipefail

PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$PATCH_DIR/.." && pwd)"
BACKUP_ROOT="$HOME/lionare-data/operations/desktop/backups/v0.1.3_$(date -u +%Y%m%dT%H%M%SZ)"

FILES=(
  "apps/lionare_desktop/app.py"
  "apps/lionare_desktop/config.py"
  "apps/lionare_desktop/widgets/panels.py"
  "apps/lionare_desktop/services/backend_client.py"
  "apps/lionare_terminal/server.py"
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
cp "$PATCH_DIR/apps/lionare_desktop/services/backend_client.py" "$ROOT/apps/lionare_desktop/services/backend_client.py"

(
  cd "$ROOT"
  python "$PATCH_DIR/apps/lionare_terminal/add_lqie_routes.py"
)

(
  cd "$ROOT"
  python -m compileall -q apps/lionare_desktop apps/lionare_terminal/server.py
)

printf '\nLionare Desktop v0.1.3 backend integration patch applied.\n'
printf 'Backup: %s\n' "$BACKUP_ROOT"
printf 'Added API routes: /api/lqie/status and /api/lqie/runs\n'
