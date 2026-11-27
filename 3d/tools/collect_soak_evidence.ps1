param(
    [string]$TaskName = 'WhaleGirlSoak24hSprite',
    [string]$Tag = 'soak_24h_sprite_task',
    [string]$OutDir = 'docs\soak-evidence',
    [int]$TailLines = 80,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Checkpoint = Join-Path $Root "3d\longrun_$Tag.json"
$LogPath = Join-Path $Root "3d\longrun_$Tag.log"
$ErrPath = Join-Path $Root "3d\longrun_$Tag.err.log"

function Get-ProcessChain([int]$ProcessId, [int]$Depth = 8) {
    $chain = @()
    $current = $ProcessId
    for ($i = 0; $i -lt $Depth -and $current -gt 0; $i++) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$current" -ErrorAction SilentlyContinue
        if (-not $p) { break }
        $chain += [pscustomobject]@{
            pid = [int]$p.ProcessId
            parent = [int]$p.ParentProcessId
            name = [string]$p.Name
            command_line = [string]$p.CommandLine
        }
        $current = [int]$p.ParentProcessId
    }
    return $chain
}

function Get-EventSnapshot([datetime]$Since) {
    $items = @()
    $queries = @(
        @{ LogName = 'Application'; ProviderName = 'Application Error'; StartTime = $Since },
        @{ LogName = 'Application'; ProviderName = 'Windows Error Reporting'; StartTime = $Since },
        @{ LogName = 'System'; Id = 41, 6008; StartTime = $Since }
    )
    foreach ($query in $queries) {
        try {
            $events = Get-WinEvent -FilterHashtable $query -MaxEvents 20 -ErrorAction Stop
            foreach ($event in $events) {
                $message = [string]$event.Message
                if ($message.Length -gt 1500) { $message = $message.Substring(0, 1500) }
                $items += [pscustomobject]@{
                    time = $event.TimeCreated.ToString('o')
                    id = [int]$event.Id
                    provider = [string]$event.ProviderName
                    level = [string]$event.LevelDisplayName
                    message = $message
                }
            }
        } catch {
            # No matching events is normal.
        }
    }
    return $items
}

$data = $null
$checkpointMissing = -not (Test-Path -LiteralPath (Join-Path $Root "3d\longrun_$Tag.json"))
if (-not $checkpointMissing) {
    try {
        $data = Get-Content -LiteralPath $Checkpoint -Raw | ConvertFrom-Json
    } catch {
        $checkpointMissing = $true
    }
}

$task = $null
$taskInfo = $null
$taskError = $null
try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
} catch {
    $taskError = $_.Exception.Message
}

$targetPid = if ($data -and $data.pid) { [int]$data.pid } else { $null }
$process = if ($targetPid) { Get-Process -Id $targetPid -ErrorAction SilentlyContinue } else { $null }
$processAlive = $null -ne $process
$parentChain = if ($targetPid) { Get-ProcessChain -ProcessId $targetPid } else { @() }
$whaleProcesses = @(Get-CimInstance Win32_Process -Filter "Name='whale3d.exe'" -ErrorAction SilentlyContinue)
$whaleCount = $whaleProcesses.Count

$updatedAt = $null
$staleS = $null
if ($data -and $data.updated_at) {
    try {
        $updatedAt = [datetime]::Parse([string]$data.updated_at)
        $staleS = [math]::Round(((Get-Date) - $updatedAt).TotalSeconds, 1)
    } catch { }
}
$interval = if ($data -and $data.sample_interval_s) { [double]$data.sample_interval_s } else { 30.0 }
$checkpointInterval = if ($data -and $data.checkpoint_interval_s) { [double]$data.checkpoint_interval_s } else { $interval * 10 }
$staleWindow = [math]::Max($interval * 2.5, $checkpointInterval * 2.5)
$stale = ($data -and $data.status -eq 'running' -and $null -ne $staleS -and $staleS -gt $staleWindow)

$samples = if ($data) { @($data.samples) } else { @() }
$lastSample = if ($samples.Count -gt 0) { $samples[-1] } else { $null }
$checkpointStatus = if ($data) { [string]$data.status } else { 'missing' }
$taskState = if ($task) { [string]$task.State } else { 'missing' }

$verdict = 'unknown'
if ($checkpointMissing) {
    $verdict = 'checkpoint_missing'
} elseif ($checkpointStatus -eq 'done' -and $processAlive) {
    $verdict = 'completed'
} elseif ($checkpointStatus -eq 'done' -and -not $processAlive) {
    $verdict = 'completed_process_dead'
} elseif ($checkpointStatus -eq 'running' -and $processAlive -and $whaleCount -eq 1 -and $taskState -eq 'Running' -and -not $stale) {
    $verdict = 'running_healthy'
} elseif ($checkpointStatus -eq 'running' -and -not $processAlive) {
    $verdict = 'running_process_gone'
} elseif ($taskState -ne 'Running' -and $processAlive) {
    $verdict = 'task_not_running_process_alive'
} elseif ($checkpointStatus -eq 'running' -and $stale) {
    $verdict = 'running_stale'
}

$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$disks = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction SilentlyContinue |
    Select-Object DeviceID, Size, FreeSpace)
$startedAt = if ($data -and $data.started_at) {
    try { [datetime]::Parse([string]$data.started_at) } catch { (Get-Date).AddHours(-24) }
} else {
    (Get-Date).AddHours(-24)
}
$events = Get-EventSnapshot -Since $startedAt

$summary = [pscustomobject]@{
    collected_at = (Get-Date).ToString('o')
    task = $TaskName
    task_state = $taskState
    task_error = $taskError
    task_info = if ($taskInfo) {
        [pscustomobject]@{
            last_run_time = if ($taskInfo.LastRunTime) { $taskInfo.LastRunTime.ToString('o') } else { $null }
            last_task_result = [int64]$taskInfo.LastTaskResult
            last_task_result_hex = '0x{0:X8}' -f [uint32]$taskInfo.LastTaskResult
            next_run_time = if ($taskInfo.NextRunTime) { $taskInfo.NextRunTime.ToString('o') } else { $null }
            number_of_missed_runs = [int]$taskInfo.NumberOfMissedRuns
        }
    } else { $null }
    tag = $Tag
    checkpoint_path = $Checkpoint
    checkpoint_status = $checkpointStatus
    checkpoint_updated_at = if ($data) { [string]$data.updated_at } else { $null }
    checkpoint_started_at = if ($data) { [string]$data.started_at } else { $null }
    sample_count = $samples.Count
    elapsed_s = if ($lastSample) { [double]$lastSample[0] } else { $null }
    remaining_s = if ($lastSample -and $data -and $data.duration_s) { [math]::Round([double]$data.duration_s - [double]$lastSample[0], 1) } else { $null }
    target_pid = $targetPid
    process_name = if ($process) { [string]$process.ProcessName } else { $null }
    process_alive = $processAlive
    pid_reused = ($targetPid -and $process -and $process.ProcessName -ne 'whale3d')
    parent_chain = $parentChain
    whale3d_count = $whaleCount
    whale3d_processes = @($whaleProcesses | ForEach-Object {
        [pscustomobject]@{ pid = [int]$_.ProcessId; command_line = [string]$_.CommandLine }
    })
    stale_s = $staleS
    stale_window_s = $staleWindow
    stale = $stale
    verdict = $verdict
    log = [pscustomobject]@{
        path = $LogPath
        exists = Test-Path -LiteralPath $LogPath
        length = if (Test-Path -LiteralPath $LogPath) { (Get-Item -LiteralPath $LogPath).Length } else { $null }
        last_write = if (Test-Path -LiteralPath $LogPath) { (Get-Item -LiteralPath $LogPath).LastWriteTime.ToString('o') } else { $null }
        tail = if (Test-Path -LiteralPath $LogPath) { @(Get-Content -LiteralPath $LogPath -Tail $TailLines -ErrorAction SilentlyContinue) } else { @() }
    }
    err = [pscustomobject]@{
        path = $ErrPath
        exists = Test-Path -LiteralPath $ErrPath
        length = if (Test-Path -LiteralPath $ErrPath) { (Get-Item -LiteralPath $ErrPath).Length } else { $null }
        last_write = if (Test-Path -LiteralPath $ErrPath) { (Get-Item -LiteralPath $ErrPath).LastWriteTime.ToString('o') } else { $null }
        tail = if (Test-Path -LiteralPath $ErrPath) { @(Get-Content -LiteralPath $ErrPath -Tail $TailLines -ErrorAction SilentlyContinue) } else { @() }
    }
    system = [pscustomobject]@{
        os_caption = if ($os) { [string]$os.Caption } else { $null }
        last_boot = if ($os) { $os.LastBootUpTime.ToString('o') } else { $null }
        uptime_s = if ($os) { [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalSeconds, 1) } else { $null }
        total_memory_mb = if ($os) { [math]::Round([double]$os.TotalVisibleMemorySize / 1KB, 1) } else { $null }
        free_memory_mb = if ($os) { [math]::Round([double]$os.FreePhysicalMemory / 1KB, 1) } else { $null }
        disks = $disks
    }
    event_since = $startedAt.ToString('o')
    events = @($events)
}

if ($DryRun) {
    $summary | ConvertTo-Json -Depth 10
    exit 0
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outRoot = Join-Path $Root $OutDir
$evidenceDir = Join-Path $outRoot "$Tag-$stamp"
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null

$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $evidenceDir 'summary.json') -Encoding UTF8

if (Test-Path -LiteralPath $Checkpoint) {
    Copy-Item -LiteralPath $Checkpoint -Destination (Join-Path $evidenceDir 'checkpoint.json') -Force
}
if (Test-Path -LiteralPath $LogPath) {
    $logTail = @(Get-Content -LiteralPath $LogPath -Tail $TailLines -ErrorAction SilentlyContinue)
    Set-Content -LiteralPath (Join-Path $evidenceDir 'longrun.log.tail.txt') -Value (($logTail | Out-String).TrimEnd()) -Encoding UTF8
}
if (Test-Path -LiteralPath $ErrPath) {
    $errTail = @(Get-Content -LiteralPath $ErrPath -Tail $TailLines -ErrorAction SilentlyContinue)
    Set-Content -LiteralPath (Join-Path $evidenceDir 'longrun.err.log.tail.txt') -Value (($errTail | Out-String).TrimEnd()) -Encoding UTF8
}
$chainJson = if (@($parentChain).Count -gt 0) { @($parentChain) | ConvertTo-Json -Depth 5 } else { '[]' }
Set-Content -LiteralPath (Join-Path $evidenceDir 'process-chain.json') -Value $chainJson -Encoding UTF8
$eventsJson = if (@($events).Count -gt 0) { @($events) | ConvertTo-Json -Depth 5 } else { '[]' }
Set-Content -LiteralPath (Join-Path $evidenceDir 'events.json') -Value $eventsJson -Encoding UTF8

$md = @(
    "# Soak evidence",
    "",
    "- collected_at: $($summary.collected_at)",
    "- task: $TaskName",
    "- task_state: $taskState",
    "- checkpoint_status: $checkpointStatus",
    "- target_pid: $targetPid",
    "- process_alive: $processAlive",
    "- whale3d_count: $whaleCount",
    "- stale_s: $staleS",
    "- verdict: $verdict",
    "",
    "## Files",
    "",
    "- summary.json",
    "- checkpoint.json (if exists)",
    "- longrun.log.tail.txt",
    "- longrun.err.log.tail.txt",
    "- process-chain.json",
    "- events.json"
) -join "`n"
Set-Content -LiteralPath (Join-Path $evidenceDir 'README.md') -Value $md -Encoding UTF8

Write-Output "evidence_dir=$evidenceDir"
Write-Output "verdict=$verdict task_state=$taskState checkpoint_status=$checkpointStatus process_alive=$processAlive whale3d_count=$whaleCount stale_s=$staleS"
exit 0
