# Migrate a legacy 2D install without running its broken uninstaller.
#
# The 3.0.27 uninstaller calls ExtractTemporaryFile() from InitializeUninstall(),
# which Inno Setup rejects with "Cannot call ExtractTemporaryFile function during
# Uninstall." The uninstaller therefore exits 1 and never removes the old app.
# This helper moves the user's data aside, removes the old program files/registry
# entry, then moves the data back. If anything fails, it restores the moved data.
param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [string]$UninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\鲸鱼娘桌宠_is1',
    [switch]$SkipShortcuts
)
$ErrorActionPreference = 'Stop'

$items = @(
    'config.json', 'accounts.json', 'memory.db', 'knowledge.db', 'accounts',
    'voices', 'tts_cache', 'workspace', 'reports', 'quarantine', 'scripts',
    'models', 'runtime', 'updates', 'ollama_library.json'
)
$moved = @()

function Restore-Data {
    foreach ($name in $moved) {
        $src = Join-Path $BackupDir $name
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $dst = Join-Path $AppDir $name
        if (Test-Path -LiteralPath $dst) {
            Remove-Item -LiteralPath $dst -Recurse -Force
        }
        Move-Item -LiteralPath $src -Destination $dst -Force
    }
    if (Test-Path -LiteralPath $BackupDir) {
        Remove-Item -LiteralPath $BackupDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

try {
    if (-not (Test-Path -LiteralPath $AppDir)) {
        throw "legacy app directory not found: $AppDir"
    }
    if (Test-Path -LiteralPath $BackupDir) {
        throw "backup directory already exists: $BackupDir"
    }

    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    foreach ($name in $items) {
        $src = Join-Path $AppDir $name
        if (-not (Test-Path -LiteralPath $src)) { continue }
        Move-Item -LiteralPath $src -Destination (Join-Path $BackupDir $name) -Force
        $moved += $name
    }

    # 2D onedir install: app code lives in WhaleGirlPet.exe + _internal.
    foreach ($name in @('_internal', 'WhaleGirlPet.exe', 'unins000.exe', 'unins000.dat', 'copy_models.cmd', 'README.md')) {
        $path = Join-Path $AppDir $name
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }

    # Old shortcuts. Missing shortcuts are not fatal.
    if (-not $SkipShortcuts) {
        $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\鲸鱼娘桌宠'
        if (Test-Path -LiteralPath $startMenu) {
            Remove-Item -LiteralPath $startMenu -Recurse -Force -ErrorAction SilentlyContinue
        }
        $desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) '鲸鱼娘桌宠.lnk'
        if (Test-Path -LiteralPath $desktop) {
            Remove-Item -LiteralPath $desktop -Force -ErrorAction SilentlyContinue
        }
    }

    # Remove the old uninstall record so the new installer owns the upgrade path.
    if (Test-Path -LiteralPath $UninstallKey) {
        Remove-Item -LiteralPath $UninstallKey -Recurse -Force
    }

    Restore-Data
} catch {
    try {
        Restore-Data
    } catch {
        Write-Error "legacy migration failed and data restore also failed: $($_.Exception.Message)"
    }
    Write-Error "legacy migration failed: $($_.Exception.Message)"
    exit 1
}
exit 0
