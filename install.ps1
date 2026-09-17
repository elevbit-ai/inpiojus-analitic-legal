# =====================================================================
#  InpioJus Analitic Legal — Instalador para PowerShell (Windows)
#  Autor: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
#
#  Instalação em uma linha:
#    irm https://elevbit-ai.github.io/inpiojus-analitic-legal/install.ps1 | iex
# =====================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║   InpioJus Analitic Legal — Instalador       ║" -ForegroundColor Cyan
Write-Host "  ║   por Joaquim Pedro de Morais Filho          ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica o Python -------------------------------------------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Host "  [!] Python 3.9+ nao encontrado." -ForegroundColor Yellow
    Write-Host "      Instale com:  winget install Python.Python.3.12" -ForegroundColor Yellow
    Write-Host "      Depois execute este instalador novamente."
    return
}
$versao = & $python.Source --version
Write-Host "  [ok] $versao encontrado." -ForegroundColor Green

# 2. Baixa a versao mais recente ---------------------------------------
$destino = Join-Path $env:LOCALAPPDATA "InpioJus"
$zipUrl  = "https://github.com/elevbit-ai/inpiojus-analitic-legal/archive/refs/heads/main.zip"
$zipTmp  = Join-Path $env:TEMP "inpiojus-main.zip"

Write-Host "  [..] Baixando a InpioJus do GitHub..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipTmp -UseBasicParsing

if (Test-Path $destino) { Remove-Item $destino -Recurse -Force }
New-Item -ItemType Directory -Force $destino | Out-Null

$extracao = Join-Path $env:TEMP "inpiojus-extract"
if (Test-Path $extracao) { Remove-Item $extracao -Recurse -Force }
Expand-Archive -Path $zipTmp -DestinationPath $extracao -Force
$raiz = Get-ChildItem $extracao -Directory | Select-Object -First 1
Copy-Item -Path (Join-Path $raiz.FullName "*") -Destination $destino -Recurse -Force
Remove-Item $zipTmp, $extracao -Recurse -Force

Write-Host "  [ok] Instalada em $destino" -ForegroundColor Green

# 3. Cria o comando `inpiojus` no perfil do PowerShell ------------------
$marcador = "# --- InpioJus Analitic Legal ---"
$funcao = @"

$marcador
function inpiojus {
    & "$($python.Source)" -m inpiojus @args
}
`$env:PYTHONPATH = "$destino;`$env:PYTHONPATH"
"@

if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}
$conteudoPerfil = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($conteudoPerfil -notmatch [regex]::Escape($marcador)) {
    Add-Content -Path $PROFILE -Value $funcao
    Write-Host "  [ok] Comando 'inpiojus' adicionado ao seu perfil do PowerShell." -ForegroundColor Green
} else {
    Write-Host "  [ok] Comando 'inpiojus' ja estava configurado." -ForegroundColor Green
}

# 4. Disponibiliza na sessao atual --------------------------------------
$env:PYTHONPATH = "$destino;$env:PYTHONPATH"
$pythonExe = $python.Source
New-Item -Path Function:\global:inpiojus -Value { & $pythonExe -m inpiojus @args }.GetNewClosure() -Force | Out-Null

Write-Host ""
Write-Host "  Instalacao concluida! Experimente agora:" -ForegroundColor Cyan
Write-Host ""
Write-Host "    inpiojus analisar `"$destino\exemplos\processo_civil_exemplo.txt`""
Write-Host "    inpiojus memoria"
Write-Host "    inpiojus --versao"
Write-Host ""
Write-Host "  Documentacao: https://elevbit-ai.github.io/inpiojus-analitic-legal/"
Write-Host ""
