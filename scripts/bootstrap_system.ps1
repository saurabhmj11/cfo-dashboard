# PowerShell Bootstrap Script for Autonomous Financial Analyst Platform

Write-Host "🚀 Starting Autonomous Financial Analyst System..." -ForegroundColor Cyan

# 1. Spin up containers
Write-Host "📦 Orchestrating Docker containers..."
docker-compose up -d --build

# 2. Wait for Paperclip Control Plane to be healthy
Write-Host "⏳ Waiting for Paperclip Control Plane (v0.3.1) to be healthy..."
$Attempts = 0
$MaxAttempts = 30
$Healthy = $false

while (-not $Healthy -and $Attempts -lt $MaxAttempts) {
    $Status = docker inspect --format='{{json .State.Health.Status}}' (docker-compose ps -q paperclip)
    if ($Status -eq '"healthy"') {
        $Healthy = $true
        Write-Host "✅ Paperclip is healthy!" -ForegroundColor Green
    } else {
        $Attempts++
        Write-Sleep -Seconds 5
        Write-Host "  - Waiting... ($Attempts/$MaxAttempts)"
    }
}

if (-not $Healthy) {
    Write-Host "❌ Error: Paperclip failed to become healthy in time." -ForegroundColor Red
    exit 1
}

# 3. Register/Hire Agents
Write-Host "🤖 Hiring Autonomous Workforce (Detective, Forecaster, Advisor)..."
python scripts/register_paperclip_agents.py

Write-Host "🎉 System is fully operational and autonomous!" -ForegroundColor Green
Write-Host "🔗 Dashboard: http://localhost:3000"
Write-Host "🔗 Paperclip: http://localhost:3100"
