# Installe HELYOS en SERVICE toujours actif — SANS droits admin.
#
# Méthode : un raccourci dans le dossier Démarrage de Windows lance le serveur
# résilient (serveur.ps1) à chaque ouverture de session. serveur.ps1 boucle et
# redémarre le noyau tout seul s'il tombe. Résultat : « ça marche toujours ».
#
# À lancer UNE fois (double-clic ou clic droit -> Exécuter avec PowerShell).
# Pour retirer : .\scripts\desinstaller_service.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent

# 1) raccourci dans le dossier Démarrage (lancé automatiquement à chaque session)
$startup = [Environment]::GetFolderPath("Startup")
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path $startup "HELYOS-serveur.lnk"))
$lnk.TargetPath = "powershell.exe"
$lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$repo\scripts\serveur.ps1`""
$lnk.WorkingDirectory = $repo
$lnk.WindowStyle = 7          # minimisé/caché
$lnk.Description = "Noyau HELYOS - serveur resilient (redemarre seul)"
$lnk.Save()

# 2) démarrer tout de suite (détaché), s'il ne tourne pas déjà
$up = $false
try { Invoke-WebRequest "http://127.0.0.1:8080/health" -TimeoutSec 3 -UseBasicParsing | Out-Null; $up = $true } catch {}
if (-not $up) {
    Start-Process -WindowStyle Hidden -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-WindowStyle","Hidden","-File","`"$repo\scripts\serveur.ps1`""
}

Write-Host ""
Write-Host "  HELYOS est maintenant un service permanent (sans admin)." -ForegroundColor Green
Write-Host "  - Demarre a chaque ouverture de session Windows."
Write-Host "  - Redemarre tout seul s'il s'arrete."
Write-Host "  - Raccourci Demarrage : $startup\HELYOS-serveur.lnk"
Write-Host "  Ouvre HELYOS : double-clic sur l'icone du Bureau."
Write-Host ""
