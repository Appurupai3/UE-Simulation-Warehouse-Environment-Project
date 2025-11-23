# UE4.27 WebSocket Bridge Demo Startup Script (PowerShell)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

Write-Host "🚀 Starting UE4.27 WebSocket Bridge Demo..." -ForegroundColor Cyan

# Check bun
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: bun is not installed!" -ForegroundColor Red
    Write-Host "請先安裝 bun: powershell -c \"irm bun.sh/install.ps1|iex\"" -ForegroundColor Yellow
    exit 1
}

# Install frontend deps if needed
$frontendPath = Join-Path $scriptRoot "Frontend"
if (-not (Test-Path (Join-Path $frontendPath "node_modules"))) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontendPath
    bun install
    Pop-Location
}

Write-Host "🔧 Starting FastAPI Backend..." -ForegroundColor Cyan
$backendPath = Join-Path $scriptRoot "Backend"
$venvPath = Join-Path $backendPath "venv"

if (-not (Test-Path $venvPath)) {
    Write-Host "🐍 Creating Python virtual environment..." -ForegroundColor Yellow
    Push-Location $backendPath
    python -m venv venv
    Pop-Location
}

$venvPython = Join-Path $venvPath "Scripts/python.exe"
& $venvPython -m pip install -r (Join-Path $backendPath "requirements.txt")

Write-Host "🌐 Starting WebSocket server on port 8000..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($path, $python)
    Set-Location $path
    & $python -m app.main
} -ArgumentList $backendPath, $venvPython

Write-Host "🎨 Starting Vue.js Frontend..." -ForegroundColor Cyan
$frontendJob = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    bun run dev
} -ArgumentList $frontendPath

Write-Host ""
Write-Host "✅ Demo is now running!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access URLs:" -ForegroundColor Cyan
Write-Host "   🌐 Frontend: http://localhost:5173"
Write-Host "   🔌 WebSocket: ws://localhost:8000"
Write-Host ""
Write-Host "📖 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Open UE4.27 project"
Write-Host "   2. Create Blueprint WebSocket client (see UE_Client/README_Blueprint_WebSocket.md)"
Write-Host "   3. Connect UE client to ws://localhost:8000/ws/ue/your_client_id"
Write-Host ""
Write-Host "🛑 To stop demo:" -ForegroundColor Yellow
Write-Host "   Stop-Job $backendJob.Id $frontendJob.Id" -ForegroundColor Yellow
Write-Host ""
Write-Host "Enjoy the demo! 🎮" -ForegroundColor Green
