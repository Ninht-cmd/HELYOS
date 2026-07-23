# Serveur HELYOS RÉSILIENT — lancé au démarrage de session par la tâche planifiée.
# Boucle infinie : si le noyau s'arrête pour une raison quelconque, il redémarre
# tout seul en 3 secondes. C'est ce qui garantit « ça marche toujours ».
$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

$env:HELYOS_LLM_BACKEND = "ollama"
# cerveau le plus intelligent disponible (RTX 5070 Ti -> 14b, sinon 8b)
$models = (ollama list 2>$null | Out-String)
if ($models -match "qwen3:14b") { $env:HELYOS_LLM_MODEL = "qwen3:14b" }
elseif ($models -match "qwen3:8b") { $env:HELYOS_LLM_MODEL = "qwen3:8b" }
# persistance : les données survivent (business, caisse, prospects, commandes)
$env:HELYOS_MEMORY_BACKEND = "sqlite"
$env:HELYOS_MEMORY_PATH = Join-Path $repo "helyos_data.sqlite"

while ($true) {
    # ne démarre que si le port 8080 est libre (jamais deux noyaux en parallèle)
    $busy = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if (-not $busy) {
        python -m uvicorn jarvis_kernel.main:app --app-dir apps/jarvis-kernel/src --host 127.0.0.1 --port 8080
    }
    Start-Sleep -Seconds 3   # s'il est tombé (ou déjà occupé), on réessaie sans saturer
}
