#!/usr/bin/env bash
set -euo pipefail

PATCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$PATCH_ROOT/.." && pwd)"

if [[ ! -f "$PROJECT_ROOT/apps/lionare_desktop/app.py" || ! -f "$PROJECT_ROOT/apps/lionare_desktop/widgets/panels.py" ]]; then
  echo "ERROR: Run this script from the extracted patch folder inside the Lionare repository."
  echo "Expected repository root: $PROJECT_ROOT"
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/lionare-data/operations/desktop/backups/desktop_patch_$STAMP"
mkdir -p "$BACKUP/apps/lionare_desktop/widgets"
cp "$PROJECT_ROOT/apps/lionare_desktop/app.py" "$BACKUP/apps/lionare_desktop/app.py"
cp "$PROJECT_ROOT/apps/lionare_desktop/config.py" "$BACKUP/apps/lionare_desktop/config.py"
cp "$PROJECT_ROOT/apps/lionare_desktop/widgets/panels.py" "$BACKUP/apps/lionare_desktop/widgets/panels.py"

cp "$PATCH_ROOT/files/apps/lionare_desktop/app.py" "$PROJECT_ROOT/apps/lionare_desktop/app.py"
cp "$PATCH_ROOT/files/apps/lionare_desktop/config.py" "$PROJECT_ROOT/apps/lionare_desktop/config.py"
cp "$PATCH_ROOT/files/apps/lionare_desktop/widgets/panels.py" "$PROJECT_ROOT/apps/lionare_desktop/widgets/panels.py"

python -m compileall -q "$PROJECT_ROOT/apps/lionare_desktop"
echo "Lionare Desktop patch applied."
echo "Backup: $BACKUP"
echo "Compile check: PASSED"
