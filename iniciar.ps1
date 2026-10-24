$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendDir = Join-Path $projectRoot 'backend'
$frontendDir = Join-Path $projectRoot 'frontend'
$python = Join-Path $backendDir '.venv\Scripts\python.exe'
$viteScript = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
$backendUrl = 'http://127.0.0.1:8000'
$frontendUrl = 'http://localhost:5173'

function Test-HttpReady([string] $url) {
    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing
        return [int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Test-PortInUse([int] $port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Start-LocalServer([string] $name, [string] $executable, [string[]] $arguments, [string] $workingDirectory, [int] $port, [string] $readyUrl, [string] $logPrefix) {
    if (Test-HttpReady $readyUrl) {
        Write-Host "$name ja esta respondendo em $readyUrl"
        return
    }
    if (Test-PortInUse $port) {
        throw "A porta $port ja esta ocupada, mas $name nao respondeu em $readyUrl. Feche o processo que usa essa porta e tente novamente."
    }

    $stdout = Join-Path $workingDirectory "$logPrefix.log"
    $stderr = Join-Path $workingDirectory "$logPrefix-error.log"
    $null = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $workingDirectory -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-HttpReady $readyUrl) {
            Write-Host "$name iniciado em $readyUrl"
            return
        }
    }

    if (Test-Path $stderr) {
        $details = (Get-Content $stderr -Tail 12) -join [Environment]::NewLine
        throw "$name nao respondeu. Log de erro: $stderr`n$details"
    }
    throw "$name nao respondeu em $readyUrl. Confira as dependencias e a configuracao local."
}

try {
    if (-not (Test-Path $python)) {
        throw "Ambiente Python nao encontrado em $python. Consulte backend\README.md para configurar o backend."
    }
    if (-not (Test-Path (Join-Path $backendDir '.env'))) {
        throw 'Configuracao backend\.env nao encontrada. Crie o arquivo e defina DATABASE_URL conforme backend\.env.example.'
    }
    if (-not (Test-Path $viteScript)) {
        throw "Vite nao encontrado em $viteScript. Instale Node.js e as dependencias do frontend (pnpm install)."
    }

    $node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
    if (-not $node) {
        $nvsNodeRoot = Join-Path $env:LOCALAPPDATA 'nvs\node'
        $nodeCandidates = @()
        if (Test-Path $nvsNodeRoot) {
            $nodeCandidates += Get-ChildItem $nvsNodeRoot -Directory | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'x64\node.exe' }
        }
        $nodeCandidates += Join-Path $env:ProgramFiles 'nodejs\node.exe'
        $node = $nodeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $node) {
        throw 'Node.js nao foi encontrado no PATH nem nos locais usuais. Instale Node.js 20.19+ ou 22.12+ e tente novamente.'
    }

    Start-LocalServer 'Backend' $python @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload', '--reload-dir', 'app', '--no-access-log') $backendDir 8000 "$backendUrl/openapi.json" 'uvicorn'
    Start-LocalServer 'Frontend' $node @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173') $frontendDir 5173 $frontendUrl 'vite'

    Write-Host ''
    Write-Host "Sistema pronto: $frontendUrl"
    Write-Host "Documentacao da API: $backendUrl/docs"
    Start-Process $frontendUrl
} catch {
    Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
