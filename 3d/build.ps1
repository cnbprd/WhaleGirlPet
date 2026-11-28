# Build the WhaleGirl 3D base prototype with the portable w64devkit + SDL3 SDK.
# No system PATH changes, no Visual Studio, no CMake.
param(
    [string]$DevkitRoot = '',
    [string]$SdlBase = '',
    [string]$OutFile = ''
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$devkitRoot = if ($DevkitRoot) { (Resolve-Path -LiteralPath $DevkitRoot).Path } else { Join-Path $root '.toolchains\w64devkit' }
$gxx = Get-ChildItem -LiteralPath $devkitRoot -Filter 'g++.exe' -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $gxx) {
    throw "g++.exe not found under $devkitRoot. Run setup-toolchain.ps1 first."
}

$sdlBase = if ($SdlBase) { (Resolve-Path -LiteralPath $SdlBase).Path } else { Join-Path $root '.toolchains\SDL3' }
$sdlRoot = Get-ChildItem -LiteralPath $sdlBase -Directory -Filter 'SDL3-*' |
    Select-Object -First 1
if (-not $sdlRoot) {
    throw "SDL3 SDK not found under $sdlBase."
}
$sdlInclude = Join-Path $sdlRoot.FullName 'x86_64-w64-mingw32\include'
$sdlLib = Join-Path $sdlRoot.FullName 'x86_64-w64-mingw32\lib'
$sdlBin = Join-Path $sdlRoot.FullName 'x86_64-w64-mingw32\bin'

$out = if ($OutFile) { $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutFile) } else { Join-Path $PSScriptRoot 'whale3d.exe' }
$windres = Get-ChildItem -LiteralPath $devkitRoot -Filter 'windres.exe' -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $windres) {
    throw "windres.exe not found under $devkitRoot."
}
$resourceObj = Join-Path $PSScriptRoot 'whale3d.res.o'
& $windres.FullName -O coff -o $resourceObj (Join-Path $PSScriptRoot 'whale3d.rc')
if ($LASTEXITCODE -ne 0) { throw "windres failed with exit code $LASTEXITCODE" }
$ozzSrc = Join-Path $PSScriptRoot 'third_party\ozz-animation-master'
$ozzBuild = Join-Path $PSScriptRoot 'third_party\ozz-build'
$ozzInclude = Join-Path $ozzSrc 'include'
$ozzLibOffline = Join-Path $ozzBuild 'src\animation\offline'
$ozzLibRuntime = Join-Path $ozzBuild 'src\animation\runtime'
$ozzLibBase = Join-Path $ozzBuild 'src\base'
foreach ($p in @($ozzInclude, $ozzLibOffline, $ozzLibRuntime, $ozzLibBase)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "ozz build input missing: $p. Build ozz first (see README)."
    }
}
$sources = @(
    (Join-Path $PSScriptRoot 'main.cpp'),
    (Join-Path $PSScriptRoot 'model.cpp'),
    (Join-Path $PSScriptRoot 'shell_ui.cpp'),
    (Join-Path $PSScriptRoot 'emotion_bus.cpp'),
    (Join-Path $PSScriptRoot 'sprite.cpp'),
    (Join-Path $PSScriptRoot 'sprite_manifest.cpp'),
    $resourceObj
)
& $gxx.FullName -std=c++17 -Os -s -Wall -Wextra -mwindows `
    -DWHALE3D_USE_OZZ `
    -ffunction-sections -fdata-sections `
    "-I$PSScriptRoot" "-I$sdlInclude" "-I$ozzInclude" `
    $sources `
    "-L$sdlLib" "-L$ozzLibOffline" "-L$ozzLibRuntime" "-L$ozzLibBase" `
    -lSDL3 -lozz_animation_offline_r -lozz_animation_r -lozz_base_r `
    -lopengl32 -lgdi32 -luser32 -lshell32 -ladvapi32 -lws2_32 -lpsapi `
    -static-libgcc -static-libstdc++ `
    "-Wl,--gc-sections" `
    -o $out
if ($LASTEXITCODE -ne 0) { throw "g++ failed with exit code $LASTEXITCODE" }

Copy-Item -LiteralPath (Join-Path $sdlBin 'SDL3.dll') -Destination (Join-Path $PSScriptRoot 'SDL3.dll') -Force

Get-Item -LiteralPath $out, (Join-Path $PSScriptRoot 'SDL3.dll') |
    Select-Object Name, @{n='MB';e={[math]::Round($_.Length / 1MB, 2)}}, Length |
    Format-Table -AutoSize

Write-Host "Build OK: $out"
