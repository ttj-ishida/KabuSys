README — KabuSys (日本株自動売買システム)
=====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なパイプライン／ライブラリ群です。
主要な機能は以下のとおりです。

- 自動売買実行エンジン（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch、監視ログは SQLite に永続化）
- ポートフォリオ構築ユーティリティ（候補選択・重み計算・ポジションサイズ算出・セクター上限）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI/LLM 連携（ニュースセンチメントスコアリング、レジーム判定。OpenAI API を利用）
- Paper Trading 用の分離された DB と MockBroker（KABUSYS_ENV=paper_trading）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

主な特徴
--------
- 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化。DuckDB は時系列・研究用途に使用（デフォルト: data/kabusys.duckdb）。
- Paper Trading は本番 DB と完全分離（data/paper_trading.db を使用）。
- プロセス優先度・CPU アフィニティ設定ユーティリティ（psutil ベース）。
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント集計・市場レジーム判定。
- フェイルセーフ設計: API エラーや欠損データはフォールバックやログにより安全に継続。

前提 / 依存関係
----------------
少なくとも次の Python パッケージが必要です（バージョンはプロジェクト要件に合わせて調整してください）:

- python >= 3.9
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード使用時)

その他: SQLite は標準ライブラリ sqlite3 を使用。外部 API を使う機能（OpenAI、kabuステーション など）を使う場合はそれぞれの API キー／資格情報が必要です。

セットアップ手順
----------------
1. リポジトリをクローンし、開発用仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt がある場合はそちらを利用してください）:
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の設定:
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant|partial|never|reject  (paper_trading 用)
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0 or 1
     - MONITOR_POLL_INTERVAL=60  (監視ループのポーリング間隔 秒)

   例: .env（最小）
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...

4. データディレクトリ作成（必要に応じて）:
   - mkdir -p data

使い方
------

実行方法の前提:
- このリポジトリをパッケージとしてインストールしていない場合、実行時に PYTHONPATH を src に向けるか、プロジェクトルートから python -m を使います。
  例: PYTHONPATH=src python -m kabusys.run_monitoring
  または (Windows PowerShell の場合)
  $env:PYTHONPATH = "src"; python -m kabusys.run_monitoring

1) 監視ループの起動（SystemMonitor 単体）
   - 簡単な起動:
     PYTHONPATH=src python -m kabusys.run_monitoring
   - 説明:
     - プロセス優先度を high に設定（可能な場合）。
     - Settings に基づいて monitoring 用 SQLite（settings.sqlite_path）と DuckDB に接続し、init_monitoring_db() によって監視用テーブルを生成します（冪等）。
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
     - 停止はプロジェクトルートの data/stop_requested.flag の作成で検知して終了します。

2) 実行エンジンの起動（ExecutionEngine）
   - 起動:
     PYTHONPATH=src python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、Paper Trading 用 DB（settings.paper_sqlite_path）を使用して本番 DB と分離します。
     - 実行中は data/execution.pid に PID を書き、data/stop_requested.flag の作成で停止を検知します。
     - KillSwitch（監視側）が作成する data/kill.flag を用いた停止の運用も想定しています（Settings.kill_flag_path）。

3) Streamlit 監視ダッシュボード
   - 起動例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視用 SQLite を read-only で開き、ダッシュボードを表示します。
     - MonitoringEngine を起動してログが入っていないと表示は空になります。

4) Paper Trading 検証レポート
   - 実行:
     PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     --db PATH で DB ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH 優先）。

5) AI（ニューススコアリング / レジーム判定）
   - ニュースセンチメント: kabusys.ai.score_news を呼び出す（スクリプトとしての CLI は未提供）。関数 signature:
     score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str | None = None) -> int
   - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - OpenAI API キー（OPENAI_API_KEY）を設定するか、api_key 引数で渡す必要があります。
     - API 呼び出しはリトライやフォールバック（失敗時は 0.0 フォールバック等）を実装していますが、API 費用やレート制限に注意してください。

停止方法
--------
- 監視ループ / 実行エンジンは以下のフラグファイルを検知して安全に停止します:
  - data/stop_requested.flag — run_monitoring/run_execution が監視している汎用停止フラグ
  - data/kill.flag — KillSwitch が書き込むファイル（ExecutionEngine 側での取り扱いを確認してください）
- また通常は Ctrl+C (KeyboardInterrupt) でも停止できます。

設定関連の注意
----------------
- Settings モジュールは .env と .env.local を自動でプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境変数の必須項目（Settings._require を通るもの）が未設定だと起動時に例外が発生します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- PAPER_FILL_MODE は paper_trading 時のモックの約定挙動を制御します（instant/partial/never/reject）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数/設定管理
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py             — プロセス優先度・CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py                — SQLite による永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py             — （ファイルは存在します。実行ロジックを含む）
  - broker_factory.py
  - broker_api.py
  - order_record.py
  - order_* （その他注文関連）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                      — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py               — 市場レジーム判定（OpenAI）
- data/（実行時生成推奨）
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (デフォルト PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

開発・運用上の注意
-------------------
- 本番運用時は KABUSYS_ENV=live、paper_trading での実運用は分離された DB（PAPER_TRADING_SQLITE_PATH）を必ず利用してください。
- process priority / cpu affinity の設定はプラットフォーム依存です。権限不足等で失敗しても warning を出してスキップします。
- OpenAI との連携は API 利用料とレート制限に注意してください。news_nlp と regime_detector はリトライ・フォールバック挙動を持ちますが、API キーの管理は厳重に行ってください。
- 監視テーブルやトランザクション（DuckDB/SQLite）周りは、既存 DB に対するマイグレーション（列追加など）をコード側で行っています。バックアップを推奨します。

貢献・拡張
----------
- 研究モジュール（research）やポートフォリオ構築ロジックは純粋関数として設計されているため、ユニットテストが書きやすくなっています。テスト追加・改善歓迎です。
- Broker API の抽象化により新しいブローカー実装が可能です（execution/broker_factory.py を参照）。

ライセンス
----------
（この README ではライセンス表記は含めていません。リポジトリに LICENSE ファイルがあればそちらを参照してください。）

以上。README の補足や実行方法の具体的なテンプレート（.env.example 等）が必要であれば、使用する OS／環境に合わせて追記します。