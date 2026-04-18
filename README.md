# KabuSys

日本株向け自動売買・リサーチ基盤ライブラリ & 起動スクリプト群

このリポジトリは、アルゴリズム売買の実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、ニュースNLP 等を含む一連のコンポーネント群を提供します。モジュールはできるだけ純粋関数・副作用最小化で設計されており、SQLite / DuckDB を用いたローカル永続化や OpenAI API との連携をサポートします。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド・例）
- 主要設定・環境変数
- ディレクトリ構成（概略）
- 主要モジュールの説明
- 注意事項

---

## プロジェクト概要

KabuSys は、日本株の自動売買フレームワークです。主な役割は次の通りです。

- ExecutionEngine: 発注ロジック・注文管理・リスク管理を行う実行エンジン
- Monitoring: システム状態・注文状態・リスク監視と Kill Switch（停止フラグ）の評価
- Portfolio construction: 候補選定、重み計算、ポジションサイズ算出
- Research: DuckDB を使ったファクター計算・特徴量評価
- AI 補助: ニュース記事を LLM (OpenAI) で評価し、銘柄ごとのスコアを生成
- ツール: ペーパートレード検証レポート生成など

設計上のポイント:
- 環境ごとに DB を分離（paper_trading 用 DB 等）
- .env による設定管理（対話式ウィザード・検証 CLI あり）
- ログはコンソールと日次ローテートファイルへ出力
- フェイルセーフ設計（API 失敗やデータ不足時は安全側にフォールバック）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV に応じて paper_trading モードをサポート）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 環境管理
  - config_setup.py — 対話式 .env ウィザード（.env の初期作成/更新）
  - validate_config.py — .env と config/*.yaml の事前検証 CLI
- 監視
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_db
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスク調整（セクター上限）、ポジションサイズ計算
- Research / Analytics
  - ファクター計算（momentum, volatility, value）
  - forward returns / IC 計算 / 統計サマリー
- AI
  - news_nlp.score_news — raw_news を OpenAI に投げて ai_scores に書き込み
  - regime_detector.score_regime — ETF MA とマクロニュースの LLM でレジーム判定
- ツール
  - tools.paper_verification_report — Paper Trading の集計・検証レポート生成

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - (例) git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - 追加（任意）
     - PyYAML（config/*.yaml のパース検証を行う場合）: pip install pyyaml

   ※ requirements.txt が無い場合は上記モジュールを手動で用意してください。

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に .env を作成してください（このプロジェクトでは .env.example は同梱されていないので wizard を使うのが簡単です）。

5. 設定検証（必須変数が揃っているかチェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 以下に SQLite / PID / フラグファイル等を作成します。実行時に自動作成されることが多いですが、権限や配置方針に応じて事前に作成してください。

---

## 使い方（主要コマンド・例）

- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デーモンやサービスで運用想定）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 起動前に data/kill.flag が存在する場合は起動をスキップします。
    - PID ファイル: data/execution.pid（設定により変更可）

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト: 60）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視は Settings.sqlite_path（本番用 monitoring DB）を常に使用します（環境に依存しない）。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI / レジーム判定等（ライブラリ呼び出し）
  - 例: from kabusys.ai import score_news; score_news(conn, target_date, api_key="...")

---

## 主要設定・環境変数

（主要なものを抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
    - paper_trading: mock ブローカーを利用し data/paper_trading.db を使用
    - live: 実際に発注が行われるため慎重に設定してください

- データベース
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

- ロギング
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
  - ログ出力はコンソール（stdout）と日次ローテートファイル（logs/<app>.log）に出力

- OpenAI / AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用）
  - PAPER_FILL_MODE — ペーパートレードの塗り方（instant|partial|never|reject） デフォルト: instant

- 停止制御 / フラグ
  - PID_FILE_PATH（Settings.pid_file_path） — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Settings.kill_flag_path） — Kill Switch 用フラグ（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成（抜粋）

ルート（プロジェクト）からの主要なファイル/フォルダ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 操作用ラッパー（テーブル初期化含む）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py              — prices / last date 等の取得ユーティリティ（DuckDB 絡み）
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

- data/                       — デフォルトの DB / PID / flag 等が置かれる（実行時に作成される）
- logs/                       — ログファイル（setup_logging により作成）

---

## 主要モジュールの簡易説明

- config.py / Settings
  - .env/.env.local の自動ロード機能を持ち、各種設定値（パス・閾値・フラグなど）をプロパティで提供します。

- run_execution.py
  - 起動フロー:
    1. ログ設定・プロセス優先度設定
    2. SQLite / DuckDB 接続（paper_trading なら専用 DB を使用）
    3. BrokerClient 作成（本番 or Mock）
    4. OrderRepository / OrderManager / RiskManager / Reconciler 組立
    5. ExecutionEngine をスレッドで実行し、stop flag を監視して Graceful に停止
  - stop フラグ: data/stop_requested.flag を検知

- run_monitoring.py
  - SystemMonitor を定期的に呼び出して system_status 等を記録
  - MONITOR_POLL_INTERVAL で間隔調整可能

- monitoring_db.py
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブル初期化とマイグレーションを提供
  - MonitoringDB クラスで永続化操作（log_system_status, log_trade_event, upsert_dashboard 等）を行う

- portfolio/*
  - 候補選定、重み計算、単元調整、aggregate cap のスケーリングなど、ポートフォリオ構築に関する純粋関数群を提供

- research/*
  - DuckDB 接続を受け取り、ファクターや将来リターン、IC、統計サマリーを計算

- ai/news_nlp.py
  - 指定ウィンドウの raw_news を銘柄ごとに集約し、OpenAI に複数銘柄をバッチで投げて JSON 形式でスコアを得て ai_scores テーブルに書き込む
  - リトライ/バックオフやレスポンス検証、部分失敗時の部分書込（冪等性考慮）などフェイルセーフ設計

---

## 注意事項 / 運用上のポイント

- 本番 (KABUSYS_ENV=live) での実行は慎重に:
  - 必須環境変数（API トークン・パスワード）や LINE 通知先が適切かを validate_config で確認してください。
  - KILL_FLAG_CLEAR_ON_START は本番環境で 1 にしないことを推奨（Kill Switch を誤ってクリアする危険あり）。

- .env ファイルは絶対に Git に入れないでください（config_setup のヘッダにも注意書きあり）。

- モジュール間の DB スキーマ変更はマイグレーション処理が一部含まれていますが、バックアップを取ってから運用してください。

- OpenAI API 連携:
  - OPENAI_API_KEY を環境変数に設定してください。
  - API のレスポンスやコストに注意。news_nlp はバッチサイズ・文字数上限などを設定しているものの、実行コストは環境次第です。

- ロギング:
  - setup_logging を各起動スクリプトで呼び出して統一的なログを得ます（stdout + 日次ファイル）。
  - logs/ ディレクトリの作成に失敗した場合はファイル出力は無効化され、コンソールのみになります。

---

必要であれば、README に以下の内容も追加できます：
- カスタム systemd / service のサンプル unit ファイル（run_execution/run_monitoring をサービス化する例）
- docker-compose / コンテナ化手順
- 詳細な DB スキーマ定義（SQL）
- 開発用のユニットテスト実行方法

追加してほしいセクションがあれば教えてください。