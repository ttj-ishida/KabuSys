# scripts/setup_task_scheduler.ps1
# KabuSys Windows Task Scheduler 登録スクリプト
#
# 使い方:
#   powershell -File scripts\setup_task_scheduler.ps1
#   powershell -File scripts\setup_task_scheduler.ps1 -PythonPath C:\path\to\python.exe
#
# 既存のジョブは -Force で上書き登録される。

param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

Write-Host "KabuSys Task Scheduler 登録開始"
Write-Host "  WorkDir   : $WorkDir"
Write-Host "  PythonPath: $PythonPath"

function Register-KabuSysTask {
    param(
        [string]$TaskName,
        [string]$Script,
        [string]$Arguments = "",
        [string]$TriggerTime
    )

    $action = if ($Arguments) {
        New-ScheduledTaskAction -Execute $PythonPath `
            -Argument "scripts\$Script $Arguments" `
            -WorkingDirectory $WorkDir
    } else {
        New-ScheduledTaskAction -Execute $PythonPath `
            -Argument "scripts\$Script" `
            -WorkingDirectory $WorkDir
    }

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

    Write-Host "  登録完了: $TaskName ($TriggerTime)"
}

# Night batch jobs
Register-KabuSysTask -TaskName "KabuSys_DataUpdate"            -Script "run_data_update.py"            -TriggerTime "15:30"
Register-KabuSysTask -TaskName "KabuSys_FeatureGen"            -Script "run_feature_gen.py"            -TriggerTime "16:00"
Register-KabuSysTask -TaskName "KabuSys_AiAnalysis"            -Script "run_ai_analysis.py"            -TriggerTime "18:00"
Register-KabuSysTask -TaskName "KabuSys_StrategySignal"        -Script "run_strategy_signal.py"        -TriggerTime "20:00"
Register-KabuSysTask -TaskName "KabuSys_PortfolioConstruction" -Script "run_portfolio_construction.py" -TriggerTime "21:00"

# System start jobs
Register-KabuSysTask -TaskName "KabuSys_ExecutionStart"  -Script "start_system.py" -Arguments "--component execution"  -TriggerTime "08:30"
Register-KabuSysTask -TaskName "KabuSys_MonitoringStart" -Script "start_system.py" -Arguments "--component monitoring" -TriggerTime "09:00"

Write-Host ""
Write-Host "7 件のジョブ登録が完了しました。"
Write-Host "確認: Get-ScheduledTask -TaskName 'KabuSys_*' | Select-Object TaskName, State"
