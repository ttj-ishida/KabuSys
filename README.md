README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコア部分を実装した Python パッケージです。本リポジトリには以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- 発注・注文管理、リスク管理、約定ログの永続化（SQLite）
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制約）
- リサーチ機能（ファクター計算、将来リターン、IC 計算 等）
- AI 支援モジュール（ニュースの NLP スコアリング、レジーム判定）※OpenAI API 必須
- 設定ウィザードと設定検証ツール、ペーパートレード検証レポート生成

主な特徴
-------
- 本番／ペーパートレードの分離: KABUSYS_ENV に応じ、発注先や SQLite DB を切り替え可能
  （paper_trading は data/paper_trading.db を使用）
- モジュール化された監視（System / Trade / Risk）と Kill Switch による安全停止
- DuckDB を用いたリサーチ向け高速集計（prices_daily / raw_financials を前提）
- OpenAI を用いたニュースセンチメント解析（バッチ & 再試行ロジック搭載）
- .env 対話式ウィザード（config_setup）と起動前チェック（validate_config）

前提条件
--------
- Python 3.9 以上を推奨
- 主な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/*.yaml の検証を行う場合）
- システムのファイル書き込み権限（data/ や logs/ ディレクトリ）

インストール（開発環境）
-----------------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※プロジェクトに requirements.txt がある場合はそれを利用してください。

環境設定 (.env)
---------------
対話式ウィザードで .env を作成できます:

- python -m kabusys.config_setup

主に入力が必要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）

推奨・その他
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時）
- OPENAI_API_KEY — OpenAI を利用する場合に必須
- LOG_LEVEL / LOG_DIR / KILL_FLAG_CLEAR_ON_START / PAPER_FILL_MODE 等

設定検証
--------
作成した .env や config/*.yaml の整合性を起動前にチェックできます:

- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

データベース初期化
------------------
多くの起動スクリプトは内部で monitoring DB のスキーマを自動作成します（init_monitoring_db）。明示的な初期化は不要です。

起動・使用方法
--------------

1) 監視プロセス（SystemMonitor のポーリング）
- 実行:
  - python -m kabusys.run_monitoring
- 特記事項:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず）
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します

2) 実行エンジン（ExecutionEngine）
- 実行:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag があれば起動せず終了
  - 実行中に stop_requested.flag が作られるとエンジンを停止
  - 実行時に PID を data/execution.pid に記録

3) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4) AI 機能
- ニューススコアリング:
  - kabusys.ai.score_news を呼び出して ai_scores テーブルへ書き込み
  - OpenAI API キー（OPENAI_API_KEY）が必要
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime を利用（OpenAI API が必要）

停止・Kill Switch
-----------------
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を送ります。
- 手動で停止させたい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）。

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - コンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log）を設定
  - LOG_DIR 環境変数で出力先を上書き可能
  - LOG_LEVEL でログレベルを指定

主要モジュールと機能（要約）
---------------------------
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト
- run_execution.py: ExecutionEngine 起動スクリプト（paper_trading 時に MockBroker）
- config_setup.py: .env 対話式ウィザード
- validate_config.py: 起動前チェック CLI
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- ai/news_nlp.py: ニュースの LLM ベースのセンチメントスコア取得（OpenAI）
- ai/regime_detector.py: マクロセンチメント＋ETF MA で市場レジーム判定（OpenAI）
- research/*: ファクター計算、将来リターン、IC、統計サマリー等（DuckDB ベース）
- portfolio/*: 候補選定・重み付け・セクター制約・株数決定ロジック（純粋関数群、DB 参照なし）
- monitoring/*: MonitoringDB（SQLite）、System/Trade/Risk Monitor、KillSwitch、MonitoringEngine
- utils/*: logging_setup、process_priority（psutil を利用して優先度設定）等
- config.py: 環境変数ラッパー Settings（デフォルトや必須チェックを実装）

よく使うファイル・パス
---------------------
- デフォルト DuckDB: data/kabusys.duckdb
- デフォルト monitoring SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- ログディレクトリ: logs/（デフォルト）
- 停止フラグ: data/stop_requested.flag
- Kill フラグ: data/kill.flag
- PID ファイル: data/execution.pid

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_monitoring.py
- run_execution.py
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照される想定)
- execution/ (発注周りの実装群、factory 等)
- utils/
  - logging_setup.py
  - process_priority.py
- data/ (実行時に使用: DB・フラグ・PID などを格納)

開発者向けメモ
--------------
- settings は kabusys.config.Settings 経由で取得してください（各種デフォルト・検証ロジック実装済み）。
- DuckDB を使うリサーチ関数は接続を引数に取るためユニットテストしやすい設計です。
- OpenAI 呼び出し部は再試行・バックオフ・レスポンスバリデーションを備えています。テスト時は内部関数をモックしてください（例: _call_openai_api の patch）。
- process_priority は psutil を利用しています。権限や OS により挙動が異なるため警告ログでフォールバックします。

サポート / 追加情報
-------------------
- 起動・設定で不明点がある場合は validate_config を実行し、出力に従って修正してください。
- production（本番）実行時は KABUSYS_ENV=live に設定する前にすべての通知先（LINE 等）やキルスイッチ挙動を確認してください。

以上。README に不足があれば、どの部分を詳しく記載したいか教えてください。