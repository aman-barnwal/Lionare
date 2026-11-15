
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
TORCH_MODE="${1:-cu130}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python 3.12 is required."
    exit 1
fi

if [ ! -f venv/pyvenv.cfg ]; then
    "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate

python -c '
import sys
if sys.version_info[:2] != (3, 12):
    raise SystemExit("This project currently requires Python 3.12")
'

python -m pip install --upgrade pip

echo "Installing LQIE and all Python dependencies..."
python -m pip install -e ".[all]"

case "$TORCH_MODE" in
    cu130)
        echo "Installing PyTorch CUDA 13.0..."
        python -m pip install torch==2.14.1 \
            --index-url https://download.pytorch.org/whl/cu130
        ;;
    cpu)
        echo "Installing CPU-only PyTorch..."
        python -m pip install torch==2.14.1 \
            --index-url https://download.pytorch.org/whl/cpu
        ;;
    *)
        echo "Usage: ./scripts/install.sh [cu130|cpu]"
        exit 1
        ;;
esac

echo "Checking dependency consistency..."
python -m pip check

echo "Verifying installations..."
python - <<'PY'
import numpy
import torch
import polars
import duckdb
import pyarrow
import sklearn
from openbb import obb

print("NumPy:", numpy.__version__)
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("Polars:", polars.__version__)
print("DuckDB:", duckdb.__version__)
print("PyArrow:", pyarrow.__version__)
print("Scikit-learn:", sklearn.__version__)
print("OpenBB providers:", sorted(obb.coverage.providers))
print("Installation verification complete.")
PY

echo "LQIE installation completed."

