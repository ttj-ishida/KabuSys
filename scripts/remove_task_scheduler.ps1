# scripts/remove_task_scheduler.ps1
# KabuSys Windows Task Scheduler removal script
#
# Usage:
#   powershell -File scripts\remove_task_scheduler.ps1
#
# Removes all scheduled tasks whose names start with "KabuSys_".

$ErrorActionPreference = "Stop"

$tasks = Get-ScheduledTask -TaskName "KabuSys_*" -ErrorAction SilentlyContinue

if ($null -eq $tasks -or $tasks.Count -eq 0) {
    Write-Host "No KabuSys_* tasks found. Nothing to remove."
    exit 0
}

Write-Host "The following tasks will be removed:"
foreach ($task in $tasks) {
    Write-Host "  $($task.TaskName)"
}

Write-Host ""
$confirm = Read-Host "Type 'yes' to confirm removal"
if ($confirm -ne "yes") {
    Write-Host "Cancelled."
    exit 0
}

Write-Host ""
foreach ($task in $tasks) {
    Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
    Write-Host "  [REMOVED] $($task.TaskName)"
}

Write-Host ""
Write-Host "All KabuSys_* tasks removed."
