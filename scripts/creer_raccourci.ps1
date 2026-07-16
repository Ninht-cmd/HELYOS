# Crée l'icône HELYOS.ico (depuis le logo PWA existant) + le raccourci Bureau.
# À lancer UNE fois : ensuite, double-clic sur « HELYOS » sur le Bureau = lancement façon launcher.
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent

# 1) icône : ICO moderne = un conteneur autour du PNG (aucune dépendance)
$py = @'
import struct, sys
png = open(sys.argv[1], "rb").read()
w = h = 180 % 256
ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), 22) + png
open(sys.argv[2], "wb").write(ico)
print("icone OK")
'@
$tmp = Join-Path $env:TEMP "helyos_ico.py"
Set-Content -Path $tmp -Value $py -Encoding utf8
python $tmp (Join-Path $repo "apps\jarvis-kernel\web\icon-180.png") (Join-Path $repo "scripts\HELYOS.ico")

# 2) raccourci Bureau -> launcher.ps1 (fenêtre PowerShell invisible)
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path $desktop "HELYOS.lnk"))
$lnk.TargetPath = "powershell.exe"
$lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$repo\scripts\launcher.ps1`""
$lnk.WorkingDirectory = $repo
$lnk.IconLocation = "$repo\scripts\HELYOS.ico"
$lnk.Description = "HELYOS — ton OS de holding (noyau local + fenetre d'application)"
$lnk.Save()
Write-Host "Raccourci cree : $desktop\HELYOS.lnk"
