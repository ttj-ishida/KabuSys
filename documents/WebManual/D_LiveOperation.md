# D. 本番運用 — WebManual

- **対象**: KabuSys を実際の資金で自動売買として運用する方
- **想定読者**: ペーパートレードで検証済みの運用者
- **目的**: 本番環境での日次運用を、毎日の定型手順として安全に実施できるようにする

> ⚠️ **本番運用を開始する前に、必ずペーパートレード（[C_PaperTrading.md](./C_PaperTrading.md)）で動作確認を行ってください。**

---

## D-1. 本番運用を始める前のチェックリスト

以下がすべて完了していることを確認してください。

- [ ] ペーパートレードで数日間、一連の運用フロー（夜間バッチ→発注→約定確認）が正常に動作している
- [ ] `.env` の `KABUSYS_ENV` を `paper_trading` から `live` に変更した
- [ ] `python -m kabusys.validate_config` が `live` 環境でエラーなく完了する
- [ ] kabuステーション® が本番用パスワード（ポート 18080）でログインできている
- [ ] `config/risk_config.yaml` のリスクパラメータを実際の運用資金に合わせて設定している
- [ ] Task Scheduler の全バッチジョブが `Ready` 状態になっている

---

## D-2. 1日の運用タイムライン

```
07:50  PC・kabuステーション起動確認（手動）
08:00  Pre-Market Checklist 確認（手動）
08:30  Execution Engine 起動（Task Scheduler 自動）
09:00  Monitoring 起動（Task Scheduler 自動）
       ─────── 前場（09:00〜11:30）───────
       自動発注・約定確認・リスク監視
       ─────── 昼休み（11:30〜12:30）─────
       注文受付停止
       ─────── 後場（12:30〜15:00）───────
       自動発注・約定確認・リスク監視
15:00  市場クローズ → Market Close 確認（手動）
15:30  市場データ更新バッチ（Task Scheduler 自動）
16:00  特徴量計算バッチ（Task Scheduler 自動）
18:00  AI 分析バッチ（Task Scheduler 自動・オプション）
20:00  売買シグナル生成バッチ（Task Scheduler 自動）
21:00  ポートフォリオ構築バッチ（Task Scheduler 自動）
21:30  夜間バッチ結果確認（手動）
```

---

## D-3. 朝の確認（08:00 — Pre-Market Checklist）

市場オープン前に、以下を **すべて** 確認してから Execution を起動します。

| 確認項目 | 内容 | 確認方法 |
|---|---|---|
| PC 状態 | スリープ解除済み・正常動作 | 目視 |
| kabuステーション | 起動・ログイン済み（本番ポート 18080） | 画面確認 |
| API 接続 | kabuステーション の接続状態 = 正常 | kabuステーション 画面 |
| 夜間データ | 前日分データが DuckDB に入っている | `data_update` ログ確認 |
| Signal Queue | 本日の `pending` シグナルが存在する | 下記コマンド |
| ポジション整合 | DB と証券口座のポジションが一致 | 下記コマンド |
| 停止フラグ | `data/stop_requested.flag` が存在しない | エクスプローラー確認 |
| Task Scheduler | 全バッチジョブが `Ready` 状態 | 下記コマンド |

**Signal Queue 確認:**
```cmd
python -m kabusys.run_signal_queue_report
```

**ポジション整合確認:**
```cmd
python -m kabusys.run_position_reconciliation_report
```
→ `CLEAN` が表示されれば問題なし。`DISCREPANCY` が出た場合は Execution 起動前に確認すること。

**Task Scheduler 状態確認:**
```powershell
Get-ScheduledTask -TaskName "KabuSys_*" | Select-Object TaskName, State
```

---

## D-4. Execution の起動と停止（08:30）

Task Scheduler が自動起動します。手動での起動・停止が必要な場合は以下を使用します。

**手動起動（Execution + Monitoring まとめて）:**
```cmd
python scripts\start_system.py
```

**Execution のみ起動:**
```cmd
python scripts\start_system.py --component execution
```

**起動前の安全確認（`--dry-run`）:**
```cmd
python scripts\start_system.py --dry-run
```
発注は行わず、Signal Queue とポジションの状態のみ確認できます。

**停止（グレースフルシャットダウン）:**
```cmd
python scripts\stop_system.py
```

---

## D-5. ザラ場中の監視（09:00〜15:00）

ザラ場中は以下の項目を定期的に目視確認します。

| 監視項目 | 確認内容 | 異常時の対応 |
|---|---|---|
| 注文エラー | `rejected` 注文が連続していないか | ログ確認 → [E. 障害対応](./E_FailureRecovery.md) |
| API 接続 | kabuステーション の接続状態 | kabuステーション 再起動 |
| ドローダウン | 日次損失が閾値に近づいていないか | Kill Switch 検討 |
| Execution プロセス | `data/execution.pid` が存在するか | `start_system.py --component execution` |

**ログのリアルタイム確認:**
```powershell
# Execution ログの直近50行
Get-Content logs\execution.log -Tail 50

# ERROR / CRITICAL のみ抽出
Select-String -Path logs\*.log -Pattern "ERROR|CRITICAL"
```

**主要なログキーワード:**

| キーワード | 意味 | 対応 |
|---|---|---|
| `停止フラグを検知` | グレースフル停止開始 | 正常停止を確認する |
| `Kill Switch` | 緊急停止発動 | [E-2. 緊急停止](./E_FailureRecovery.md#e-2) を参照 |
| `position_discrepancies` | ポジション不整合 | [E-4. ポジション不整合](./E_FailureRecovery.md#e-4) を参照 |
| `CIRCUIT_BREAKER_OPEN` | サーキットブレーカー発動 | [E-3. API 障害](./E_FailureRecovery.md#e-3) を参照 |

---

## D-6. 引け後の確認（15:00 — Market Close）

市場クローズ後に以下を確認します。

| 確認項目 | 確認内容 |
|---|---|
| 未約定注文 | `signal_queue` に `pending` が残っていないか |
| ポジション更新 | `positions` テーブルが最新状態か |
| 当日損益 | `portfolio_performance` に本日分が記録されているか |

```cmd
:: ポジション確認
duckdb data\kabusys.duckdb "SELECT * FROM positions ORDER BY code"

:: 日次レポート生成（artifacts/ に保存）
python -m kabusys.run_performance_report --type daily --save

:: Market Close レポート
python -m kabusys.run_market_close_report
```

---

## D-7. 夜間バッチの確認（21:30）

夜間バッチが正常完了したかを確認します。

```powershell
# Task Scheduler の実行結果を一覧表示
Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult
```

`LastTaskResult = 0` が正常終了です。

| ジョブ名 | 実行時刻 | 確認内容 |
|---|---|---|
| KabuSys_DataUpdate | 15:30 | DuckDB に当日の株価データが追加されている |
| KabuSys_FeatureGen | 16:00 | `features` テーブルが更新されている |
| KabuSys_AiAnalysis | 18:00 | `news_scores`, `regime_scores` が更新されている（オプション） |
| KabuSys_StrategySignal | 20:00 | `signals` テーブルに本日の BUY シグナルがある |
| KabuSys_PortfolioConstruction | 21:00 | `signal_queue` に `pending` シグナルが入っている |

**signal_queue に pending がない場合（翌日の発注候補ゼロ）:**
```cmd
python -m kabusys.run_signal_queue_report
:: → pending = 0 なら翌日は発注なし（戦略上の条件不成立）
```

---

## D-8. 成績レポートの確認（日次・週次・月次）

成績レポートはいつでも生成できます。

```cmd
:: 日次レポート
python -m kabusys.run_performance_report --type daily --save

:: 週次レポート
python -m kabusys.run_performance_report --type weekly --save

:: 月次レポート
python -m kabusys.run_performance_report --type monthly --save
```

レポートは `artifacts/performance/live/` 配下に保存されます。

---

## 関連ドキュメント

- `documents/08_Operations/TradingRunbook.md` — 日次運用の詳細手順（エンジニア向け完全版）
- [E_FailureRecovery.md](./E_FailureRecovery.md) — 異常が起きたときの対応
- [C_PaperTrading.md](./C_PaperTrading.md) — ペーパートレードへの切り替え方
