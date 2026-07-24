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

# OBSERVABILITÉ : on capture la sortie du noyau ET on trace chaque (re)démarrage.
# Sans ça, un ingénieur ne peut pas savoir SI/POURQUOI le noyau tombe. On mesure.
$log = Join-Path $repo "helyos_serveur.log"
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -Append -Encoding utf8 $log }

Log "=== serveur resilient demarre (surveillance) ==="
while ($true) {
    # ne démarre que si le port 8080 est libre (jamais deux noyaux en parallèle)
    $busy = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if (-not $busy) {
        Log "noyau LANCE (modele=$($env:HELYOS_LLM_MODEL))"
        # 2>&1 : stderr (les tracebacks) va DANS le log -> on saura enfin pourquoi il meurt
        python -m uvicorn jarvis_kernel.main:app --app-dir apps/jarvis-kernel/src --host 127.0.0.1 --port 8080 *>> $log
        Log "noyau ARRETE (code=$LASTEXITCODE) -> relance dans 3s"
    }
    Start-Sleep -Seconds 3   # s'il est tombé (ou déjà occupé), on réessaie sans saturer
}
