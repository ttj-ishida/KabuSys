# RuntimeArchitecture.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの
**ランタイムアーキテクチャ（Runtime Architecture）** を定義する。

Runtime Architecture は以下を定義する。

-   システムプロセス構成
-   ジョブスケジュール
-   日次パイプライン
-   ザラ場処理
-   システム間のデータ受け渡し

本システムは **Single Windows Node (1台PC)** 上で稼働するため、
サーバー分離ではなく **プロセス分離 + スケジューリング設計**
により安全性を確保する。

------------------------------------------------------------------------

# 2. プロセス構成

Windows PC 上では以下のプロセスが独立して稼働する。

    Windows PC
    │
    ├ data_service
    ├ feature_service
    ├ ai_service
    ├ strategy_service
    ├ portfolio_service
    ├ execution_service
    └ monitoring_service

  プロセス             役割
  -------------------- -----------------------------
  data_service         J-Quants / News データ取得
  feature_service      特徴量生成
  ai_service           ニュース解析 / レジーム判定
  strategy_service     売買シグナル生成
  portfolio_service    銘柄選定・株数計算
  execution_service    発注処理
  monitoring_service   システム監視

------------------------------------------------------------------------

# 3. 日次パイプライン（Night Batch）

重い処理は **夜間バッチ** で実行する。

    J-Quants / News
          ↓
    data_update_job
          ↓
    feature_job
          ↓
    ai_analysis_job
          ↓
    strategy_signal_job
          ↓
    portfolio_construction_job
          ↓
    signal_queue

夜間処理時間

    15:30 〜 08:30

------------------------------------------------------------------------

# 4. シグナルキュー

Strategy層とExecution層の間には **Signal Queue** を設置する。

    Strategy Engine
          ↓
    Signal Queue
          ↓
    Execution Engine

保存形式

    signals.parquet
    または
    signals_table

Signal内容

  項目         内容
  ------------ --------------
  date         取引日
  code         銘柄コード
  side         buy/sell
  size         株数
  order_type   limit/market
  price        指値

------------------------------------------------------------------------

# 5. ザラ場処理（Market Hours）

ザラ場では **Execution と Monitoring のみ稼働**する。

    Signal Queue
         ↓
    execution_service
         ↓
    kabuステーションAPI
         ↓
    証券会社

Execution の役割

-   発注
-   約定確認
-   ポジション更新

------------------------------------------------------------------------

# 6. リスク制御

Execution層では以下を確認する。

-   二重発注防止
-   口座余力チェック
-   ポジション上限
-   サーキットブレーカー

例

    Max Position Size
    Max Drawdown

------------------------------------------------------------------------

# 7. Monitoringプロセス

monitoring_service は常時稼働する。

監視対象

-   execution_service 生存
-   CPU / メモリ
-   データ更新
-   注文エラー

異常時

    Slack通知
    Kill Switch

------------------------------------------------------------------------

# 8. スケジューラ

ジョブ管理には Windows Task Scheduler を使用する。

  時刻           ジョブ
  -------------- ---------------------
  15:30          data_update_job
  16:00          feature_job
  18:00          ai_analysis_job
  20:00          strategy_signal_job
  21:00          portfolio_job
  08:30          execution_start
  09:00〜15:30   execution_monitor

------------------------------------------------------------------------

# 9. プロセス優先度

執行プロセスを最優先とする。

  プロセス             優先度
  -------------------- --------
  execution_service    High
  monitoring_service   High
  strategy_service     Normal
  ai_service           Low

------------------------------------------------------------------------

# 10. 障害対応

異常時のフロー

    Monitoring
        ↓
    Alert
        ↓
    Kill Switch
        ↓
    Execution停止

------------------------------------------------------------------------

# 11. 将来拡張

将来的には以下を検討する。

-   Linux Research Server
-   GPU AI処理
-   分散バックテスト
-   クラウドバックアップ

------------------------------------------------------------------------

# 12. まとめ

Runtime Architecture は以下で構成される。

    Night Batch
       ↓
    Signal Queue
       ↓
    Execution
       ↓
    Monitoring

この設計により **Single Windows Node でも安全で安定した自動売買運用**
を実現する。
