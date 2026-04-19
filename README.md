README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。本リポジトリは以下を含みます。

- ExecutionEngine（発注・オーダー管理・リスク管理）
- Monitoring（システム稼働・注文ログ・リスクの監視と Kill Switch）
- Portfolio 構築ユーティリティ（銘柄選定・重み付け・株数決定）
- Research（ファクター計算・特徴量探索）
- AI 補助（ニュースの NLP スコアリング・市場レジーム判定）
- 運用・検証ツール（設定ウィザード・設定検証・ペーパートレード検証レポート）

主な設計方針
- 本番／ペーパートレードを環境変数 KABUSYS_ENV で切替可能（development / paper_trading / live）。
- .env を使った設定管理をサポート。対話式ウィザードと検証 CLI を提供。
- DuckDB（分析用）と SQLite（監視・オーダーログ）を併用。
- OpenAI（gpt-4o-mini など）を用いたニュース NLP／レジーム判定機能を備える（APIキー必須、失敗時はフェイルセーフで継続）。

機能一覧
--------
- 設定管理
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行系
  - 実トレード / ペーパートレードの ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBroker を利用し data/paper_trading.db に記録（本番 DB と分離）
- 監視系
  - SystemMonitor のポーリング起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 停止フラグ data/stop_requested.flag を検知してループ終了
- モニタリング永続化（SQLite）
  - system_status / trade_logs / positions / risk_logs / dashboard のテーブルを管理
- リスク監視
  - ドローダウン検出・ポジション上限監視・Kill Switch（data/kill.flag 生成）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等加重・スコア加重、セクター制約、ポジションサイズ計算（lot 単位丸め）
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリューなど）
  - 将来リターン・IC（情報係数）計算、統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコアリング（ai_scores へ書込）
  - マクロニュース＋ETF MA200 を用いた市場レジーム判定（market_regime へ書込）
  - API エラーはリトライ／フォールバックし、運用を中断しない設計
- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. Python 仮想環境を作成して有効化
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - 必須（抜粋）: duckdb, psutil, openai, (PyYAML は config 検証で任意)
   - 例:
     pip install duckdb psutil openai

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. データ・ログ用ディレクトリ作成（自動で作られる場合もありますが手動作成推奨）
   mkdir -p data logs

4. 環境変数設定
   - 対話式で .env を作成:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照してください）

   重要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の SQLite、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使う場合に必須）
   - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject、デフォルト: instant）
   - LOG_LEVEL（DEBUG/INFO/...）

5. 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
基本的にはモジュールとして起動します。

- 実行エンジン（ExecutionEngine）起動
  - 本番モード:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパー（分離 DB を使用）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  注意:
  - paper_trading の場合、MockBrokerClient が用いられ、ログは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込まれます。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - ExecutionEngine の PID ファイルは data/execution.pid（Settings.pid_file_path）に書かれます。

- 監視ループ（SystemMonitor）起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依らず本番 DB パスを利用）。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db で指定するか環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（プログラムから呼ぶ）
  - 例: ニューススコアを生成する（Python REPL 等で）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026,4,10), api_key='sk-...')

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10), api_key='sk-...')

運用に関する注意
----------------
- ログ
  - ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト 30 日保持）。
  - setup_logging() は stdout とファイルの両方に出力します。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
  - run_monitoring/run_execution は data/stop_requested.flag を検出して安全終了します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は必要なテーブルとカラムを自動作成・マイグレーションします。

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は paper_sqlite_path を使用して本番 DB と分離します。
  - ただし Monitoring は環境に関係なく Settings.sqlite_path（本番監視 DB 想定）を使います。

依存関係（主なもの）
-------------------
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能）
- PyYAML（オプション: config 検証で YAML 構文チェックを行う場合）
- 標準ライブラリ（sqlite3, logging, threading, datetime, pathlib 等）

ディレクトリ構成
----------------
主要なファイル／ディレクトリ構成（src/kabusys を基準）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/               — 発注エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (runtime)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb (DuckDB)
    - kill.flag / stop_requested.flag / execution.pid

（実際のリポジトリでは src/ 以下に配置されています）

開発者向けメモ
---------------
- コードはテストしやすいように副作用を最小限にしており、多くの関数は純粋関数（副作用なし）になっています。
- OpenAI API 呼び出し部はリトライ・フォールバック設計。単体テスト時は _call_openai_api をモックしてください（例: unittest.mock.patch）。
- データ鮮度チェックは get_last_price_date（kabusy.data.pipeline）を参照します。DuckDB の prices_daily が最新であることを確かめてください。

ライセンス／バージョン
---------------------
- __version__ は kabusys.__version__（現在 0.1.0）。
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

問い合わせ
---------
不明点や改善提案はリポジトリの Issue または担当者へ連絡してください。

以上。