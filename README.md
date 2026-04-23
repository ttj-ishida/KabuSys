# KabuSys

日本株向け自動売買システムのコアライブラリ（ドメインロジック・運用ユーティリティ群）。  
このリポジトリは、Execution エンジン・Monitoring 周りの起動スクリプト、ポートフォリオ構築・ポジション決定ロジック、Research/AI 補助モジュールなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム用に設計された Python モジュール群です。主な要素は次の通りです。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（プロセス稼働監視、注文ログ、リスクイベント記録、Kill Switch）
- Portfolio Construction（銘柄選定、重み付け、ポジションサイズ決定）
- Research（ファクター計算、特徴量探索、IC 計算）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 開発 / 運用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計上の特徴:
- 設定は .env または環境変数で管理（自動ロード機能あり）
- Paper Trading と Live 本番 DB を分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を分析用 DB として併用
- OpenAI（gpt-4o-mini）を使ったニュース解析機能（任意）
- モジュールはテストしやすい純粋関数／明確な I/O 境界を意識した実装

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
  - Settings クラス: 環境変数の集中管理（既定値と検証付き）
- Monitoring
  - monitoring_db.py: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 複数モニタの束ねとアラート判定
  - kill_switch.py: 条件により data/kill.flag を書き込む
- Execution（主要部は別ファイル群に実装）
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager, OrderRepository, Reconciler, RiskManager, ExecutionEngine（起動スクリプトから組み立て）
- Portfolio（純粋関数）
  - portfolio_builder.py: 候補選定、等配分・スコア配分
  - position_sizing.py: 株数計算、単元丸め、資金スケールダウン
  - risk_adjustment.py: セクターキャップ、レジーム乗数
- Research
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ
- AI
  - news_nlp.py: raw_news を OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py: ma200 とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - logging_setup.py: 統一的ログ設定（stdout + 日次ローテート）
  - process_priority.py: プロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成

---

## セットアップ手順（開発 / ローカル実行向け）

1. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必須（最小）: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実プロジェクトでは requirements.txt / poetry / pipenv 等で管理してください。

3. プロジェクトルートに移動（README のあるディレクトリ）
   - パッケージは src 配下にあるため、実行時はプロジェクトルートをカレントにすることを推奨します。

4. .env の作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に必須環境変数を設定してください。

5. 必須環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - その他（オプションあるいはデフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - PAPER_FILL_MODE（paper_trading 用: instant, partial, never, reject）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト 60 秒）

6. DB 初期化
   - run_execution や run_monitoring は起動時に必要テーブルを作成します（init_monitoring_db）。
   - DuckDB のテーブルは外部スクリプトや ETL で用意してください（prices_daily / raw_financials / raw_news など）。

---

## 使い方（主要コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を失敗扱い）:
    - python -m kabusys.validate_config --strict

- Execution エンジン起動
  - 本番/開発/ペーパートレードの切替は KABUSYS_ENV で制御
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 例（デフォルト development）:
    - python -m kabusys.run_execution
  - 注意:
    - run_execution は data/execution.pid を扱い、data/stop_requested.flag により外部停止を検知します。
    - ペーパートレード時は broker が MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と完全分離）。

- Monitoring 起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプション or PAPER_TRADING_SQLITE_PATH 環境変数で指定可。

- AI 機能（プログラム API として利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")

  ※ OpenAI キーは api_key 引数か環境変数 OPENAI_API_KEY で指定。API 呼び出しは冗長なリトライとフォールバックを含む安全設計です。

---

## 運用メモ / 注意点

- Kill Switch
  - KillSwitch は監視条件（ドローダウン超過等）で Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine はこのファイルの存在を検知して停止します。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされるため危険です（デフォルト 0 を推奨）。

- ログ
  - ログは stdout と logs/<app_name>.log（日次ローテート、30日保持）へ出力されます。
  - ログレベルは LOG_LEVEL 環境変数で制御。

- DB 分離
  - Paper Trading と 本番用 SQLite は分離されています（PAPER_TRADING_SQLITE_PATH）。
  - Monitoring 用 DB は Settings.sqlite_path（デフォルト data/monitoring.db）。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼び、可能なら OS の優先度を上げます（psutil に依存）。権限不足の場合は警告を出して継続します。

- 自動環境変数ロード
  - プロジェクトルートが検出できれば .env、.env.local が自動ロードされます。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成

（主要ファイル・サブパッケージの一覧。src/kabusys 以下）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - config.py                       — Settings クラス（環境変数管理）
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 設定検証 CLI
    - utils/
      - __init__.py
      - logging_setup.py              — 共通ログ設定
      - process_priority.py           — 優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (別ファイル)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (別ファイル)
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - (その他実装ファイル)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py

- data/    — 実行時に使用するファイル群（pid / flag / sqlite 等、デフォルトパス）
- logs/    — ログ出力先（デフォルト）

---

## 追加情報 / 開発者向け

- DuckDB を使った Research モジュールは、prices_daily / raw_financials / raw_news 等のテーブルを前提に設計されています。分析データの投入は ETL 側で行ってください。
- AI 呼び出しは OpenAI の SDK（OpenAI Python）に依存します。API 変更があった場合は wrapper 部分を更新してください（score_news/_call_openai_api 等はテスト時に差し替え可能な設計）。
- validate_config.py は PyYAML がインストールされていれば config/*.yaml の内容検証も行います。無ければ警告表示でスキップします。
- 各モジュールは冪等性・フェイルセーフを意識しており、例外発生時はログに記録して継続するパターンが多いです。

---

必要があれば、README にサンプル .env テンプレートや起動用 systemd / Supervisor のユニット例、Dockerfile/Compose サンプルを追加で作成します。どの情報を優先して追記しますか？