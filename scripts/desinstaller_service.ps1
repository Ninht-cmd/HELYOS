# Retire le service HELYOS (raccourci Démarrage) et arrête le noyau.
$ErrorActionPreference = "SilentlyContinue"
$startup = [Environment]::GetFolderPath("Startup")
Remove-Item (Join-Path $startup "HELYOS-serveur.lnk") -Force
& "$PSScriptRoot\arreter.ps1"
Write-Host "Service HELYOS desinstalle (le raccourci Demarrage a ete retire)." -ForegroundColor Yellow
