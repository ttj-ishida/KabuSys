# KabuSys

日本株向け自動売買／リサーチ基盤の Python パッケージ（README）。  
このドキュメントはリポジトリ内のソースコードに基づき、導入・実行方法や主要機能を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な役割は以下のとおりです。

- 市場データ（DuckDB）を用いたファクター計算・特徴量解析（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 注文管理・実行エンジン（execution）※本番・ペーパートレード対応
- システム・注文・リスクの監視とアラート（monitoring）
- ニュースの NLP によるセンチメント評価や市場レジーム判定（AI）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度等）
- 運用支援ツール（設定ウィザード、設定検証、paper trading 検証レポート）

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- 環境設定/ウィザード:
  - `.env` を対話式に生成・更新する `config_setup.py`
  - 設定・ファイルの整合性検証を行う `validate_config.py`
- 実行エンジン:
  - `run_execution.py`：ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - Execution 用 PID / Stop フラグの取り扱い（data/execution.pid, data/stop_requested.flag）
- 監視:
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
  - MonitoringDB（SQLite）による system_status / trade_logs / positions / risk_logs / dashboard の永続化
  - Kill Switch（条件に応じて data/kill.flag を生成し ExecutionEngine を停止）
- ポートフォリオ構築:
  - 候補選定、等配分・スコア配分、セクター上限、レジーム乗数、ポジションサイズ計算
- リサーチ:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る純関数群）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI:
  - ニュースを OpenAI に投げて銘柄別センチメントを作成（news_nlp.py）
  - マクロニュースと ETF MA の合成で市場レジームを判定（regime_detector.py）
- 運用ツール:
  - `kabusys.tools.paper_verification_report`：ペーパートレード検証レポート生成

---

## 必要な環境変数（主なもの）

必須（起動前に設定すること）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/デフォルト値（src/kabusys/config.py を参照）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- LOG_DIR: ログ出力先（デフォルト: logs/）

その他:
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60 秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1"=有効、デフォルト: "0"）
- PID_FILE_PATH / KILL_FLAG_PATH（デフォルトは data 内のパス）

> 注: `.env` 自動ロード機能が有効（デフォルト）で、プロジェクトルートにある `.env`／`.env.local` が読み込まれます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   - git clone ...

2. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須例:
     - duckdb
     - psutil
     - openai (AI 機能を使用する場合)
     - sqlite3 は標準ライブラリに含まれます
   - 例:
     - pip install duckdb psutil openai
   - Optional:
     - PyYAML（`validate_config.py` が config/*.yaml を検証する場合）

4. 環境変数（.env）を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（`config_setup` によって生成されるテンプレートを参照）

5. ディレクトリ（data, logs）を作成（`setup_logging` が自動作成を試みますが、事前に作ると安心です）
   - mkdir -p data logs

6. DB 初期化
   - 監視用 SQLite は起動時に自動でテーブル作成（init_monitoring_db）されます。
   - DuckDB ファイル（prices_daily / raw_financials 等）は別プロセスで用意することを前提としています。

---

## 使い方（実行例）

各スクリプトはパッケージモジュールとして実行できます。プロジェクトルートで実行してください。

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - ExecutionEngine は data/stop_requested.flag を検知すると停止します。

- 監視（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（monitoring.db）に接続し、duckdb も使用します。
  - 停止フラグ: data/stop_requested.flag を置くとループを抜けます。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して利用
  - 例: スクリプトや上位モジュールから kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す

---

## 実行時の注意点

- 監視（monitoring）は「環境にかかわらず」Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。つまり monitoring は常に本番用監視 DB を参照します。
- run_execution は KABUSYS_ENV が `paper_trading` の場合、paper_trading 用 DB を使用して本番 DB と分離します。
- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30 日保持）
  - LOG_DIR 環境変数で変更可
- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼びます。psutil が必要ですし権限によっては設定に失敗する場合があります（警告ログが出ます）。
- Kill Switch:
  - `KillSwitch` によって `data/kill.flag` が書き込まれると ExecutionEngine に停止を促します。`KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアされますが、本番では推奨されません（安全装置なので自動クリアは危険）。
- DB マイグレーション:
  - init_monitoring_db は既存 DB に対して冪等にテーブル作成を行い、必要に応じてカラム追加（簡易マイグレーション）も行います。

---

## 開発向け・内部 API

- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights（portfolio_builder）
  - calc_position_sizes（position_sizing）
  - apply_sector_cap, calc_regime_multiplier（risk_adjustment）
- research:
  - calc_momentum, calc_volatility, calc_value（factor_research）
  - calc_forward_returns, calc_ic, factor_summary（feature_exploration）
- monitoring:
  - MonitoringDB（monitoring_db.py）: system_status, trade_logs, positions, risk_logs, dashboard の読み書き
  - RiskMonitor / SystemMonitor / TradeMonitor（TradeMonitor はコードベースにあり監視ロジックを提供）
  - MonitoringEngine: 各 Monitor を束ねるポーリング実行
- ai:
  - news_nlp.score_news: raw_news を OpenAI に送り ai_scores を更新
  - regime_detector.score_regime: マクロ記事 + ETF MA を合成して market_regime を更新

これらは DuckDB 接続や sqlite3.Connection、Broker クライアント等を受け取り、ユニットテスト可能な形で設計されています（副作用を最小にした純関数群も多い）。

---

## ディレクトリ構成（抜粋）

プロジェクトルート: src/kabusys 以下を想定

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照実装あり)
    - trade_monitor.py (参照実装あり)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (運用時に作成される想定)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (ペーパートレード時)
    - kill.flag / stop_requested.flag / execution.pid など

（実際のファイルはリポジトリ内の `src/kabusys` を参照してください）

---

## 依存関係（代表的なもの）

- Python 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, etc.
- 外部ライブラリ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config.py が YAML 内容検証を行う場合に必要）
- 推奨: 仮想環境（venv）で管理すること

---

## よくある運用上の注意

- 本番環境で `KABUSYS_ENV=live` にする場合は特に `.env` の内容、LINE 通知設定、KILL_FLAG_CLEAR_ON_START を慎重に確認してください（validate_config でチェックできます）。
- OpenAI を利用する機能は API 利用料がかかります。キーの取り扱い、レートリミット、エラー時の挙動（リトライ）に注意してください。
- DuckDB のデータ（prices_daily 等）は外部 ETL で準備する想定です。research モジュールは DuckDB 接続を受けて読み取ります。

---

必要であれば、この README をベースに「運用手順書（systemd ユニットの例、cron/Task Scheduler での起動方法、バックアップ方法）」や「開発者向け API ドキュメント（関数シグネチャと戻り値の詳細）」を作成します。どの内容をより詳しく出力するか指示してください。