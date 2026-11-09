# Единый портал: кабинет компании и все семь проектов на одном порту.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

Write-Host "ML-кабинет: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Первый запрос прогревает модели 10-20 секунд." -ForegroundColor DarkGray
python -m gateway.app
