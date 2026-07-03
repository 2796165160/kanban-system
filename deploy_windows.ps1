param(
    [string]$Port = "8000",
    [switch]$InstallService,
    [switch]$RemoveService,
    [switch]$StartService,
    [switch]$StopService,
    [switch]$StatusService
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$ServiceName = "KanbanSystem"

function Write-Step($msg) { Write-Host ">>> $msg" -ForegroundColor Cyan }
function Write-OK($msg) { Write-Host "  OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  WARN: $msg" -ForegroundColor Yellow }

# ── 1. Check Python ──
Write-Step "检查 Python..."
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "Python 未安装或不在 PATH 中" }
Write-OK "Python: $py"

# ── 2. Install Python deps ──
Write-Step "安装 Python 依赖..."
& $py -m pip install -r (Join-Path $BackendDir "requirements.txt") -q
Write-OK "依赖安装完成"

# ── 3. Build frontend ──
Write-Step "构建前端..."
$npm = (Get-Command npm -ErrorAction SilentlyContinue).Source
if (-not $npm) { throw "npm 未安装" }
Set-Location $FrontendDir
& $npm run build
if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
Set-Location $RootDir
Write-OK "前端构建完成: $(Join-Path $FrontendDir "dist")"

# ── 4. Check nssm ──
if ($InstallService -or $RemoveService -or $StartService -or $StopService -or $StatusService) {
    $nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
    if (-not $nssm) { throw "nssm 未找到，请先下载 nssm.exe 放入 PATH。下载: https://nssm.cc/download" }
}

# ── 5. Windows Service management ──
if ($InstallService) {
    Write-Step "安装 Windows 服务: $ServiceName"
    $uvicornArgs = "-m uvicorn main:app --host 0.0.0.0 --port $Port"
    & $nssm install $ServiceName $py $uvicornArgs
    & $nssm set $ServiceName AppDirectory $BackendDir
    & $nssm set $ServiceName AppStdout (Join-Path $BackendDir "access.log")
    & $nssm set $ServiceName AppStderr (Join-Path $BackendDir "error.log")
    & $nssm set $ServiceName Start SERVICE_AUTO_START
    & $nssm set $ServiceName DisplayName "工序进度看板系统"
    & $nssm set $ServiceName Description "标注平台工序进度看板 - FastAPI + Vue3"
    Write-OK "服务已安装。使用 Start-Service $ServiceName 启动"
}

if ($StartService) {
    Write-Step "启动服务: $ServiceName"
    & $nssm start $ServiceName
    Write-OK "服务已启动，监听端口 $Port"
}

if ($StopService) {
    Write-Step "停止服务: $ServiceName"
    & $nssm stop $ServiceName
    Write-OK "服务已停止"
}

if ($RemoveService) {
    Write-Step "删除服务: $ServiceName"
    & $nssm stop $ServiceName -confirm
    & $nssm remove $ServiceName -confirm
    Write-OK "服务已删除"
}

if ($StatusService) {
    & $nssm status $ServiceName
}

if (-not $InstallService -and -not $RemoveService -and -not $StartService -and -not $StopService -and -not $StatusService) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " 工序进度看板系统 - Windows 部署脚本" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "用法: .\deploy_windows.ps1 [参数]" -ForegroundColor White
    Write-Host ""
    Write-Host "  不带参数:  构建前端 + 安装依赖" -ForegroundColor Cyan
    Write-Host "  -InstallService   安装为 Windows 服务（需 nssm）" -ForegroundColor Cyan
    Write-Host "  -StartService     启动服务" -ForegroundColor Cyan
    Write-Host "  -StopService      停止服务" -ForegroundColor Cyan
    Write-Host "  -RemoveService    删除服务" -ForegroundColor Cyan
    Write-Host "  -StatusService    查看服务状态" -ForegroundColor Cyan
    Write-Host "  -Port 8080        指定端口（默认 8000）" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "手动启动（开发测试）:" -ForegroundColor Yellow
    Write-Host "  python -m uvicorn main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
    Write-Host "  然后浏览器访问 http://服务器IP:8000" -ForegroundColor White
    Write-Host ""

    # 如果没有参数，做依赖安装和构建
    Write-Step "安装依赖 + 构建前端..."
}
