# Extract the portable toolchain into the project, without touching PATH.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root '.toolchains'
$sfx = Join-Path $tools 'w64devkit-x64-2.11.0.7z.exe'
$dst = Join-Path $tools 'w64devkit'

if (-not (Test-Path -LiteralPath $sfx)) {
    throw "Missing $sfx"
}

$gxx = Get-ChildItem -LiteralPath $dst -Filter 'g++.exe' -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $gxx) {
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    & $sfx -y "-o$dst"
    # The SFX may return an empty exit code even on success; verify the binary instead.
    Start-Sleep -Milliseconds 500
    $gxx = Get-ChildItem -LiteralPath $dst -Filter 'g++.exe' -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if (-not $gxx) { throw "g++.exe still missing under $dst" }
& $gxx.FullName --version
