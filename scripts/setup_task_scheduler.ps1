# scripts/setup_task_scheduler.ps1
# KabuSys Windows Task Scheduler registration script
#
# Usage:
#   powershell -File scripts\setup_task_scheduler.ps1
#   powershell -File scripts\setup_task_scheduler.ps1 -PythonPath C:\path\to\python.exe
#
# Existing jobs are overwritten with -Force.
# Logs are appended to logs\<TaskName>.log (directory is created automatically).

param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

Write-Host "KabuSys Task Scheduler: registration start"
Write-Host "  WorkDir   : $WorkDir"
Write-Host "  PythonPath: $PythonPath"

# Create log directory
$LogsDir = Join-Path $WorkDir "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
    Write-Host "  Created log directory: $LogsDir"
}

function Register-KabuSysTask {
    param(
        [string]$TaskName,
        [string]$Script,
        [string]$Arguments = "",
        [string]$TriggerTime
    )

    # Redirect stdout and stderr to log file via cmd.exe
    # (Task Scheduler does not support shell redirection natively)
    $logFile = Join-Path $WorkDir "logs\$TaskName.log"
    $scriptArg = if ($Arguments) { "scripts\$Script $Arguments" } else { "scripts\$Script" }
    $action = New-ScheduledTaskAction -Execute "cmd.exe" `
        -Argument "/c `"$PythonPath`" $scriptArg >> `"$logFile`" 2>&1" `
        -WorkingDirectory $WorkDir

    $trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Force | Out-Null

    Write-Host "  Registered: $TaskName ($TriggerTime) -> $logFile"
}

# Night batch jobs
Register-KabuSysTask -TaskName "KabuSys_DataUpdate"            -Script "run_data_update.py"            -TriggerTime "17:30"
# Note: KabuSys_YahooNewsCollection runs but skips collection when ENABLE_YAHOONEWS is not true
Register-KabuSysTask -TaskName "KabuSys_YahooNewsCollection"   -Script "run_yahoonews_collection.py"   -TriggerTime "17:33"
Register-KabuSysTask -TaskName "KabuSys_FeatureGen"            -Script "run_feature_gen.py"            -TriggerTime "18:30"
Register-KabuSysTask -TaskName "KabuSys_AiAnalysis"            -Script "run_ai_analysis.py"            -TriggerTime "19:00"
Register-KabuSysTask -TaskName "KabuSys_StrategySignal"        -Script "run_strategy_signal.py"        -TriggerTime "20:00"
Register-KabuSysTask -TaskName "KabuSys_PortfolioConstruction" -Script "run_portfolio_construction.py" -TriggerTime "21:00"
Register-KabuSysTask -TaskName "KabuSys_NightBatchReport"      -Script "run_night_batch_report.py"      -TriggerTime "21:15"

# System start jobs
Register-KabuSysTask -TaskName "KabuSys_ExecutionStart"  -Script "start_system.py" -Arguments "--component execution"  -TriggerTime "08:30"
Register-KabuSysTask -TaskName "KabuSys_MonitoringStart" -Script "start_system.py" -Arguments "--component monitoring" -TriggerTime "09:00"

Write-Host ""
Write-Host "9 jobs registered successfully."
Write-Host "Verify: Get-ScheduledTask -TaskName 'KabuSys_*' | Select-Object TaskName, State"
