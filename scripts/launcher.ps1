# HELYOS — lanceur « façon Epic Games » :
# double-clic -> démarre le noyau s'il ne tourne pas -> ouvre HELYOS dans une
# fenêtre d'application dédiée (sans barre d'adresse, icône propre dans la
# barre des tâches). Fermer la fenêtre ne tue PAS le noyau (il continue en
# fond, comme un launcher) — pour l'arrêter : .\scripts\arreter.ps1
$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path $PSScriptRoot -Parent
$url  = "http://127.0.0.1:8080/app/"

function Test-Kernel {
    try { (Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2 -UseBasicParsing).StatusCode -eq 200 }
    catch { $false }
}

# 1) noyau : démarrer en arrière-plan (sans console) s'il ne répond pas déjà
if (-not (Test-Kernel)) {
    $env:HELYOS_LLM_BACKEND = "ollama"   # hérité par le processus enfant (PS 5.1 compatible)
    Start-Process -WindowStyle Hidden -WorkingDirectory $repo -FilePath "python" -ArgumentList @(
        "-m","uvicorn","jarvis_kernel.main:app",
        "--app-dir","apps/jarvis-kernel/src","--host","127.0.0.1","--port","8080"
    )
    # attendre que le noyau soit prêt (max ~25 s : uvicorn + imports)
    for ($i = 0; $i -lt 50 -and -not (Test-Kernel); $i++) { Start-Sleep -Milliseconds 500 }
}

# 2) fenêtre d'application : Edge (toujours présent sur Windows 11), sinon Chrome
$edge   = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe" }
$chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) { $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe" }

$browser = if (Test-Path $chrome) { $chrome } elseif (Test-Path $edge) { $edge } else { $null }
if ($browser) {
    Start-Process -FilePath $browser -ArgumentList "--app=$url","--window-size=1360,880"
} else {
    Start-Process $url   # repli : navigateur par défaut
}
