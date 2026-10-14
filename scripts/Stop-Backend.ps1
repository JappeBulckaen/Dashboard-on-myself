$pattern = 'uvicorn'
$portPids = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$portProcesses = @($portPids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
$backendProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match $pattern -and $_.CommandLine -match 'app\.main:app'
})
$workerProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ParentProcessId -in $portPids -and
    $_.Name -match '^python.*\.exe$' -and
    $_.CommandLine -match 'multiprocessing\.spawn.*spawn_main'
})

$ids = @(
    @($portProcesses) +
    @($backendProcesses | Select-Object -ExpandProperty ProcessId) +
    @($workerProcesses | Select-Object -ExpandProperty ProcessId) |
        Sort-Object -Unique
)

if (-not $ids) {
    if ($portPids) {
        $listenerIds = $portPids -join ', '
        Write-Host "Port 8000 is listening under PID $listenerIds, but no backend process could be identified."
        exit 1
    }
    Write-Host 'No backend process found.'
    exit 0
}

foreach ($id in $ids) {
    try {
        Stop-Process -Id $id -Force -ErrorAction Stop
        Write-Host "Stopped PID $id"
    }
    catch {
        Write-Host ("Could not stop PID {0}: {1}" -f $id, $_.Exception.Message)
    }
}

$remaining = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$remainingPortProcesses = @($remaining | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
$remainingProcs = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match $pattern -and $_.CommandLine -match 'app\.main:app'
})
$remainingWorkers = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ParentProcessId -in $remaining -and
    $_.Name -match '^python.*\.exe$' -and
    $_.CommandLine -match 'multiprocessing\.spawn.*spawn_main'
})

if ($remainingPortProcesses -or $remainingProcs -or $remainingWorkers) {
    $idsLeft = @(
        @($remainingPortProcesses) +
        @($remainingProcs | Select-Object -ExpandProperty ProcessId) +
        @($remainingWorkers | Select-Object -ExpandProperty ProcessId) |
            Sort-Object -Unique
    ) -join ', '
    Write-Host "Still running: $idsLeft"
    exit 1
}

if ($remaining) {
    $listenerIds = $remaining -join ', '
    Write-Host "The backend process exited, but port 8000 is still reported under PID $listenerIds."
    exit 1
}

Write-Host 'Backend stopped successfully.'
exit 0
