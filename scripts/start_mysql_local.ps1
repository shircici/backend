# Start local MySQL (repo .mysql_local). From repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\start_mysql_local.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$ini = Join-Path $root ".mysql_local\my.ini"
if (-not (Test-Path $ini)) {
    Write-Error "Missing my.ini: $ini"
}
$mysqld = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
if (-not (Test-Path $mysqld)) {
    Write-Error "mysqld not found: $mysqld (edit path in script if different version)"
}
$net = netstat -an
if ($net -match "127\.0\.0\.1:3306\s+.*LISTENING") {
    Write-Host "MySQL already listening on 127.0.0.1:3306."
    exit 0
}
$defaults = ($root -replace "\\", "/") + "/.mysql_local/my.ini"
Start-Process -FilePath $mysqld -ArgumentList "--defaults-file=$defaults" -WindowStyle Hidden
Start-Sleep -Seconds 4
Write-Host "Started mysqld with data dir .mysql_local\data. Stop: kill mysqld process."
