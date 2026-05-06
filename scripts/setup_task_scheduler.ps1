# scripts/setup_task_scheduler.ps1
# KabuSys Windows Task Scheduler 登録スクリプト
#
# 使い方:
#   powershell -File scripts\setup_task_scheduler.ps1
#   powershell -File scripts\setup_task_scheduler.ps1 -PythonPath C:\path\to\python.exe
#
# 既存のジョブは -Force で上書き登録される。
# ログは logs\<TaskName>.log に追記される（ログディレクトリは自動作成）。

param(
    [string]$PythonPath = "python",
    [string]$WorkDir = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

Write-Host "KabuSys Task Scheduler 登録開始"
Write-Host "  WorkDir   : $WorkDir"
Write-Host "  PythonPath: $PythonPath"

# ログディレクトリを作成
$LogsDir = Join-Path $WorkDir "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
    Write-Host "  ログディレクトリ作成: $LogsDir"
}

function Register-KabuSysTask {
    param(
        [string]$TaskName,
        [string]$Script,
        [string]$Arguments = "",
        [string]$TriggerTime
    )

    # 標準出力・標準エラーをログファイルにリダイレクト
    # cmd.exe 経由で >> リダイレクトを実現する（Task Scheduler は直接リダイレクト非対応）
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

    Write-Host "  登録完了: $TaskName ($TriggerTime) → $logFile"
}

# Night batch jobs
Register-KabuSysTask -TaskName "KabuSys_DataUpdate"            -Script "run_data_update.py"            -TriggerTime "15:30"
# オプション: ENABLE_YAHOONEWS=true のときのみ実際に収集が実行される（false の場合即スキップ）
Register-KabuSysTask -TaskName "KabuSys_YahooNewsCollection"   -Script "run_yahoonews_collection.py"   -TriggerTime "15:33"
Register-KabuSysTask -TaskName "KabuSys_FeatureGen"            -Script "run_feature_gen.py"            -TriggerTime "16:00"
Register-KabuSysTask -TaskName "KabuSys_AiAnalysis"            -Script "run_ai_analysis.py"            -TriggerTime "18:00"
Register-KabuSysTask -TaskName "KabuSys_StrategySignal"        -Script "run_strategy_signal.py"        -TriggerTime "20:00"
Register-KabuSysTask -TaskName "KabuSys_PortfolioConstruction" -Script "run_portfolio_construction.py" -TriggerTime "21:00"

# System start jobs
Register-KabuSysTask -TaskName "KabuSys_ExecutionStart"  -Script "start_system.py" -Arguments "--component execution"  -TriggerTime "08:30"
Register-KabuSysTask -TaskName "KabuSys_MonitoringStart" -Script "start_system.py" -Arguments "--component monitoring" -TriggerTime "09:00"

Write-Host ""
Write-Host "8 件のジョブ登録が完了しました。"
Write-Host "確認: Get-ScheduledTask -TaskName 'KabuSys_*' | Select-Object TaskName, State"
