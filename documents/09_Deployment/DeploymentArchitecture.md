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
    Execution Engine
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

------------------------------------------------------------------------

# 9. 自動起動

Windows Task Scheduler により以下を自動実行する。

  時刻    内容
  ------- -----------------------------------
  15:30   market data ingestion
  16:00   feature generation
  18:00   AI analysis (news + regime)
  20:00   strategy signal generation
  21:00   portfolio construction
  08:30   execution_service 起動
  09:00   monitoring_service 起動

**初期セットアップ（初回のみ）:**

```cmd
:: 1. 環境変数設定（.env ウィザード）
python -m kabusys.config_setup

:: 2. config/*.yaml テンプレート生成
python scripts\generate_config.py

:: 3. 設定検証
python -m kabusys.validate_config

:: 4a. スケジューラーデーモン登録（推奨: DB ロック問題を自動解消）
::     ログオン時に run_scheduler.py が起動し、全ジョブを一元管理する
powershell -File scripts\setup_scheduler_daemon.ps1

:: 4b. 個別タスク登録（従来方式）
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
  scripts\run_scheduler.py            スケジューラーデーモン本体（常駐・推奨）
  scripts\setup_scheduler_daemon.ps1  デーモンを Task Scheduler に登録（ログオン時起動）
  scripts\setup_task_scheduler.ps1    個別タスクを Task Scheduler に登録（従来方式）
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
