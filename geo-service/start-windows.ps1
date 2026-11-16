[CmdletBinding()]
param([switch]$Install, [switch]$Test, [switch]$PipeLoop, [int]$Port = 8002, [string]$PythonPath, [switch]$Reload, [switch]$Verify, [switch]$LivePower, [switch]$AutoPort)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($PipeLoop -and -not $Test) { throw 'Use -PipeLoop junto com -Test.' }
if ($Verify -and $Test) { throw 'Use -Verify separado de -Test.' }
if ($LivePower -and -not $Verify) { throw 'Use -LivePower junto com -Verify.' }
function Test-WorkingPython([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    try { & $Path --version *> $null; return ($LASTEXITCODE -eq 0) }
    catch { return $false }
}
if (-not $PythonPath) {
    $PythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    # Uma .venv recebida de outro computador pode apontar para Python inexistente.
    # Nesse caso, preserva a pasta recebida e cria um ambiente local separado.
    if (-not (Test-WorkingPython $PythonPath)) {
        $PythonPath = Join-Path $PSScriptRoot '.venv-local\Scripts\python.exe'
    }
    if ($Install -and -not (Test-WorkingPython $PythonPath)) {
        & python -m venv .venv-local
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente Python.' }
    }
    if (-not (Test-WorkingPython $PythonPath)) {
        $sharedPython = Join-Path $PSScriptRoot '..\..\geo-service\geo-service\.venv\Scripts\python.exe'
        if (Test-Path -LiteralPath $sharedPython) {
            $PythonPath = (Resolve-Path -LiteralPath $sharedPython).Path
            Write-Host 'Usando o ambiente existente. Para instalar todas as dependencias desta versao, execute com -Install.'
        } else { throw 'Ambiente Python ausente. Execute com -Install ou informe -PythonPath.' }
    }
}
if (-not $Install) {
    & $PythonPath -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('fastapi','uvicorn','httpx','pydantic')) else 1)" *> $null
    if ($LASTEXITCODE -ne 0) {
        $runtimeFallback = Join-Path $PSScriptRoot '..\..\geo-service\geo-service\.venv\Scripts\python.exe'
        if (Test-WorkingPython $runtimeFallback) {
            & $runtimeFallback -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) for n in ('fastapi','uvicorn','httpx','pydantic')) else 1)" *> $null
            if ($LASTEXITCODE -ne 0) { throw 'Ambiente sem dependencias. Execute com -Install em conexao com PyPI.' }
            $PythonPath = (Resolve-Path -LiteralPath $runtimeFallback).Path
            Write-Host 'Ambiente local incompleto; usando ambiente existente com dependencias principais.'
        } else { throw 'Ambiente sem dependencias. Execute com -Install em conexao com PyPI.' }
    }
}
if ($Install) {
    & $PythonPath -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependencias.' }
}
if ($Verify) {
    $verificationArgs = @((Join-Path $PSScriptRoot 'verify-delivery.py'), '--port', "$Port")
    if ($LivePower) { $verificationArgs += '--live-power' }
    & $PythonPath @verificationArgs
} elseif ($Test) {
    if ($PipeLoop) { & $PythonPath .\run-tests.py --windows-pipe-loop }
    else { & $PythonPath .\run-tests.py }
} else {
    if ($AutoPort) {
        $availablePort = $null
        foreach ($candidatePort in @(8010, 8011, 8012, 8088, 8765, 9000, 18080)) {
            $portProbe = $null
            try {
                $portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $candidatePort)
                $portProbe.Server.ExclusiveAddressUse = $true
                $portProbe.Start()
                $availablePort = $candidatePort
                break
            } catch { Write-Host "Porta $candidatePort indisponivel; tentando outra." }
            finally { if ($portProbe) { $portProbe.Stop() } }
        }
        if ($null -eq $availablePort) { throw 'Nenhuma porta de demonstracao disponivel. Nao foram alteradas permissoes ou firewall.' }
        $Port = $availablePort
    }
    & $PythonPath (Join-Path $PSScriptRoot 'check-startup.py')
    if ($LASTEXITCODE -ne 0) { throw 'Conferencia da aplicacao falhou; servidor nao iniciado.' }
    Write-Host "Bancada geo-service1: http://127.0.0.1:$Port/test"
    # Caminho explicito evita importar a outra pasta app existente no projeto.
    Write-Host "Projeto: $PSScriptRoot"
    $serverArgs = @('-m', 'uvicorn', 'app.main:app', '--app-dir', $PSScriptRoot, '--host', '127.0.0.1', '--port', "$Port")
    if ($Reload) { $serverArgs += '--reload' }
    & $PythonPath @serverArgs
}
if ($LASTEXITCODE -ne 0) { throw "Processo encerrado com codigo $LASTEXITCODE." }
