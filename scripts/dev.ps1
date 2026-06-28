<#
.SYNOPSIS
  Script de développement HELYOS.

.DESCRIPTION
  Commandes :
    setup   Crée un venv (.venv) et installe le Kernel avec la couche serveur + dev.
    test    Lance la suite de tests du cœur (stdlib only ; venv non requis).
    run     Démarre l'API du Kernel (http://127.0.0.1:8080). Nécessite 'setup'.
    up      Démarre l'infra Docker (profil 'core' : postgres + redis).
    up-all  Démarre toute l'infra Docker (profil 'all').
    down    Arrête l'infra Docker.

.EXAMPLE
  .\scripts\dev.ps1 test
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet("setup", "test", "run", "up", "up-all", "down")]
  [string]$Command = "test"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Kernel = Join-Path $Root "apps\jarvis-kernel"
$Src = Join-Path $Kernel "src"
$Tests = Join-Path $Kernel "tests"
$Venv = Join-Path $Root ".venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Compose = Join-Path $Root "deploy\docker-compose.yml"

function Resolve-Python {
  if (Test-Path $VenvPy) { return $VenvPy }
  return "python"
}

switch ($Command) {
  "setup" {
    Write-Host "==> Création du venv ($Venv)" -ForegroundColor Cyan
    python -m venv $Venv
    Write-Host "==> Installation du Kernel (.[server,dev])" -ForegroundColor Cyan
    & $VenvPy -m pip install --upgrade pip
    & $VenvPy -m pip install -e "$Kernel[server,dev]"
    Write-Host "OK. Lancez : .\scripts\dev.ps1 test" -ForegroundColor Green
  }
  "test" {
    $py = Resolve-Python
    Write-Host "==> Tests (python=$py)" -ForegroundColor Cyan
    $env:PYTHONPATH = $Src
    & $py -m unittest discover -s $Tests -t $Kernel -v
  }
  "run" {
    if (-not (Test-Path $VenvPy)) { throw "venv absent. Lancez d'abord : .\scripts\dev.ps1 setup" }
    Write-Host "==> Démarrage de l'API sur http://127.0.0.1:8080 (Ctrl+C pour arrêter)" -ForegroundColor Cyan
    $env:PYTHONPATH = $Src
    & $VenvPy -m jarvis_kernel
  }
  "up" {
    docker compose -f $Compose --profile core up -d
  }
  "up-all" {
    docker compose -f $Compose --profile all up -d
  }
  "down" {
    docker compose -f $Compose --profile all down
  }
}
