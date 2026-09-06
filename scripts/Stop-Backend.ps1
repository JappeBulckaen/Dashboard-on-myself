$pattern = 'uvicorn app.main:app --reload'
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $pattern }

if (-not $procs) {
    Write-Host 'No backend process found.'
    exit 0
}

foreach ($p in $procs) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped PID $($p.ProcessId)"
    }
    catch {
        Write-Host "Could not stop PID $($p.ProcessId): $($_.Exception.Message)"
    }
}

$remaining = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $pattern }

if ($remaining) {
    $ids = ($remaining | ForEach-Object { $_.ProcessId }) -join ', '
    Write-Host "Still running: $ids"
    exit 1
}

Write-Host 'Backend stopped successfully.'
exit 0
