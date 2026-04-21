param(
    [string]$DbName = "sku_db",
    [string]$DbUser = "backend",
    [string]$DbPassword = "backend_dev_pass",
    [string]$DbHost = "127.0.0.1",
    [string]$DbPort = "3306",
    [int]$SeedCount = 5,
    [string]$WithWriteCheck = "true"
)

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$python = "python"
$mysqlBin = "C:\Program Files\MySQL\MySQL Server 8.4\bin"
$mysqlExe = Join-Path $mysqlBin "mysql.exe"
$mysqlAdminExe = Join-Path $mysqlBin "mysqladmin.exe"
$startMysqlScript = Join-Path $PSScriptRoot "start_mysql_local.ps1"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Push-Location $root

Write-Step "Prepare env file"
$envPath = Join-Path $root ".env"
$envExamplePath = Join-Path $root ".env.example"
if (-not (Test-Path $envPath)) {
    if (-not (Test-Path $envExamplePath)) {
        throw "Missing .env.example. Path: $envExamplePath"
    }
    Copy-Item $envExamplePath $envPath
    Write-Host "Created .env from .env.example"
}

Write-Step "Check mysql tools"
if (-not (Test-Path $mysqlExe)) {
    throw "mysql.exe not found: $mysqlExe"
}
if (-not (Test-Path $mysqlAdminExe)) {
    throw "mysqladmin.exe not found: $mysqlAdminExe"
}
if ($env:Path -notlike "*$mysqlBin*") {
    $env:Path = "$mysqlBin;$env:Path"
}

Write-Step "Start local mysql"
& powershell -ExecutionPolicy Bypass -File $startMysqlScript
& $mysqlAdminExe -h $DbHost -P $DbPort -u root ping | Out-Null
Write-Host "MySQL is alive on ${DbHost}:$DbPort"

Write-Step "Create database and app user"
$sql = "CREATE DATABASE IF NOT EXISTS $DbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; " +
    "CREATE USER IF NOT EXISTS '$DbUser'@'%' IDENTIFIED BY '$DbPassword'; " +
    "ALTER USER '$DbUser'@'%' IDENTIFIED BY '$DbPassword'; " +
    "GRANT ALL PRIVILEGES ON $DbName.* TO '$DbUser'@'%'; FLUSH PRIVILEGES;"
& $mysqlExe -h $DbHost -P $DbPort -u root -e $sql

Write-Step "Install mysqlclient"
& $python -m pip install mysqlclient

Write-Step "Run django migrate"
& $python manage.py migrate

Write-Step "Django shell DB test"
& $python manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute('SELECT 1'); print('shell db test ->', c.fetchone()[0])"

Write-Step "Django dbshell test"
& $python manage.py dbshell -- -e "SHOW DATABASES;"

Write-Step "Seed demo data"
& $python manage.py seed_demo_sku --count $SeedCount
Write-Host "View data at: http://127.0.0.1:8000/api/sku/list/"

Write-Step "Run db health checks"
& $python manage.py db_healthcheck
$withWriteNormalized = $WithWriteCheck.ToString().Trim().ToLowerInvariant()
$withWriteEnabled = @("1", "true", "$true", "yes", "y") -contains $withWriteNormalized
if ($withWriteEnabled) {
    & $python manage.py db_healthcheck --with-write
}

Write-Host ""
Write-Host "All checks finished." -ForegroundColor Green
Pop-Location
