KabuSys — 日本株自動売買システム
=================================

本リポジトリは日本株向けの自動売買フレームワーク（試作）です。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（本番/ペーパートレード）、監視・アラート、LLM を使ったニュース NLP などのコンポーネントで構成されています。

主な特徴
--------
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出）
- リスク制御（ドローダウン監視、ポジション上限、リスクログ）
- ExecutionEngine（本番・ペーパートレード分離）
- 監視サブシステム（System / Trade / Risk モニタ、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（OpenAI を使ったニュースセンチメント、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 各種ツール（Paper Trading 検証レポート生成）

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（typing の union 表記などを利用）
- OS: Linux / macOS / Windows（ただし一部ユーティリティは POSIX を想定）

1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例: git clone ... && cd repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例: pip install -r requirements.txt
   - 必須ライブラリ（主要）: duckdb, psutil, openai, PyYAML（設定検証用）など
   - requirements.txt がない場合は用途に応じて個別インストールしてください。

4. .env 作成（環境変数設定）
   - インタラクティブウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成・更新します（.env は絶対に Git にコミットしないでください）
   - 手動で環境変数を設定する場合は .env を作成するか OS 環境変数に設定してください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります（exit 1）。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI モジュール使用時に必要）
- LOG_LEVEL, LOG_DIR など

使い方（主要スクリプト）
------------------------

実行エンジン（ExecutionEngine）
- 概要: 発注処理を行うエンジン。本番/ペーパートレードを切替可能。
- 起動:
  - python -m kabusys.run_execution
  - 起動時に Settings に従って SQLite 接続（paper_trading の場合は専用 DB）と DuckDB を開き、ExecutionEngine をスレッドで実行します。
- 停止:
  - data/stop_requested.flag を作成すると起動中の run_execution は検知して安全停止します。
  - kill.flag（Settings.kill_flag_path）を監視して ExecutionEngine に停止指示を出す仕組み（KillSwitch）があります。
- PID: data/execution.pid に PID を出力する運用が想定されています。

監視プロセス（Monitoring）
- 概要: System / Trade / Risk を定期ポーリングしてログ・アラート・KillSwitch を管理。
- 起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視用の SQLite は Settings.sqlite_path（monitoring は環境に依らず本番 sqlite_path を使用）を参照します。
- 停止:
  - run_monitoring は data/stop_requested.flag を検知して終了します。

設定ウィザード / 検証
- .env を対話的に作成:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
  - --strict オプションで警告を FAIL 扱いにできます

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数も使用可能。

AI（OpenAI）機能
- ニュース NLP（銘柄別センチメント）:
  - kabusys.ai.score_news を呼び出すか、アプリ内から利用
  - OPENAI_API_KEY が必要
  - 処理は raw_news / news_symbols テーブルから記事を集約し LLM に送信して結果を ai_scores に書き込みます
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出し、market_regime テーブルに書き込みます
  - 同様に OPENAI_API_KEY が必要

ログとプロセス制御
- ログ設定:
  - kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力
- プロセス優先度:
  - run_* スクリプトは set_process_priority("high") を最初に呼びます（psutil を使用）

ディレクトリ構成（src/kabusys 配下の主なファイル）
------------------------------------------------
- __init__.py
- config.py               — 環境変数 / Settings
- config_setup.py         — .env 対話ウィザード
- validate_config.py      — 起動前検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

- execution/               — 発注関連（Engine, OrderManager, BrokerFactory など）
- monitoring/
  - monitoring_db.py       — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （アラート送信ロジック、LINE 等）
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（注）上記は主要ファイルの要約です。細かいモジュールはツリーを参照してください。

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では環境変数・設定を慎重に管理してください。validate_config は live 時に特別な警告を出します。
- .env は絶対に Git にコミットしないでください。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用 SQLite を使用して本番 DB と分離します（設定: PAPER_TRADING_SQLITE_PATH）。
- Kill Switch（data/kill.flag）を使えば監視側から Execution を安全に停止できます。起動時に KILL_FLAG_CLEAR_ON_START 設定に注意してください（本番では 0 推奨）。
- OpenAI を利用する機能は API 呼び出し失敗時にフォールバック（多くは無害なデフォルト）する実装がされていますが、API キーの管理とコストに注意してください。

開発・テスト
------------
- 自動 .env ロード: config.py はプロジェクトルートを探索し .env / .env.local を自動的に読み込みます（テスト中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- unit テストを書く際は、OpenAI 呼び出しや psutil など外部依存をモックすると良いです（例: news_nlp._call_openai_api を patch）。

よく使うコマンド例
-----------------
- ウィザードで初期設定:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はコードベースの主な使い方・構成をまとめたものです。各モジュールの詳細実装はソースコード内の docstring / コメントを参照してください。追加でドキュメント化したい箇所やサンプル設定ファイル（.env.example や config/*.yaml）等があればお知らせください。