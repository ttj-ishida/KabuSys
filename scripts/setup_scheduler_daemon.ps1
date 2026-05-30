# scripts/setup_scheduler_daemon.ps1
# KabuSys スケジューラーデーモンを Task Scheduler に登録する
#
# 既存の個別ジョブ (KabuSys_DataUpdate 等) を置き換える場合は
# 先に既存タスクを削除してください（下記コマンド参照）。
#
# Usage:
#   powershell -File scripts\setup_scheduler_daemon.ps1
#   powershell -File scripts\setup_scheduler_daemon.ps1 -PythonPath C:\path\to\python.exe

param(
    [string]$PythonPath = "python",
    [string]$WorkDir    = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

$TaskName = "KabuSys_Scheduler"

$LogsDir = Join-Path $WorkDir "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

# ログは Python 側の FileHandler (logs/scheduler.log) のみで出力する。
# cmd.exe リダイレクトを使わないことで二重書き込みを防ぐ。
$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "scripts\run_scheduler.py" `
    -WorkingDirectory $WorkDir

# ログオン時に起動（クラッシュ時は 5 分後に最大 3 回リトライ）
$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -Force | Out-Null

Write-Host "登録完了: $TaskName"
Write-Host "  ログ   : $(Join-Path $WorkDir 'logs\scheduler.log') (Python FileHandler)"
Write-Host ""
Write-Host "--- 既存の個別タスクを削除する場合 ---"
Write-Host "  Get-ScheduledTask -TaskName 'KabuSys_*' | Where-Object TaskName -ne 'KabuSys_Scheduler' | Unregister-ScheduledTask -Confirm:`$false"
Write-Host ""
Write-Host "--- 確認 ---"
Write-Host "  python scripts\run_scheduler.py --list"
Write-Host "  python scripts\run_scheduler.py --once"
Write-Host ""
Write-Host "--- 今すぐ手動起動 ---"
Write-Host "  Start-ScheduledTask -TaskName 'KabuSys_Scheduler'"
