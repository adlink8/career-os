[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DeployDir = Join-Path $ProjectRoot 'deploy/judge0'
$ComposeFile = Join-Path $DeployDir 'docker-compose.yml'
$ConfigPath = Join-Path $DeployDir 'judge0.conf'
$RuntimeEnvPath = Join-Path $DeployDir 'runtime.env'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'docker is not available on PATH.'
}

function New-Secret {
    param([int]$Bytes = 24)
    return [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes($Bytes))
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    $redisPassword = New-Secret
    $postgresPassword = New-Secret
    $authToken = New-Secret
    $config = @"
JUDGE0_TELEMETRY_ENABLE=false
ENABLE_WAIT_RESULT=true
ENABLE_NETWORK=false
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$redisPassword
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=judge0
POSTGRES_USER=judge0
POSTGRES_PASSWORD=$postgresPassword
AUTHN_HEADER=X-Auth-Token
AUTHN_TOKEN=$authToken
ALLOW_ORIGIN=http://127.0.0.1
"@
    [IO.File]::WriteAllText($ConfigPath, $config.Trim() + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))
} else {
    $authToken = ((Get-Content -LiteralPath $ConfigPath | Where-Object { $_ -match '^AUTHN_TOKEN=' }) -replace '^AUTHN_TOKEN=', '').Trim()
    if ([string]::IsNullOrWhiteSpace($authToken) -or $authToken -eq 'CHANGE_ME') {
        throw "AUTHN_TOKEN is missing in $ConfigPath. Remove the local config and rerun to regenerate it."
    }
}

$runtimeEnv = @"
JUDGE0_URL=http://127.0.0.1:2358
JUDGE0_TOKEN=$authToken
CAREER_OS_PLUGINS=judge0
"@
[IO.File]::WriteAllText($RuntimeEnvPath, $runtimeEnv.Trim() + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))

Push-Location $DeployDir
try {
    Write-Host 'Starting Judge0 database and Redis...'
    & docker compose -f $ComposeFile up -d db redis
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up -d db redis failed.' }

    Write-Host 'Starting Judge0 server and worker...'
    & docker compose -f $ComposeFile up -d server worker
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up -d server worker failed.' }
} finally {
    Pop-Location
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$healthHeaders = @{ 'X-Auth-Token' = $authToken }
$lastError = $null
do {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:2358/system_info' -Headers $healthHeaders -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "Judge0 is healthy at http://127.0.0.1:2358 (local-only binding)."
            & docker compose -f $ComposeFile ps
            exit 0
        }
    } catch {
        $lastError = $_.Exception.Message
    }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

& docker compose -f $ComposeFile ps
throw "Judge0 health check timed out after $TimeoutSeconds seconds. Last error: $lastError"
