# DeploymentArchitecture.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの
**デプロイメントアーキテクチャ（Deployment Architecture）** を定義する。

本システムは **1台の Windows PC 上で稼働する構成** を前提とする。

この設計では以下を明確にする。

-   システムの物理配置
-   論理レイヤー構成
-   各コンポーネントの役割
-   デプロイ手順
-   障害時の復旧方法

個人運用の自動売買システムでは、**単一ノード構成 + 論理レイヤー分離**
が最もシンプルで安定した構成となる。

------------------------------------------------------------------------

# 2. システム構成（Single Node Architecture）

本システムは以下の構成で稼働する。

    Windows PC
    │
    ├ Data Platform
    │
    ├ Research Environment
    │
    ├ Backtest Framework
    │
    ├ Strategy Engine
    │
    ├ AI Analysis
    │
    ├ Portfolio Construction
    │
    ├ Execution Engine
    │
    └ Monitoring System

すべてのコンポーネントは **同一PC内のプロセスとして動作する。**

------------------------------------------------------------------------

# 3. レイヤー構成

システムは以下の論理レイヤーで構成される。

    Data Layer
    ↓
    Research Layer
    ↓
    Strategy Layer
    ↓
    Execution Layer
    ↓
    Monitoring Layer

各レイヤーは役割ごとに分離される。

  Layer        役割
  ------------ -----------------------------
  Data         市場データ / ニュースデータ
  Research     戦略研究
  Strategy     売買シグナル生成
  Execution    発注処理
  Monitoring   システム監視

------------------------------------------------------------------------

# 4. Windows PC 構成

OS

    Windows

理由

-   kabuステーションAPIがWindows専用
-   ローカルAPIの安定性
-   運用管理の容易さ

推奨スペック

  項目      推奨
  --------- -----------
  CPU       6〜8 Core
  Memory    32GB
  Storage   SSD 1TB
  Network   常時接続

------------------------------------------------------------------------

# 5. コンポーネント構成

## 5.1 Data Platform

役割

-   市場データ保存
-   ニュースデータ保存
-   AIスコア保存
-   売買履歴保存

構成

    DuckDB
    Parquet

------------------------------------------------------------------------

## 5.2 Research Environment

役割

-   データ分析
-   ファクター研究
-   AIモデル開発

主なツール

    Python
    pandas
    numpy
    Jupyter

------------------------------------------------------------------------

## 5.3 Backtest Framework

役割

-   戦略検証
-   パフォーマンス評価

入力

-   Data Platform

出力

-   Backtest Result

------------------------------------------------------------------------

## 5.4 Strategy Engine

役割

-   特徴量計算
-   スコア生成
-   売買シグナル生成

------------------------------------------------------------------------

## 5.5 AI Analysis

役割

-   ニュース解析
-   センチメント分析
-   市場レジーム判定

------------------------------------------------------------------------

## 5.6 Portfolio Construction

役割

-   銘柄選定
-   資金配分
-   ポートフォリオ生成

------------------------------------------------------------------------

## 5.7 Execution Engine

役割

-   発注処理
-   約定管理
-   ポジション管理

通信

    Execution Engine
    ↓
    kabuステーション API
    ↓
    証券会社

> **現在は停止中。** 運用は手動注文メイン（`.env` の `ENABLE_AUTO_EXECUTION=false`）で、
> Execution Engine は起動しない。自動執行を再開した場合も、自動で発注するのは
> `signal_queue` の BUY だけ（自動売却の機能はない）。

------------------------------------------------------------------------

## 5.8 Monitoring System

役割

-   システム監視
-   データ監視
-   リスク監視
-   発注監視

------------------------------------------------------------------------

# 6. データフロー

システムのデータフローは以下の通り。

    Market Data / News
    ↓
    Data Platform
    ↓
    Feature Generation
    ↓
    Strategy Engine
    ↓
    Portfolio Construction
    ↓
    【手動注文メイン（現在の運用）】
    夜 LINE / 朝の手動注文レポート
    ↓
    ユーザーが証券画面で発注
    ↓
    約定を manual_trades に入力
    ↓
    保有評価・売却候補（manual_action_queue）

    【自動執行（現在停止中）】
    Execution Engine（signal_queue の BUY のみ）
    ↓
    kabuステーション API
    ↓
    Broker

------------------------------------------------------------------------

# 7. デプロイフロー

新戦略の導入は以下の手順で行う。

    Research
    ↓
    Backtest
    ↓
    Forward Test
    ↓
    Production Deploy

------------------------------------------------------------------------

# 8. デプロイ方法

コード管理

    Git

運用フロー

    develop branch
    ↓
    test
    ↓
    main branch
    ↓
    production deploy

## 8.1 運用フォルダと開発フォルダ

開発と運用は **同じ PC の別フォルダ** に分ける。

  フォルダ                              用途
  ------------------------------------- ------------------------------------------------------------
  `C:\Projects\KabuSys`                 運用フォルダ（git clone、origin = github.com/ttj-ishida/KabuSys）
  `C:\Users\tetsu\Projects\KabuSys`     開発フォルダ（例。ブランチ作業・テストはこちら）

-   DB（`data/kabusys.duckdb`・`data/monitoring.db`）・ログ（`logs/`）・`artifacts/`・`.env` は**運用フォルダ側**にある
-   スケジューラーと手動注文の作業（約定入力・レポート確認）はすべて運用フォルダで行う
-   production deploy = 運用フォルダで `main` を pull すること

## 8.2 Python 環境

-   Python 3.13.5
-   運用用の仮想環境: `C:\Projects\KabuSys\.venv`
-   `requirements.txt` / `constraints.txt` は Python 3.13 と非互換（**Issue #422**）。
    `pip install -c constraints.txt -r requirements.txt` は失敗するため、運用 `.venv` には
    動作確認済みのバージョン（numpy 2.4.4、pandas 2.3.3、pyarrow 23.0.1、duckdb 1.5.0、
    streamlit 1.55.0、openai 1.109.1、pytest 9.0.2、ruff 0.15.11 など）を暫定的に入れている
-   現状、`KabuSys_Scheduler` タスクの実行ファイルは `python`（グローバルの `C:\Python313`）。
    `.venv` への切り替えは予定（管理者 PowerShell で `Set-ScheduledTask` によりアクションを変更）

------------------------------------------------------------------------

# 9. 自動起動

運用では **スケジューラーデーモン方式** を使う。Windows タスク `KabuSys_Scheduler`
（ログオン時トリガー）が `scripts\run_scheduler.py` を常駐起動し、すべてのジョブを
一元管理する（登録: `scripts\setup_scheduler_daemon.ps1`）。

-   非営業日（土日・祝日・年末年始）は全ジョブをスキップする
-   起動時刻を過ぎたジョブは、起動直後に順次実行する（追いつき）
-   設定は起動時と日付変更時に `.env` から再読込する
-   個別タスク方式（`scripts\setup_task_scheduler.ps1`）は従来方式で、現在は使っていない

  時刻    ジョブ                           手動運用中
  ------- -------------------------------- ----------------------------------------------------------
  08:00   pre_market_report                実行（自動執行の可否判定。BLOCKED でも問題なし）
  08:02   signal_queue_report              実行
  08:05   manual_order_report（朝）        実行（朝 LINE）
  08:30   execution_start                  **無効**（`ENABLE_AUTO_EXECUTION=false`）
  08:35   position_reconciliation_report   **無効**
  09:00   monitoring_start                 **無効**
  15:35   tdnet_collection                 実行（`ENABLE_TDNET=true`）
  17:30   data_update                      実行
  17:33   yahoonews_collection             実行（`ENABLE_YAHOONEWS=true`）
  18:30   feature_gen                      実行
  19:00   ai_analysis                      実行（`ENABLE_AI_SENTIMENT=true`。スコア未出力: Issue #419）
  20:00   strategy_signal                  実行
  21:00   portfolio_construction           実行（夜 LINE）
  21:10   manual_order_report（夜）        実行
  21:15   night_batch_report               実行

**初期セットアップ（初回のみ）:**

```cmd
:: 1. 環境変数設定（.env ウィザード）
python -m kabusys.config_setup

:: 2. config/*.yaml テンプレート生成
python scripts\generate_config.py

:: 3. 設定検証
python -m kabusys.validate_config

:: 4a. スケジューラーデーモン登録（運用で使用中）
::     ログオン時に run_scheduler.py が起動し、全ジョブを一元管理する
::     .venv の python を使う場合は -PythonPath で指定する
powershell -File scripts\setup_scheduler_daemon.ps1 -PythonPath C:\Projects\KabuSys\.venv\Scripts\python.exe

:: 4b. 個別タスク登録（従来方式・未使用。ENABLE_AUTO_EXECUTION を参照しない）
:: powershell -File scripts\setup_task_scheduler.ps1
```

**手動起動・停止:**

  操作                   コマンド
  ---------------------- -----------------------------------------------
  全体起動               python scripts\start_system.py
  全体停止               python scripts\stop_system.py
  実行系のみ起動         python scripts\start_system.py --component execution
  監視系のみ起動         python scripts\start_system.py --component monitoring
  状態確認（発注なし）   python scripts\start_system.py --dry-run
  停止フラグ解除＋起動   python scripts\start_system.py --clear-stop-flag

**保守スクリプト:**

  スクリプト                          用途
  ----------------------------------- -------------------------------------------------
  scripts\run_scheduler.py            スケジューラーデーモン本体（常駐・運用で使用中）
  scripts\setup_scheduler_daemon.ps1  デーモンを Task Scheduler に登録（ログオン時起動）
  scripts\setup_task_scheduler.ps1    個別タスクを Task Scheduler に登録（従来方式・未使用）
  scripts\remove_task_scheduler.ps1   KabuSys_* タスクを一括削除
  scripts\rebuild_features.py         特徴量を手動再計算（データ確認付き）
  scripts\reset_signals.py            signal_queue をクリア（取引時間外のみ）
  scripts\mark_signal_failed.py       指定シグナルを status='failed' に手動更新
  scripts\generate_config.py          config/*.yaml テンプレートを生成
  python -m kabusys.config_setup      .env を対話式で作成・更新
  python -m kabusys.validate_config   設定の事前検証（必須変数・YAML・live 警告）

詳細: `documents/10_Runtime/RuntimeJobSchedule.md`

------------------------------------------------------------------------

# 10. 障害対応

障害対応フロー

    異常検知
    ↓
    Monitoring Alert
    ↓
    原因分析
    ↓
    復旧

重大障害

    Kill Switch

------------------------------------------------------------------------

# 11. ロールバック

問題発生時

    previous version

へ戻す。

手順

1.  Deploy停止
2.  Gitで旧バージョン取得
3.  システム再起動

------------------------------------------------------------------------

# 12. セキュリティ

以下を実施する。

-   APIキー保護
-   Windowsログイン保護
-   アクセスログ保存

------------------------------------------------------------------------

# 13. 将来拡張

将来的には以下を検討する。

-   Research Server (Linux) 追加
-   分散バックテスト
-   GPU AI分析
-   クラウドバックアップ

------------------------------------------------------------------------

# 14. まとめ

本システムは **Single Windows Node Architecture** を採用する。

    Windows PC
    │
    ├ Data Platform
    ├ Research
    ├ Strategy
    ├ AI
    ├ Portfolio
    ├ Execution
    └ Monitoring

この構成により、**シンプルで安定した個人運用の自動売買システム**を実現する。
