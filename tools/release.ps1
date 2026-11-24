# -*- coding: utf-8 -*-
<#
一键发版（v2.9.7 第 1 条：每次新版本都及时进 git 仓库）

用法（在 F:\WhaleGirlPet 下执行）：
    .\tools\release.ps1                 # 用当前版本号打包 + 提交 + 推送
    .\tools\release.ps1 -Bump -Note "零食商城上线"   # 版本号末位 +1 再走一遍
    .\tools\release.ps1 -SkipBuild       # 只提交推送（代码改动不涉及打包时）

做的事：
1) （可选）把 app/paths.py 的 APP_VERSION 末位 +1
2) PyInstaller 打包 dist\WhaleGirlPet.exe
3) Inno 编译 dist\WhaleGirlPet-Setup-<版本>.exe
4) git add -A / commit / push origin main
5) 打印 CI 地址（.github/workflows 里 push 后自动建 Release 并上传资产）
#>
param(
    [switch]$Bump,
    [switch]$SkipBuild,
    [string]$Note = ""
)

$ErrorActionPreference = "Stop"
$Root = "F:\WhaleGirlPet"
Set-Location $Root

function Get-Version {
    $line = Select-String -Path "$Root\app\paths.py" -Pattern 'APP_VERSION\s*=\s*"([0-9.]+)"'
    return $line.Matches[0].Groups[1].Value
}

if ($Bump) {
    $old = Get-Version
    $parts = $old.Split(".")
    $parts[-1] = [string]([int]$parts[-1] + 1)
    $new = $parts -join "."
    $py = Get-Content "$Root\app\paths.py" -Raw
    $py = $py -replace ('APP_VERSION = "' + [regex]::Escape($old) + '"'), ('APP_VERSION = "' + $new + '"')
    [System.IO.File]::WriteAllText("$Root\app\paths.py", $py, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "版本号：$old -> $new"
} else {
    $new = Get-Version
    Write-Host "使用现有版本号：$new"
}

if (-not $SkipBuild) {
    Write-Host "[1/3] PyInstaller 打包 …"
    & "$Root\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean WhaleGirlPet.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败（$LASTEXITCODE）" }

    Write-Host "[2/3] Inno 编译安装包 …"
    & "$Root\tools\inno\ISCC.exe" "$Root\installer\whale_pet.iss"
    if ($LASTEXITCODE -ne 0) { throw "ISCC 失败（$LASTEXITCODE）" }
}

$setup = "$Root\dist\WhaleGirlPet-Setup-$new.exe"
if (-not $SkipBuild -and -not (Test-Path $setup)) { throw "没找到安装包：$setup" }

Write-Host "[3/3] 提交并推送 …"
git add -A
$msg = if ($Note) { "v$new $Note" } else { "v$new" }
git commit -m $msg
if ($LASTEXITCODE -ne 0) { Write-Host "没有需要提交的改动，继续推送已有提交" }
git push origin main
if ($LASTEXITCODE -ne 0) { throw "git push 失败（$LASTEXITCODE）" }

Write-Host ""
Write-Host "完成：v$new 已推送。CI 会自动编译并建 Release："
Write-Host "  https://github.com/cnbprd/WhaleGirlPet/actions"
Write-Host "  https://github.com/cnbprd/WhaleGirlPet/releases"
if (Test-Path $setup) {
    $size = (Get-Item $setup).Length
    Write-Host ("安装包：{0}（{1:N0} 字节）" -f $setup, $size)
}
