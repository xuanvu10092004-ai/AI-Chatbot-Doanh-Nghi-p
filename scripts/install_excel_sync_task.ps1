param([string]$Python = 'pythonw.exe', [string]$TaskName = 'PortalExcelSync')
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$worker = Join-Path $workspace 'excel_sync_worker.py'
$pythonPath = (Get-Command $Python -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath (Join-Path $workspace '.env'))) { throw 'Thiếu .env trong workspace.' }
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"' + $worker + '" --interval 2') -WorkingDirectory $workspace
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Đồng bộ MySQL dùng chung sang Excel; không cần mở trình duyệt' | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output "Đã cài và khởi động $TaskName cho người dùng hiện tại. Log: data/exports/excel_sync_worker.log"
