$ErrorActionPreference = 'Stop'
Set-Location 'C:\lionare'
if (-not (Test-Path '.venv-desktop\Scripts\python.exe')) {
    py -3.12 -m venv .venv-desktop
}
.\.venv-desktop\Scripts\python.exe -m pip install --upgrade pip
.\.venv-desktop\Scripts\python.exe -m pip install -r apps\lionare_desktop\requirements.txt
$env:LIONARE_API_URL = 'http://127.0.0.1:8765'
$env:LIONARE_DATA_LAKE = '\\wsl.localhost\Ubuntu\home\ishendra\lionare-data'
.\.venv-desktop\Scripts\python.exe apps\lionare_desktop\main.py
