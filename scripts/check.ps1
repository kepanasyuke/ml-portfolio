# Проверка качества: линтер -> AST-гейт стиля -> тесты.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

python -m ruff check .
if (-not $?) { throw "ruff: есть замечания" }

python tools/style_gate.py .
if (-not $?) { throw "style-gate: нарушены правила стиля" }

python -m pytest
if (-not $?) { throw "pytest: тесты упали" }

Write-Host "Все проверки пройдены: ruff, style-gate, pytest" -ForegroundColor Green
