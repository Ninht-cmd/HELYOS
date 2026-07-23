param(
  [string]$Node = "C:\Users\emezr\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
  [string]$HelyosRoot = "C:\Users\emezr\Desktop\HELYOS",
  [string]$NvidiaLabRoot = "C:\Users\emezr\WORKSPACE\NVIDIA-LAB",
  [string]$OpenSourceLabRoot = "C:\Users\emezr\WORKSPACE\OPEN-SOURCE-LAB",
  [string]$OutputDir = "C:\Users\emezr\Desktop\HELYOS\data\business-state"
)

$ErrorActionPreference = "Stop"

$env:HELYOS_ROOT = $HelyosRoot
$env:JARVIS_ROOT = Join-Path $HelyosRoot "apps\jarvis-kernel"
$env:NVIDIA_LAB_ROOT = $NvidiaLabRoot
$env:OPEN_SOURCE_LAB_ROOT = $OpenSourceLabRoot
$env:BUSINESS_STATE_OUT = $OutputDir

$builder = Join-Path $HelyosRoot "scripts\build-business-state-workbook.mjs"
& $Node $builder
