# HELYOS — accès réseau LOCAL (ton téléphone, ta tablette, sur TON wifi).
#
# Ce que ça fait : lance le noyau en écoutant sur toutes les interfaces de TA
# machine (0.0.0.0) au lieu de seulement localhost, et affiche l'URL à ouvrir
# sur ton téléphone. Reste dans ton réseau domestique — rien n'est publié sur
# Internet.
#
# ⚠️  À SAVOIR, sans détour : le noyau n'a PAS d'authentification. Toute personne
#    sur ton wifi qui ouvre cette URL contrôle HELYOS (voit le portefeuille,
#    ajoute des écritures, etc.). Sur ton wifi personnel = risque faible.
#    NE FAIS PAS ça sur un wifi public (gare, café, coworking).
#    Pour un accès « tout le monde, partout » sur Internet : il faut d'abord
#    construire l'authentification (voir docs/ACCES.md) — c'est un vrai chantier.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# adresse IPv4 locale (la première non-loopback, préférence wifi/ethernet)
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
  Sort-Object -Property InterfaceMetric |
  Select-Object -First 1).IPAddress
if (-not $ip) { $ip = "TON-IP-LOCALE" }

Write-Host ""
Write-Host "  HELYOS — accès réseau local" -ForegroundColor Cyan
Write-Host "  ---------------------------------------------"
Write-Host "  Sur ce PC        : http://127.0.0.1:8080/app/"
Write-Host "  Sur ton téléphone: " -NoNewline; Write-Host "http://${ip}:8080/app/" -ForegroundColor Green
Write-Host "  (même wifi requis · Ctrl+C pour arrêter)"
Write-Host "  ⚠  Aucune authentification : n'utilise ceci que sur un wifi de confiance." -ForegroundColor Yellow
Write-Host ""

$env:HELYOS_LLM_BACKEND = "ollama"
$env:HELYOS_MEMORY_BACKEND = "sqlite"          # persistance : les données survivent au redémarrage
$env:HELYOS_MEMORY_PATH = Join-Path (Split-Path $PSScriptRoot -Parent) "helyos_data.sqlite"
python -m uvicorn jarvis_kernel.main:app --app-dir apps/jarvis-kernel/src --host 0.0.0.0 --port 8080
