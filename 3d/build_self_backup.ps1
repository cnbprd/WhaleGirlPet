# Build the WhaleGirl 3D base prototype with the portable w64devkit + SDL3 SDK.
# No system PATH changes, no Visual Studio, no CMake.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$devkitRoot = Join-Path $root '.toolchains\w64devkit'
$gxx = Get-ChildItem -LiteralPath $devkitRoot -Filter 'g++.exe' -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $gxx) {
    throw "g++.exe not found under $devkitRoot. Run setup-toolchain.ps1 first."
}

$sdlBase = Join-Path $root '.toolchains\SDL3'
$sdlRoot = Get-ChildItem -LiteralPath $sdlBase -Directory -Filter 'SDL3-*' |
    Select-Object -First 1
if (-not $sdlRoot) {
    throw "SDL3 SDK not found under $sdlBase."
}
$sdlInclude = Join-Path $sdlRoot.FullName 'x86_64-w64-mingw32\include'
$sdlLib = Join-Path $sdlRoot.FullName 'x86_64-w64-mingw32\lib'
$sdlBin = Join-Path $sdlRoot.FullName 'x86_64-w64-mingw32\bin'

$out = Join-Path $PSScriptRoot 'whale3d.exe'
$sources = @(
    (Join-Path $PSScriptRoot 'main.cpp'),
    (Join-Path $PSScriptRoot 'model.cpp')
)
& $gxx.FullName -std=c++17 -Os -s -Wall -Wextra `
    -ffunction-sections -fdata-sections `
    "-I$PSScriptRoot" "-I$sdlInclude" `
    $sources `
    "-L$sdlLib" -lSDL3 -lopengl32 -lgdi32 -luser32 `
    -static-libgcc -static-libstdc++ `
    "-Wl,--gc-sections" `
    -o $out
if ($LASTEXITCODE -ne 0) { throw "g++ failed with exit code $LASTEXITCODE" }

Copy-Item -LiteralPath (Join-Path $sdlBin 'SDL3.dll') -Destination (Join-Path $PSScriptRoot 'SDL3.dll') -Force

Get-Item -LiteralPath $out, (Join-Path $PSScriptRoot 'SDL3.dll') |
    Select-Object Name, @{n='MB';e={[math]::Round($_.Length / 1MB, 2)}}, Length |
    Format-Table -AutoSize

Write-Host "Build OK: $out"
