param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$iscc = Join-Path $repo 'tools\inno\ISCC.exe'
$iss = Join-Path $repo 'installer\whale3d.iss'
$payloadRoot = Join-Path $repo 'build\3d-installer-payload'
$outDir = Join-Path $repo 'dist\3d'

if (-not (Test-Path -LiteralPath $iscc)) { throw "Inno Setup compiler not found: $iscc" }
if (-not (Test-Path -LiteralPath $iss)) { throw "Installer script not found: $iss" }

$packages = @(
    @{ Version = '3.2.0'; Zip = '3d\whale3d-whale-girl-v3.2-dev.zip'; Suffix = '-dev' },
    @{ Version = '3.1.2'; Zip = '3d\whale3d-whale-girl-v3.zip' },
    @{ Version = '3.1.0'; Zip = '3d\whale3d-whale-girl-v2.zip' },
    @{ Version = '3.0.28'; Zip = '3d\whale3d-whale-girl-v1.zip' }
)

New-Item -ItemType Directory -Path $outDir -Force | Out-Null
if (Test-Path -LiteralPath $payloadRoot) { Remove-Item -LiteralPath $payloadRoot -Recurse -Force }
New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null

$results = @()
foreach ($pkg in $packages) {
    $zip = Join-Path $repo $pkg.Zip
    if (-not (Test-Path -LiteralPath $zip)) { throw "Package not found: $zip" }

    $payload = Join-Path $payloadRoot $pkg.Version
    New-Item -ItemType Directory -Path $payload -Force | Out-Null
    Expand-Archive -LiteralPath $zip -DestinationPath $payload -Force

    & $iscc "/DAppVersion=$($pkg.Version)" "/DBuildSuffix=$($pkg.Suffix)" "/DPayloadDir=$payload" $iss
    if ($LASTEXITCODE -ne 0) { throw "ISCC failed for $($pkg.Version) (exit $LASTEXITCODE)" }

    $setup = Join-Path $outDir "WhaleGirlPet-Setup-$($pkg.Version)$($pkg.Suffix).exe"
    if (-not (Test-Path -LiteralPath $setup)) { throw "Setup output missing: $setup" }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash.ToLowerInvariant()
    $shaFile = "$setup.sha256"
    Set-Content -LiteralPath $shaFile -Value "$hash  $([IO.Path]::GetFileName($setup))" -Encoding ascii
    $results += [pscustomobject]@{
        Version = $pkg.Version
        Setup = $setup
        Bytes = (Get-Item -LiteralPath $setup).Length
        SHA256 = $hash
    }
}

$results | Format-Table -AutoSize
