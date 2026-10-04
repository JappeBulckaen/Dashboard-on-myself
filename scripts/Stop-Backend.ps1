$pattern = 'uvicorn'
$portPids = @(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -match $pattern -and $_.CommandLine -match 'app\.main:app') -or ($_.ProcessId -in $portPids)
}

$ids = @($procs | Select-Object -ExpandProperty ProcessId | Sort-Object -Unique)

if (-not $ids) {
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

$remaining = @(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$remainingProcs = Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -match $pattern -and $_.CommandLine -match 'app\.main:app') -or ($_.ProcessId -in $remaining)
}

if ($remainingProcs) {
    $idsLeft = ($remainingProcs | Select-Object -ExpandProperty ProcessId | Sort-Object -Unique) -join ', '
    Write-Host "Still running: $idsLeft"
    exit 1
}

Write-Host 'Backend stopped successfully.'
exit 0
