# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ兼実行スクリプト群）。  
このリポジトリは、発注エンジン（Execution）、監視系（Monitoring）、研究用ツール群（Research / Portfolio）、AI を用いたニュース/NLP モジュール等を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を持つモジュール型システムです。

- 発注・実行エンジン（ExecutionEngine）
  - 実口座／ペーパートレードの切替（KABUSYS_ENV）
  - リスク管理・注文管理・約定ログ記録
- 監視（Monitoring）
  - システム資源（CPU/メモリ/ディスク）、プロセス生存、データ鮮度の定期チェック
  - リスク（ドローダウン、ポジション数）監視、Kill Switch（停止フラグ）生成
- 研究（Research）
  - DuckDB を利用したファクター算出（Momentum / Volatility / Value 等）
  - 特徴量探索、IC 計算、前方リターン計算
- ポートフォリオ構築（Portfolio）
  - 候補選定、配分計算（等金額/スコア加重/リスクベース）
  - セクターキャップ、レジーム乗数の適用
- AI モジュール（AI）
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュースセンチメント）
- ツール
  - ペーパー取引検証レポート生成スクリプト 等

---

## 主な機能一覧

- 環境依存の分離
  - `KABUSYS_ENV` により `development` / `paper_trading` / `live` を切替
  - `paper_trading` 時は Mock ブローカー、専用 SQLite（デフォルト: `data/paper_trading.db`）を使用
- 監視ポーリング
  - `run_monitoring.py` によるポーリングループ（デフォルト 60 秒、環境変数で上書き可）
  - system/trade/risk 各種モニタ統合とアラート評価
- Kill Switch
  - 必要条件を満たすと `data/kill.flag` を書き込み、Execution を停止させる機能
- Research / Portfolio
  - DuckDB 上で完結するファクター計算・ポジションサイズ決定
- AI（OpenAI）
  - ニュース集約 → LLM で銘柄別スコア生成（`ai.score_news`）
  - マクロニュース + ETF MA200 を元にレジーム判定（`ai.regime_detector`）
- 運用支援
  - `.env` 対話式ウィザード（`config_setup.py`）
  - 起動前設定検証 CLI（`validate_config.py`）
  - ペーパートレード検証レポート（`tools/paper_verification_report.py`）

---

## 動作環境 / 依存

- Python 3.10+
- 推奨パッケージ（一例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（`validate_config` が YAML 検証を行う場合に必要）
- インストール例:
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements ファイルが無い場合は上記を手動でインストール）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML

3. 環境変数の準備 (.env)
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに `.env` を作成し、以下の主要キーを設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|...)
     - OPENAI_API_KEY (AI 機能利用時に必要)
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知用、任意）
   - 自動 .env 読み込み:
     - デフォルトでプロジェクトルートの `.env` / `.env.local` が自動読み込みされます。
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合は `--strict` を付ける。

---

## 実行方法（使い方）

基本的にはパッケージをモジュール実行します。

- 監視ループ起動（Monitoring）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 動作:
    - `Settings` から DB パスを読み取り SQLite/ DuckDB に接続します（監視用は本番 sqlite_path を使用; 環境に依らず同じ監視 DB を参照）。
    - プロセス優先度を "high" に設定します（可能な場合）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定（デフォルト 60）。不正値は 60 秒にフォールバック。
    - 停止: プロジェクトルートの `data/stop_requested.flag` が存在するとループは終了します。

- 実行エンジン起動（Execution）
  - コマンド:
    - python -m kabusys.run_execution
  - 動作:
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）にログを記録します。本番 DB と完全分離されます。
    - 実行前に `data/stop_requested.flag` が既に存在する場合は起動せず終了します。
    - 実行中に `data/stop_requested.flag` を作成するとエンジンに停止シグナルが送られ、可能な限り安全に停止します。
    - 実行時、プロセス PID はデフォルト `data/execution.pid` に記録されます（`Settings.pid_file_path`）。

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - --db PATH もしくは環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI / レジーム判定・ニューススコアリング
  - モジュール関数として呼び出します（CLI ラッパーは無し）。
  - 例（Python から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="xxx")
  - OpenAI API キーは引数に渡すか環境変数 `OPENAI_API_KEY` を使用。

---

## 主要環境変数一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO (等)
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0|1（本番環境では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒; run_monitoring 用; デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定動作 (instant|partial|never|reject)
- OPENAI_API_KEY: OpenAI を使う場合に必要

---

## 停止 / Kill フロー

- 停止要求（監視・実行共通）
  - `data/stop_requested.flag` を作成すると `run_monitoring` / `run_execution` が検知して終了または停止処理を行います。
- Kill Switch（自動停止）
  - 監視モジュールがリスク条件（例: ドローダウン超過）を検出すると `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に自動で kill.flag をクリアします（本番では危険なので注意）。

---

## ログ

- ログ仕組みは共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用します。
- デフォルトでコンソール（stdout）と日次ローテーションでファイル（logs/<app_name>.log）出力を行います。
- ログディレクトリは環境変数 `LOG_DIR` または引数で上書き可能。存在しない場合は作成を試みます。
- ログレベルは環境変数 `LOG_LEVEL` で指定可能。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイル・パッケージ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — 監視ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB ラッパー
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文/約定監視（ファイル内にあり）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — kill.flag 書込
    - monitoring_engine.py   — 各 Monitor 統合ループ
    - alert_manager.py       — （通知用抽象層）
  - execution/
    - execution_engine.py    — 実行エンジン（Engine）
    - broker_factory.py      — BrokerClient 作成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 絡み
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパー取引検証レポート生成ツール

---

## 開発上の注意 / 運用メモ

- DuckDB / SQLite によるデータ参照が多く、ファイルパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）の管理に注意してください。
- `paper_trading` モードは本番データベースと分離される設計です。ペーパートレード運用時は `KABUSYS_ENV=paper_trading` を必ず指定してください。
- AI 機能（OpenAI）を使う場合、API キーの管理（OPENAI_API_KEY）には注意してください。課金発生の可能性があります。
- `KILL_FLAG_CLEAR_ON_START=1` は開発時のみ推奨。本番で誤って設定すると安全装置を無効化する可能性があります。
- `MONITOR_POLL_INTERVAL` は監視の間隔を秒で指定します（run_monitoring 用）。不正な値は 60 秒にフォールバックします。

---

## よく使うコマンド例

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視開始
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン開始
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

この README はプロジェクトの主要な使い方・設定方法をまとめたものです。詳細な実装や設計に関しては該当モジュール（`src/kabusys/*`）のドキュメントストリングやコードコメントを参照してください。必要であれば README の追加改善（例: 具体的な ExecutionEngine の運用手順、DB スキーマ説明、テスト手順）を行います。