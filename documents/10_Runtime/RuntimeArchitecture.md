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

> **現在の運用方式（2026-10 時点）:** 手動注文メイン。夜間バッチと朝・夜のレポートは
> 自動で動くが、発注はユーザーが証券画面で行い、約定を `manual_trades` に入力する。
> 自動執行（execution_service / monitoring_service の起動）は `.env` の
> `ENABLE_AUTO_EXECUTION=false` で停止中。**自動売却の機能はない**（`signal_queue` には
> BUY しか入らず、自動執行を再開しても自動で発注されるのは BUY だけ）。

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

    15:35 〜 21:15（tdnet_collection 〜 night_batch_report）

夜間バッチの後に、手動注文向けのレポートと LINE を出す。

    portfolio_construction（21:00、夜 LINE）
          ↓
    manual_order_report --phase evening（21:10）
          ↓
    night_batch_report（21:15）
          ↓
    manual_order_report --phase morning（翌 08:05、朝 LINE）

日付の決まり: D 日夜のバッチは `signals` / `signal_queue` を `date = D` で書き、
翌朝のレポート・執行は前営業日（`prev_trading_day`）の分を読む。

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

> 実装では DuckDB の `signal_queue` テーブルで、運用ジョブのうち書き込むのは
> `scripts/run_portfolio_construction.py` のみ（BUY だけを INSERT。検証用ツール
> `kabusys.tools.inject_dummy_signal` を除く）。SELL シグナルは `signals` テーブル・LINE・売却候補
> （`manual_action_queue`）に出るだけで、`signal_queue` には入らない。

------------------------------------------------------------------------

# 5. ザラ場処理（Market Hours）

> 以下は自動執行モードの構成。**現在は停止中**で、手動運用ではザラ場中に KabuSys の
> プロセスは動かない（ユーザーが証券画面で発注し、約定を入力する）。

自動執行モードでは、ザラ場で **Execution と Monitoring のみ稼働**する。**intraday のシグナル生成は行わない。**

    Signal Queue（夜間バッチで生成済み）
         ↓
    execution_service
         ↓
    kabuステーションAPI
         ↓
    証券会社

**intraday シグナル生成を持たない理由:**
本戦略は日足スイング設計であり、シグナル判断に使う特徴量（モメンタム・ボラティリティ・AIスコア・レジーム）はすべて日足終値ベースで計算される。ザラ場中の価格変動でシグナルを再計算する設計ではなく、発注は寄付き1回限りである。ザラ場はあくまで前夜生成済みシグナルの執行・約定管理・監視のみを担う。

Execution の役割

-   寄付き発注（シグナルキューから読み取り）
-   約定確認（WebSocket push 受信）
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

monitoring_service は自動執行モードで稼働する（09:00 起動）。手動運用中
（`ENABLE_AUTO_EXECUTION=false`）は Execution プロセスの死活を前提に CRITICAL 通知が
続くため起動しない。Kill Switch は未約定注文の取消のみで、保有の売却はしない。

監視対象

-   execution_service 生存
-   CPU / メモリ
-   データ更新
-   注文エラー

異常時

    LINE通知
    Kill Switch

------------------------------------------------------------------------

# 8. スケジューラ

ジョブ自動実行の方式は 2 通りある。**運用では方式 A（スケジューラーデーモン）を使っている。**

## 方式 A: スケジューラーデーモン（運用で使用中）

単一の Python プロセスが常駐してすべてのジョブを一元管理する。
Windows タスク `KabuSys_Scheduler`（ログオン時トリガー）が
運用フォルダ `C:\Projects\KabuSys` で `scripts\run_scheduler.py` を起動する。

- `run_execution` が DuckDB 接続を保持したまま市場終了後も生存し続けることで
  夜間バッチが DB ロックで失敗する問題を自動解消する（DuckDB に書くジョブの前に execution を停止）
- 取引カレンダーを参照し、非営業日（土日・祝日・年末年始）は全ジョブをスキップする
- 起動時刻を過ぎたジョブは、起動直後に順次実行する（追いつき）。実行済みは
  `data/scheduler_ran_today.json` に記録し、再起動しても当日分は重複実行しない
- 設定（`ENABLE_AUTO_EXECUTION` / `ENABLE_TDNET` / `ENABLE_YAHOONEWS` / `ENABLE_AI_SENTIMENT` など）は
  起動時と日付変更時に `.env` から再読込する
- 現状、タスクの実行ファイルは `python`（グローバル `C:\Python313`）。`.venv` への切り替えを予定

  スクリプト                                用途
  ----------------------------------------- ------------------------------------------------
  scripts\run_scheduler.py                  スケジューラーデーモン本体（常駐）
  scripts\setup_scheduler_daemon.ps1        Task Scheduler に「ログオン時起動」で 1 エントリ登録

## 方式 B: 個別タスク登録（従来方式・未使用）

従来方式で、現在は使っていない。`ENABLE_AUTO_EXECUTION` を参照しないため、
手動運用中に使うと 08:30 の Execution 起動なども登録される。

  スクリプト                              用途
  --------------------------------------- -----------------------------------------------
  scripts\setup_task_scheduler.ps1        登録（Core 常時 / Addon は .env フラグ依存）
  scripts\remove_task_scheduler.ps1       KabuSys_* タスクを一括削除

詳細: `documents/10_Runtime/RuntimeJobSchedule.md`（セクション7）

------------------------------------------------------------------------

# 9. プロセス優先度

執行プロセスを最優先とする。

  プロセス             優先度     起動スクリプト
  -------------------- -------- -------------------------------------------
  execution_service    High     scripts\start_system.py --component execution
  monitoring_service   High     scripts\start_system.py --component monitoring
  strategy_service     Normal   ライブラリ呼び出し（夜間バッチから呼び出し）
  ai_service           Low      ライブラリ呼び出し（夜間バッチから呼び出し）

**実装:** `src/kabusys/utils/process_priority.py`

- `set_process_priority(level)` — Windows: `psutil.HIGH/NORMAL/IDLE_PRIORITY_CLASS`、Linux/Darwin/FreeBSD: `psutil.Process().nice(-10/0/10)`、未対応OS は WARNING でスキップ
- `set_cpu_affinity(cpu_count)` — 最初の N コアに固定（`None` で全コア使用）
- 権限不足（`psutil.AccessDenied`）および未対応プラットフォーム（`AttributeError`/`NotImplementedError`）は WARNING ログで続行（プロセスを落とさない）
- 詳細仕様: `docs/superpowers/specs/2026-04-09-execution-priority-control.md`（Issue #43）

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
    手動注文レポート / LINE → ユーザーが発注 → 約定入力（現在の運用）
    Execution → Monitoring（自動執行モード・現在停止中）

この設計により **Single Windows Node でも安全で安定した自動売買運用**
を実現する。
