param(
    [string]$TaskName = 'WhaleGirlSoak24hSprite',
    [string]$Tag = 'soak_24h_sprite_task',
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Checkpoint = Join-Path $Root "3d\longrun_$Tag.json"
$LogPath = Join-Path $Root "3d\longrun_$Tag.log"

function Get-ParentChain([int]$ProcessId, [int]$Depth = 8) {
    $chain = @()
    $current = $ProcessId
    for ($i = 0; $i -lt $Depth -and $current -gt 0; $i++) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$current" -ErrorAction SilentlyContinue
        if (-not $p) { break }
        $chain += [pscustomobject]@{
            pid = [int]$p.ProcessId
            parent = [int]$p.ParentProcessId
            name = [string]$p.Name
        }
        $current = [int]$p.ParentProcessId
    }
    return $chain
}

if (-not (Test-Path -LiteralPath $Checkpoint)) {
    if ($Json) {
        [pscustomobject]@{ healthy = $false; error = "missing checkpoint: $Checkpoint" } |
            ConvertTo-Json -Depth 6
    } else {
        Write-Output "missing checkpoint: $Checkpoint"
    }
    exit 2
}

$data = Get-Content -LiteralPath $Checkpoint -Raw | ConvertFrom-Json
$samples = @($data.samples)
$lastSample = if ($samples.Count -gt 0) { $samples[-1] } else { $null }
$updatedAt = $null
$staleS = $null
if ($data.updated_at) {
    try {
        $updatedAt = [datetime]::Parse([string]$data.updated_at)
        $staleS = [math]::Round(((Get-Date) - $updatedAt).TotalSeconds, 1)
    } catch { }
}
$interval = if ($data.sample_interval_s) { [double]$data.sample_interval_s } else { 30.0 }
$checkpointInterval = if ($data.checkpoint_interval_s) { [double]$data.checkpoint_interval_s } else { $interval * 10 }
$staleWindow = [math]::Max($interval * 2.5, $checkpointInterval * 2.5)
$stale = ($data.status -eq 'running' -and $null -ne $staleS -and $staleS -gt $staleWindow)

$task = $null
$taskInfo = $null
$taskError = $null
try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
} catch {
    $taskError = $_.Exception.Message
}

$processAlive = $false
$process = $null
if ($data.pid) {
    $process = Get-Process -Id ([int]$data.pid) -ErrorAction SilentlyContinue
    $processAlive = $null -ne $process
}
$parentChain = if ($data.pid) { Get-ParentChain -ProcessId ([int]$data.pid) } else { @() }
$whaleCount = @(Get-Process -Name whale3d -ErrorAction SilentlyContinue).Count

$fps = @()
if (Test-Path -LiteralPath $LogPath) {
    $lines = Get-Content -LiteralPath $LogPath -Tail 2000 -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match 'fps=([0-9]+(?:\.[0-9]+)?)') { $fps += [double]$matches[1] }
    }
}

$summary = [pscustomobject]@{
    task = $TaskName
    task_state = if ($task) { [string]$task.State } else { 'missing' }
    task_result = if ($taskInfo) { [int64]$taskInfo.LastTaskResult } else { $null }
    task_result_hex = if ($taskInfo) { '0x{0:X8}' -f [uint32]$taskInfo.LastTaskResult } else { $null }
    task_error = $taskError
    tag = [string]$data.tag
    status = [string]$data.status
    pid = if ($data.pid) { [int]$data.pid } else { $null }
    process_name = if ($process) { [string]$process.ProcessName } else { $null }
    process_alive = $processAlive
    parent_chain = ($parentChain | ForEach-Object { "$($_.name)($($_.pid))" }) -join ' -> '
    whale3d_count = $whaleCount
    samples = $samples.Count
    elapsed_s = if ($lastSample) { [double]$lastSample[0] } else { $null }
    remaining_s = if ($lastSample -and $data.duration_s) { [math]::Round([double]$data.duration_s - [double]$lastSample[0], 1) } else { $null }
    rss_mb = if ($lastSample) { [math]::Round([double]$lastSample[1] / 1MB, 1) } else { $null }
    cpu_pct = if ($lastSample) { [double]$lastSample[2] } else { $null }
    fps_avg = if ($fps.Count) { [math]::Round(($fps | Measure-Object -Average).Average, 2) } else { $null }
    fps_last = if ($fps.Count) { $fps[-1] } else { $null }
    updated_at = [string]$data.updated_at
    stale_s = $staleS
    stale_window_s = $staleWindow
    stale = $stale
    healthy = ($task -ne $null -and $task.State -eq 'Running' -and $processAlive -and $process.ProcessName -eq 'whale3d' -and $data.status -eq 'running' -and -not $stale -and $whaleCount -eq 1)
}

if ($Json) {
    $summary | ConvertTo-Json -Depth 8
} else {
    $summary | Format-List
}

if (-not $summary.healthy) { exit 2 }
exit 0
