# 卸载时"保留数据"用：先把用户数据移到同盘的备份目录，卸载完再搬回来。
param(
  [Parameter(Mandatory = $true)][ValidateSet('out', 'back')][string]$Mode,
  [Parameter(Mandatory = $true)][string]$AppDir,
  [Parameter(Mandatory = $true)][string]$BackupDir
)
$ErrorActionPreference = 'Stop'
$items = @(
  'config.json', 'accounts.json', 'memory.db', 'knowledge.db', 'accounts',
  'voices', 'tts_cache', 'workspace', 'reports', 'quarantine', 'scripts',
  'models', 'runtime', 'updates', 'ollama_library.json'
)
if ($Mode -eq 'out') {
  New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
  foreach ($name in $items) {
    $src = Join-Path $AppDir $name
    if (-not (Test-Path -LiteralPath $src)) { continue }
    $dst = Join-Path $BackupDir $name
    if (Test-Path -LiteralPath $dst) { Remove-Item -LiteralPath $dst -Recurse -Force }
    Move-Item -LiteralPath $src -Destination $dst -Force
  }
} else {
  if (-not (Test-Path -LiteralPath $BackupDir)) { return }
  New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
  foreach ($name in $items) {
    $src = Join-Path $BackupDir $name
    if (-not (Test-Path -LiteralPath $src)) { continue }
    $dst = Join-Path $AppDir $name
    if (Test-Path -LiteralPath $dst) { Remove-Item -LiteralPath $dst -Recurse -Force }
    Move-Item -LiteralPath $src -Destination $dst -Force
  }
  Remove-Item -LiteralPath $BackupDir -Recurse -Force -ErrorAction SilentlyContinue
}
