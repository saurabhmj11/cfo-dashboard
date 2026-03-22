
$ports = @(8000, 3000)
foreach ($port in $ports) {
    $process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($process) {
        $pid_val = $process.OwningProcess
        Write-Host "Killing process $pid_val on port $port"
        Stop-Process -Id $pid_val -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "No process found on port $port"
    }
}
ipconfig /flushdns
