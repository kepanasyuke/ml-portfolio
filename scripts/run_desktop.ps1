# Запуск оконного приложения: шлюз в фоне плюс окно приложения.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

Write-Host "Открываю ML-кабинет в отдельном окне (127.0.0.1:8765)" -ForegroundColor Green
python -m desktop.app @args
