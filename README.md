# KabuSys

日本株向け自動売買システムのコアライブラリ群（開発中）  
この README はリポジトリ内の Python モジュール群に基づき、導入・運用に必要な情報を日本語でまとめたものです。

> 注意: 実行スクリプト・AI 統合・DB 書き込みを含みます。実運用前に設定検証・テストを十分に行ってください。

---

## 概要

KabuSys は日本株の自動売買を支援するモジュール群です。  
主な機能は以下の通りです。

- ファクター計算（モメンタム／バリュー／ボラティリティ等） — DuckDB 経由での時系列計算
- ポートフォリオ構築（候補選定、重み付け、位置サイズ計算、セクター制約、レジーム乗数）
- 実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視（MonitoringEngine）: システム稼働・注文ログ・リスク監視、Kill Switch（停止フラグ）
- Paper Trading 用検証レポート生成ツール
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 環境設定ウィザード / 設定検証 CLI
- ログ管理ユーティリティ、プロセス優先度設定ユーティリティ等のユーティリティ群

---

## 機能一覧（抜粋）

- research
  - calc_momentum, calc_volatility, calc_value（DuckDB を用いた要因計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量解析）
- portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース・等配分など）
  - apply_sector_cap, calc_regime_multiplier（セクター制約・レジーム調整）
- ai
  - news_nlp.score_news（OpenAI を使ってニュースを銘柄ごとにスコアリング）
  - regime_detector.score_regime（MA とマクロニュースを合成して市場レジーム判定）
- monitoring
  - MonitoringDB（SQLite ベースの永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringEngine（ポーリングループ）
  - KillSwitch（data/kill.flag により ExecutionEngine を停止）
- 実行用スクリプト
  - run_execution.py（ExecutionEngine 起動）
  - run_monitoring.py（SystemMonitor ポーリング起動）
- ツール
  - config_setup.py（.env 対話ウィザード）
  - validate_config.py（設定検証 CLI）
  - tools/paper_verification_report.py（Paper Trading の検証レポート）

---

## 要件

- Python 3.10+
- 推奨（pip でインストール）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイル検証をフルに行う場合）
- 標準: sqlite3, logging, threading, datetime 等

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成・アクティベート（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows の場合は .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     - AI 機能を使わない場合は openai のインストールは任意
4. .env を作成
   - 対話ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - ウィザードで作成される主な項目（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0
5. 設定検証を実行
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります
6. data/ および logs/ ディレクトリを作成（自動作成されることが多いですが事前作成推奨）
   - mkdir -p data logs

注意:
- 自動で .env を読み込む機能は既定で有効です。自動ロードを無効化するには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 設定（主な環境変数）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 選択 / デフォルト
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - OPENAI_API_KEY: OpenAI を利用する場合に必要
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 0/1（Execution 起動時に kill.flag を自動消去するか）

Monitoring の挙動:
- run_monitoring は MONITOR_POLL_INTERVAL に従ってポーリングを行います（デフォルト 60 秒）。
- Monitoring は環境（KABUSYS_ENV）にかかわらず、本番の sqlite_path を使用して監視テーブルを操作します（監視データの一元化）。

Execution の挙動:
- run_execution は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離します。
- 実行中は data/execution.pid（既定）に PID を書きます。

停止 / Kill Switch:
- すべてのスクリプトは停止フラグファイル data/stop_requested.flag の存在をチェックして安全に終了します。
- Kill Switch（監視側の条件に応じて）は data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID が書かれます。
  - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl-C）を送る。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔変更:
    - export MONITOR_POLL_INTERVAL=30
  - 停止は data/stop_requested.flag を作成するか、Ctrl-C。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要: OPENAI_API_KEY
  - ニューススコア:
    - 呼び出し例（プログラム内）: kabusys.ai.score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - 呼び出し例: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## ロギング

- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- 標準: コンソール (stdout) とファイル出力（logs/<app_name>.log）を日次ローテーション（30 日保持）で行います。
- ログディレクトリは環境変数 LOG_DIR、またはデフォルト `logs/` を使用します。
- 設定ミスやディレクトリ作成失敗時はコンソール出力のみで継続します。

---

## プロジェクト構成（抜粋）

以下は主要ファイル／ディレクトリの仮想的な構成です（実際のリポジトリと差異がある場合があります）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (想定)
    - execution/
      - execution_engine.py (想定)
      - order_manager.py (想定)
      - order_repository.py (想定)
      - broker_factory.py (想定)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/ (実行時生成)
    - logs/ (実行時生成)
  - config/
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では特に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を確認してください。validate_config はいくつかの注意を報告します。
- Paper Trading は本番 DB と隔離するため、KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite を使用します（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を利用する機能は API レートやレスポンス不安定性に対するリトライ・フォールバックロジックを備えていますが、API キーや費用には注意してください。
- 停止フラグ（data/stop_requested.flag）を用いることで外部から安全にプロセス停止を指示できます。KillSwitch（data/kill.flag）は監視が条件を満たしたときに Execution を強制停止するため、本番では慎重に設定を扱ってください。
- ログは logs/ に保存され日次ローテーションされます。ディスク容量やログ保持ポリシーを運用に合わせて設定してください。

---

## 参考コマンド例

- .env を作成する（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config --strict
- 監視起動（デフォルト 60 秒ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（ペーパートレード時は .env で KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README は現在のコードベース（主要モジュール）に基づいて作成しています。実際のリポジトリに追加されるスクリプトや設定ファイルに応じて適宜更新してください。質問や追記してほしい項目があれば教えてください。