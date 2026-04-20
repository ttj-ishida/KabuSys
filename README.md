KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うための軽量フレームワークです。本リポジトリは以下の主要機能群を備えます:

- ExecutionEngine: 発注・注文管理・リスク管理の実行エンジン（本番/ペーパートレード対応）
- Monitoring: システム状態・注文状況・リスク指標の定期監視とアラート／Kill Switch 機構
- Portfolio construction: 候補選定・重み計算・ポジションサイズ決定・セクター制限等の純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI 補助: ニュース NLP（OpenAI）による銘柄センチメント評価、レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定など

主な特徴
--------
- 環境変数 / .env による柔軟な設定管理（config.py）
- ペーパートレードと本番データベースの明確な分離（PAPER_TRADING_SQLITE_PATH）
- モジュール化されたポートフォリオ構築ロジック（純粋関数・副作用なし）
- DuckDB を使った分析用途向けの高速クエリ
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント・レジーム判定（API キーは外部設定）
- ログはコンソール＋日次ローテーションのファイル出力（logs/<app>.log）

セットアップ（開発向け・手順）
-------------------------
前提: Python 3.10+（型注釈に Path | None などを使用）。必要パッケージは用途に応じて下記をインストールしてください。

推奨パッケージ（一例）
- duckdb
- psutil
- openai
- PyYAML（validate_config で YAML 検証を行う場合）

pip 例:
    pip install duckdb psutil openai pyyaml

1) リポジトリをクローン / ワーキングディレクトリをルートにする

2) .env の作成
- 対話式ウィザード:
    python -m kabusys.config_setup
  既存 .env がない場合はこのコマンドで必要な環境変数を対話的に作成できます。

- 手動例 (.env の最小例):
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    KABU_API_PASSWORD=your_kabu_password
    KABUSYS_ENV=development
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    LOG_LEVEL=INFO
    OPENAI_API_KEY=sk-xxxx...   # AI 機能を使う場合

3) 設定検証（起動前チェック）
    python -m kabusys.validate_config
  --strict を付けると警告も失敗として扱います:
    python -m kabusys.validate_config --strict

4) データディレクトリ
- デフォルトでは data/ と logs/ を使用します。多くのスクリプトが自動で作成しますが、必要なら予め作成してください。

使い方（主要スクリプト）
-----------------------

- Execution Engine 起動（本番 or paper_trading）
    python -m kabusys.run_execution

  説明:
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）に記録されます。本番では settings.sqlite_path（デフォルト data/monitoring.db）などを利用します。
  - 起動時に data/execution.pid に PID が書き出されます。停止は data/stop_requested.flag や data/kill.flag による制御をサポートします。

- Monitoring 起動
    python -m kabusys.run_monitoring

  説明:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を利用してログを永続化します（環境に依存せず本番 DB を使用する設計）。
  - run_monitoring が参照するストップフラグ: data/stop_requested.flag

- 環境設定ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: PID / kill flag 関連設定

ログ
----
- setup_logging() により stdout 出力 + 日次ローテーションのファイル出力を行います。
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ローテーション: 日次、30 日分保持

重要なファイル・フラグ
--------------------
- data/kill.flag: Kill Switch による ExecutionEngine の停止指示（KillSwitch モジュールが書き込み）
- data/stop_requested.flag: 手動停止フラグ。run_monitoring / run_execution が検知してループを抜けます
- data/execution.pid: ExecutionEngine の PID がここに書かれます

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要なモジュールとファイルのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数／設定管理
  - config_setup.py           -- .env 対話式ウィザード
  - validate_config.py        -- 設定検証 CLI
  - run_execution.py          -- ExecutionEngine 起動スクリプト
  - run_monitoring.py         -- Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        -- ログ設定ユーティリティ
    - process_priority.py     -- プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        -- SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

設計上の注意点 / 運用上の注意
----------------------------
- 本番環境（KABUSYS_ENV=live）では設定を慎重に。validate_config はライブ環境向けの追加警告を出します。
- AI 機能を使用するには OPENAI_API_KEY が必要です。API 呼び出しはコスト発生とレスポンス不安定性（レート制限）に注意してください。実装はリトライ・フォールバックを行いますが、失敗時は macro_sentiment=0 等で安全側にフォールバックします。
- ペーパートレード環境は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。ペーパートレードのデータは data/paper_trading.db に記録される設定がデフォルトです。
- run_monitoring は監視用 DB（sqlite_path）にデータを記録します。監視は本番 DB を使う設計になっています（環境に依存せず常に sqlite_path を参照）。
- ログディレクトリや DB ファイルの親ディレクトリが存在しない場合、スクリプト側で自動作成されるケースがありますが、権限やパスに注意してください。

拡張 / 開発メモ
----------------
- DuckDB を用いた分析・研究モジュールは外部データを取り込みやすい設計です。prices_daily / raw_financials / raw_news 等のテーブルを用意して解析に利用できます。
- Portfolio と Position Sizing は純粋関数群として分離されているため、単体テストが容易です。
- OpenAI 呼び出し部分はユニットテスト時に差し替え（mock）可能な設計になっています。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートに LICENSE 等があれば参照してください（この README には含まれていません）。

最後に
------
この README はコードベース内の docstring と設定周りのロジックに基づき作成しています。実運用前に必ず python -m kabusys.validate_config で設定検証を行い、ローカルで十分に動作確認（ペーパートレード）を行ってください。必要であれば追加の運用手順（systemd / supervisor / cron ジョブなど）や監視・監査ログの運用ルールを整備してください。