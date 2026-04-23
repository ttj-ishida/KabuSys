# KabuSys

日本株向け自動売買・リサーチ基盤（ライト版）。  
本リポジトリは取引実行エンジン、監視/アラート、ポートフォリオ構築、ファクター計算、LLM を使ったニュースセンチメントなどを含んだモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の要素で構成される日本株の自動売買／リサーチ基盤です。

- ExecutionEngine: 発注ロジック、注文管理、リスク管理、再整合（reconciler）
- Monitoring: システム状態監視、トレード監視、リスク監視、Kill Switch（フラグで Execution 停止）
- Portfolio construction: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- Research: ファクター計算（Momentum / Volatility / Value 等）、特徴量解析（IC 等）
- AI: OpenAI を使ったニュース NLP（銘柄ごとのセンチメントスコア） / レジーム判定
- Tools: ペーパートレード結果の検証レポート生成など
- 設定支援: 対話式 .env ウィザード、設定検証 CLI

設計方針として、DB（DuckDB/SQLite）経由でのデータ参照を中心にし、発注 API との結合は明確に分離されています。Paper Trading と Live の分離や、監視用 DB の永続化、プロセス優先度設定など運用面の考慮が含まれます。

---

## 主な機能一覧

- 環境設定ウィザード（.env ファイル生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替対応）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、data/paper_trading.db を用いる
- Monitoring 起動スクリプト（ポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で間隔指定（デフォルト 60 秒）
- 監視 DB 永続化（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
- Kill Switch: リスク閾値超過時に data/kill.flag を書き込み、ExecutionEngine に停止信号を送信
- Portfolio construction: 候補選定、等重・スコア重み、リスクベースのポジションサイズ計算、セクターキャップ
- Research: DuckDB を使ったファクター計算（momentum / volatility / value）や IC 計算
- AI モジュール:
  - ニュース NLP（OpenAI）で銘柄別スコアを ai_scores テーブルへ書き込み
  - レジーム判定（MA200 とマクロセンチメントの合成）
- ユーティリティ:
  - ログ設定（コンソール + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順

前提
- Python 3.10+（typing の | 構文を利用）
- SQLite（標準ライブラリ）
- DuckDB、psutil、openai（AI 機能を使う場合）、PyYAML（設定検証で YAML を検証したい場合）

推奨パッケージ（例）
pip install duckdb psutil openai PyYAML

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 初期設定（.env）を作成
   - python -m kabusys.config_setup
   - ウィザードに従って JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を設定
   - .env を生成したら設定検証を実行:
     - python -m kabusys.validate_config
5. データディレクトリの準備（必要であれば）
   - デフォルトの DB 等は data/ 配下に置かれます。ログは logs/ 配下へ。

注意:
- OpenAI を使う場合は環境変数 OPENAI_API_KEY を設定してください。
- .env は絶対に Git にコミットしないでください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

---

## 使い方（主要コマンド例）

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットすると mock ブローカーで動作し data/paper_trading.db に記録

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI: ニューススコア生成（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY を使用

- レジーム判定（プログラム呼び出し）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

監視制御（運用）
- Execution 停止をトリガーする Kill Switch は data/kill.flag を書き込みます。
- 監視プロセスや実行プロセスの強制停止・終了ループ通知に data/stop_requested.flag などを使う起動スクリプトがあります（run_monitoring/run_execution）。

ログ
- setup_logging() により stdout と logs/<app_name>.log（日次ローテート）に出力されます。
- LOG_DIR 環境変数でログ保存先を変更可能。

---

## 監視 DB（SQLite）スキーマ概要

monitoring_db.init_monitoring_db により作成される主なテーブル

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 に集計を1行で保持 (portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

監視／リスクロジックはこの DB に永続化して、Monitoring / Execution 間の状態共有やアラート判定に利用します。

---

## ディレクトリ構成

以下はソースツリー（主要ファイル）の抜粋です（src/kabusys 以下）:

- run_monitoring.py — Monitoring ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数／設定管理（.env 自動読み込み含む）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- __init__.py — パッケージ定義

サブパッケージ:
- monitoring/
  - monitoring_db.py — 監視 DB 永続化層
  - system_monitor.py — システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス検出）
  - trade_monitor.py — （トレード監視、滞留・異常約定の検出）※実装ファイルあり
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 各モニタの束ね（ポーリング）
  - alert_manager.py —（アラート送信）※実装ファイルあり
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py, ...
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py — OpenAI を使ったニューススコアリング
  - regime_detector.py — レジーム判定
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- data/ (実行時に使用するフラグファイル・DB 等を置く場所: data/*.db, data/kill.flag, data/execution.pid など)
- logs/ (ログファイル出力先、デフォルト)

（実際のファイル一覧はリポジトリを参照してください）

---

## 運用上の注意

- .env は機密情報を含むため、絶対に Git 等へコミットしないこと。
- KABUSYS_ENV を `live` にすると本番モードとなり、実際に発注が行われます。設定を慎重に確認してください（validate_config の live チェックを活用）。
- Monitoring は監視用 SQLite を用いて本番 DB の状態を常に記録します。monitoring は環境に依らず本番 sqlite_path を使用する設計になっている点に注意してください（run_monitoring の仕様）。
- OpenAI 等の外部 API の呼び出しはレート制限やエラーを考慮したリトライ実装がされていますが、API キーの漏洩や課金には注意してください。
- プロセス優先度や PID ファイル、Kill Flag 等は運用スクリプトで使用されます。OS 権限によっては priority 設定に失敗することがあります（ログに警告が出ます）。

---

以上がリポジトリの README 相当の概要です。必要であれば、各モジュール（execution, monitoring, ai, research）ごとの詳しい使い方や設計ドキュメント（例: API、関数サンプル、設定値の詳細）を別途作成します。どのモジュールの詳細を優先して欲しいか教えてください。