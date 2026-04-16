# TradingRunbook.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの **日次運用手順（Trading
Runbook）** を定義する。

目的:

-   日々の運用作業の標準化
-   障害時の対応手順の明確化
-   手動確認ポイントの整理
-   安定した自動売買運用

対象環境:

-   Single Windows PC
-   Python 自動売買システム
-   kabuステーションAPI
-   J‑Quants データ

------------------------------------------------------------------------

# 2. 日次運用フロー

    08:00  システム確認
    08:30  Execution 起動
    09:00  Market Open
    09:00‑15:30  取引監視
    15:30  Market Close
    16:00  Night Batch 確認
    21:00  Portfolio生成確認

------------------------------------------------------------------------

# 3. 朝のチェック（Pre‑Market Checklist）

時間

    08:00

確認項目

  項目           確認内容
  -------------- ----------------------
  PC状態         Windows稼働
  API接続        kabuステーション接続
  データ更新     前日データ更新
  Signal Queue   本日のシグナル存在
  ポジション     証券口座と一致

------------------------------------------------------------------------

# 4. Execution 起動

時間

    08:30 （Task Scheduler が自動実行）

Task Schedulerが実行するコマンド:

    python scripts\start_system.py --component execution

手動起動が必要な場合:

    python scripts\start_system.py

手順（自動実行の内容）:

    1. 停止フラグ（data/stop_requested.flag）をクリア
    2. execution_service 起動（data/execution.pid に PID 書き込み）
    3. 自動リコンシリエーション実行（起動時に自動）
       - OrderSent 注文をブローカーと突合・同期
       - ポジション差分をログに記録（差分があれば手動確認）
    4. API接続確認
    5. Signal Queue 読み込み
    6. monitoring_service 起動（09:00 に別タスクで自動実行）

> リコンシリエーション結果はログに出力される。
> `orders_no_status > 0` または `position_discrepancies > 0` の場合は手動確認を行うこと。

手動停止（緊急時）:

    python scripts\stop_system.py

------------------------------------------------------------------------

# 5. 市場中（Trading Hours）

時間

    09:00〜15:30

システム処理

-   シグナル取得
-   発注
-   約定確認
-   ポジション更新

監視項目

  項目            内容
  --------------- --------------
  注文エラー      rejected注文
  API接続         接続状態
  ドローダウン    DD監視
  Execution稼働   プロセス生存

------------------------------------------------------------------------

# 6. アラート対応

アラート例

    Execution Error
    API Disconnect
    Max Drawdown
    Signal Queue Error

対応

    1. ログ確認
    2. 状態確認
    3. 必要ならKill Switch

------------------------------------------------------------------------

# 7. Market Close 処理

時間

    15:30

処理

-   ポジション更新
-   日次損益計算
-   ログ保存

更新テーブル

    positions
    portfolio_performance

------------------------------------------------------------------------

# 8. 夜間処理確認

時間

    16:00〜21:00

確認項目

  Job                      内容
  ------------------------ --------------------
  data_update              市場データ更新
  feature_generation       特徴量生成
  ai_analysis              AIスコア
  strategy_signal          売買シグナル
  portfolio_construction   ポートフォリオ生成

------------------------------------------------------------------------

# 9. 障害時対応

障害例

  障害                対応                                            コマンド
  ------------------- ----------------------------------------------- ---------------------------------------------------
  API接続失敗         再接続                                          —
  注文失敗            リトライ                                        —
  PC停止              再起動後 Task Scheduler が自動起動              —
  SignalQueue破損     signal_queue をクリアして再生成                 python scripts\reset_signals.py
  特徴量データ破損    prices_daily 確認後に特徴量を再計算             python scripts\rebuild_features.py
  プロセス停止        停止フラグ経由でグレースフル停止                python scripts\stop_system.py
  手動再起動          停止後に起動                                    python scripts\stop_system.py && python scripts\start_system.py

参照

    FailureRecovery.md

------------------------------------------------------------------------

# 10. 緊急停止（Kill Switch）

条件

-   最大ドローダウン超過
-   API接続断
-   Execution異常

手順

    1. Execution停止
    2. 新規注文停止
    3. アラート送信
    4. 手動確認

------------------------------------------------------------------------

# 11. 日次レポート

Market Close 後に確認

内容

-   日次リターン
-   ポジション
-   取引履歴
-   ドローダウン

------------------------------------------------------------------------

# 12. まとめ

Trading Runbook の役割

-   日次運用の標準化
-   手動チェックポイント整理
-   障害時対応手順

このRunbookにより **安定した自動売買運用を実現する。**
