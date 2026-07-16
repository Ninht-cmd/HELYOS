# Arrête proprement le noyau HELYOS lancé par launcher.ps1 (uvicorn sur le port 8080).
$conns = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if (-not $conns) { Write-Host "HELYOS ne tourne pas."; exit 0 }
$conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
    try { Stop-Process -Id $_ -Force -Confirm:$false; Write-Host "Noyau arrêté (PID $_)." } catch {}
}
