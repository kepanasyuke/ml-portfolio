# Запуск всех семи сервисов портфолио в отдельных окнах PowerShell.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$projects = @(
  @{ module = "projects.uplift_engine.app"; port = 8001; name = "Uplift Engine" },
  @{ module = "projects.promo_optimizer.app"; port = 8002; name = "Promo Optimizer" },
  @{ module = "projects.ab_lab.app"; port = 8003; name = "A/B Lab" },
  @{ module = "projects.ml_pipeline.app"; port = 8004; name = "ML Pipeline" },
  @{ module = "projects.churn_clv.app"; port = 8005; name = "Churn & CLV" },
  @{ module = "projects.ml_monitor.app"; port = 8006; name = "ML Monitor" },
  @{ module = "projects.sql_lab.app"; port = 8007; name = "SQL Metrics Lab" }
)

foreach ($project in $projects) {
  Start-Process -FilePath "python" -ArgumentList "-m", $project.module -WorkingDirectory $root
  Write-Host ("{0} -> http://127.0.0.1:{1}" -f $project.name, $project.port)
}

Write-Host "Открыть портфолио: http://127.0.0.1:8001" -ForegroundColor Green
