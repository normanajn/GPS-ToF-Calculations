# Bootstrap gps-tof on Windows: create/refresh venv, install the package, run the tests.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path venv)) { python -m venv venv }
.\venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
.\venv\Scripts\python.exe -m pip install -e ".[test]"
.\venv\Scripts\python.exe -m pytest -q
Write-Host ""
Write-Host "gps-tof is ready:  .\venv\Scripts\Activate.ps1 ; gps-tof -c config\nova.yaml"
