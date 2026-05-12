# scripts/setup_task_scheduler.ps1
# KabuSys Windows Task Scheduler registration script
#
# Usage:
#   powershell -File scripts\setup_task_scheduler.ps1
#   powershell -File scripts\setup_task_scheduler.ps1 -PythonPath C:\path\to\python.exe
#
# Core jobs are always registered.
# Addon jobs are registered only when the corresponding flag is true in .env:
#   ENABLE_YAHOONEWS=true  -> KabuSys_YahooNewsCollection
#   ENABLE_AI_SENTIMENT=true -> KabuSys_AiAnalysis
#   ENABLE_TDNET=true      -> KabuSys_TdnetCollection
#
# Existing jobs are overwritten with -Force.
# Logs are appended to logs\<TaskName>.log (directory is created automatically).

param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Parse .env file
# ---------------------------------------------------------------------------
function Get-EnvValue {
    param([string]$EnvFile, [string]$Key)
    if (-not (Test-Path $EnvFile)) { return $null }
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if ($null -eq $line) { return $null }
    return ($line -split "=", 2)[1].Trim()
}

$EnvFile = Join-Path $WorkDir ".env"
$EnableYahooNews    = (Get-EnvValue $EnvFile "ENABLE_YAHOONEWS")    -eq "true"
$EnableAiSentiment  = (Get-EnvValue $EnvFile "ENABLE_AI_SENTIMENT") -eq "true"
$EnableTdnet        = (Get-EnvValue $EnvFile "ENABLE_TDNET")        -eq "true"

Write-Host "KabuSys Task Scheduler: registration start"
Write-Host "  WorkDir            : $WorkDir"
Write-Host "  PythonPath         : $PythonPath"
Write-Host "  ENABLE_YAHOONEWS   : $EnableYahooNews"
Write-Host "  ENABLE_AI_SENTIMENT: $EnableAiSentiment"
Write-Host "  ENABLE_TDNET       : $EnableTdnet"

# ---------------------------------------------------------------------------
# Create log directory
# ---------------------------------------------------------------------------
$LogsDir = Join-Path $WorkDir "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
    Write-Host "  Created log directory: $LogsDir"
}

# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------
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

    Write-Host "  [REGISTERED] $TaskName ($TriggerTime) -> $logFile"
}

# ---------------------------------------------------------------------------
# Core jobs (always registered)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[Core jobs]"
Register-KabuSysTask -TaskName "KabuSys_DataUpdate"            -Script "run_data_update.py"            -TriggerTime "17:30"
Register-KabuSysTask -TaskName "KabuSys_FeatureGen"            -Script "run_feature_gen.py"            -TriggerTime "18:30"
Register-KabuSysTask -TaskName "KabuSys_StrategySignal"        -Script "run_strategy_signal.py"        -TriggerTime "20:00"
Register-KabuSysTask -TaskName "KabuSys_PortfolioConstruction" -Script "run_portfolio_construction.py" -TriggerTime "21:00"
Register-KabuSysTask -TaskName "KabuSys_NightBatchReport"      -Script "run_night_batch_report.py"     -TriggerTime "21:15"
Register-KabuSysTask -TaskName "KabuSys_ExecutionStart"        -Script "start_system.py" -Arguments "--component execution"  -TriggerTime "08:30"
Register-KabuSysTask -TaskName "KabuSys_MonitoringStart"       -Script "start_system.py" -Arguments "--component monitoring" -TriggerTime "09:00"

# ---------------------------------------------------------------------------
# Addon jobs (registered only when enabled in .env)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[Addon jobs]"

if ($EnableYahooNews) {
    Register-KabuSysTask -TaskName "KabuSys_YahooNewsCollection" -Script "run_yahoonews_collection.py" -TriggerTime "17:33"
} else {
    Write-Host "  [SKIPPED] KabuSys_YahooNewsCollection (ENABLE_YAHOONEWS != true)"
}

if ($EnableAiSentiment) {
    Register-KabuSysTask -TaskName "KabuSys_AiAnalysis" -Script "run_ai_analysis.py" -TriggerTime "19:00"
} else {
    Write-Host "  [SKIPPED] KabuSys_AiAnalysis (ENABLE_AI_SENTIMENT != true)"
}

if ($EnableTdnet) {
    Register-KabuSysTask -TaskName "KabuSys_TdnetCollection" -Script "run_tdnet_collection.py" -TriggerTime "15:35"
} else {
    Write-Host "  [SKIPPED] KabuSys_TdnetCollection (ENABLE_TDNET != true)"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Registration complete."
Write-Host "Verify: Get-ScheduledTask -TaskName 'KabuSys_*' | Select-Object TaskName, State"
