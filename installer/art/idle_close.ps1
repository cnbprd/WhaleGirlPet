param(
    [string]$Name = "",
    [int]$IdleSec = 1800
)
# 安装向导的看门狗：电脑连续 30 分钟没人动、且安装器还没开始装文件时，
# 静默把安装窗口关掉（避免用户走了之后窗口一直挂着）。
# 安装一开始，安装器会在同目录写 installing.flag，本脚本随即退出，绝不杀正在装的进程。

if (-not $Name) { exit }

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
public class IdleApi {
    [DllImport("user32.dll")] public static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);
    [DllImport("kernel32.dll")] public static extern uint GetTickCount();
}
"@ -ErrorAction SilentlyContinue

$flag = Join-Path $PSScriptRoot "installing.flag"

while ($true) {
    if (Test-Path -LiteralPath $flag) { exit }
    $procs = Get-Process -Name $Name -ErrorAction SilentlyContinue
    if (-not $procs) { exit }

    $lii = New-Object LASTINPUTINFO
    $lii.cbSize = [System.Runtime.InteropServices.Marshal]::SizeOf([type]'LASTINPUTINFO')
    [void][IdleApi]::GetLastInputInfo([ref]$lii)
    $idle = ([IdleApi]::GetTickCount() - $lii.dwTime) / 1000

    if ($idle -ge $IdleSec) {
        if (Test-Path -LiteralPath $flag) { exit }
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        exit
    }
    Start-Sleep -Seconds 20
}
