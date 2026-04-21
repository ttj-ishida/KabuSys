KabuSys — 日本株自動売買システム
================================

本ドキュメントは、このリポジトリ（src/kabusys）に含まれる主要コンポーネントと
セットアップ・起動手順をまとめた README です。開発者・運用者向けに最低限必要な
情報を日本語で記載しています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買（Execution）とそれを支える監視（Monitoring）・
研究（Research）・ポートフォリオ構築（Portfolio）機能を提供するコードベースです。
主な設計方針は以下の通りです。

- 実行ロジック（発注）と監視ロジックを分離（ExecutionEngine / MonitoringEngine）。
- 本番 DB とペーパートレード DB を明確に分離（KABUSYS_ENV=paper_trading）。
- DuckDB を分析用、SQLite を監視・発注ログ用に利用。
- OpenAI を用いたニュース NLP / レジーム判定機能を備える（外部 API はオプション）。
- .env による環境変数管理、対話式ウィザードと検証ツールを提供。

主な機能一覧
------------
- Execution
  - ExecutionEngine を起動して注文発行／注文管理を実行（kabuステーション連携）。
  - ペーパートレード用の MockBrokerClient をサポート（KABUSYS_ENV=paper_trading）。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた常時監視。
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）。
  - 監視ログの永続化（SQLite）とダッシュボード更新。
- Portfolio（純粋関数群）
  - 銘柄選定、重み計算、リスク調整、建玉サイズ計算。
- Research
  - DuckDB 上でファクター計算（モメンタム、ボラティリティ、バリュー）。
  - 将来リターン計算、IC（Information Coefficient）等の統計解析ユーティリティ。
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント化し ai_scores テーブルへ書き込み。
  - regime_detector: マクロニュース＋ETF MA を合成して market_regime を決定。
- CLI ツール
  - config_setup: .env の対話式ウィザード生成。
  - validate_config: .env / config/*.yaml の起動前チェック。
  - tools/paper_verification_report: ペーパートレード結果の検証レポート生成。

セットアップ手順
----------------
前提:
- Python 3.9+ を想定（プロジェクトの pyproject.toml を参照してください）。
- 仮想環境推奨（venv / pipenv / poetry 等）。

1. リポジトリのクローン・仮想環境作成
   - git clone ... && cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージのインストール
   - requirements.txt / pyproject.toml に従って duckdb, psutil, openai, PyYAML 等をインストールしてください。
     例: pip install duckdb psutil openai PyYAML

3. .env の作成（推奨: 対話式ウィザード）
   - 対話式で作成: python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成
   - 重要: .env を Git にコミットしないこと

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプトが起動時に必要なテーブルを自動作成します（init_monitoring_db）。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading）

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ出力先ディレクトリ）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）

使い方（主要コマンド）
---------------------

- ExecutionEngine を起動（発注処理）
  - 本番／開発／ペーパーは KABUSYS_ENV で制御
  - 実行: python -m kabusys.run_execution
    - 起動時に process priority を "high" に設定し、PID ファイル (data/execution.pid) を使用します。
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH を利用します。
    - 停止は data/stop_requested.flag を作成するか、実行プロセスにシグナル送信（Ctrl-C）で。

- Monitoring を起動（監視ループ）
  - 実行: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で変更可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path（環境にかかわらず）を使用して監視テーブルに記録します。
  - 停止は data/stop_requested.flag を作成するか、Ctrl-C。

- .env の初期作成（対話式）
  - python -m kabusys.config_setup

- 設定の事前チェック
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム的呼び出し）
  - ニュース NLP のスコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn は duckdb.connect() の接続オブジェクト
    - OPENAI_API_KEY が必要
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ・PID・フラグファイル
-----------------------
- ログ:
  - デフォルトは logs/ に日次ローテーションで出力（logs/<app_name>.log）。
  - LOG_DIR 環境変数で変更可能。
- PID ファイル:
  - data/execution.pid（ExecutionEngine が使用）
- 停止・kill フラグ:
  - data/stop_requested.flag: run_* スクリプト終了指示に使用（存在確認して安全に停止）
  - data/kill.flag: KillSwitch が作成し ExecutionEngine に停止命令を与える（致命的条件）

注意事項
--------
- .env は決してリポジトリにコミットしないでください。
- 実行中のプロセス優先度変更は OS の権限で失敗することがあります（ログに警告）。
- OpenAI を使う機能は API 呼び出しに失敗した場合、フェイルセーフで進行する実装ですが、
  API キーやコール制限・料金に注意してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env を読み込む処理を無効化できます（テスト用）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
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
    - (その他: trade_monitor.py, alert_manager.py 等が想定される)
  - execution/                  — 発注周り（BrokerFactory, Engine, OrderManager 等）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（プロジェクトルート）
- .env, .env.local                 — 環境変数（.gitignore 推奨）
- config/
  - system_config.yaml, data_config.yaml, ... （テンプレート/生成対象）
- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid, kill.flag, stop_requested.flag
- logs/
  - execution.log, monitoring.log, ... （ログ出力先）

追加情報（開発者向け）
-------------------
- 設定ロード:
  - config.py はプロジェクトルート（.git / pyproject.toml）を基に .env/.env.local を自動ロードします。
  - OS 環境変数が優先され、.env.local は既存環境を上書きする実装です。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等的にテーブルを作成し、必要に応じて簡易マイグレーション（列追加）を行います。
- テスト:
  - AI 呼び出し部分はテスト中にモック可能なように関数分離しています（例: _call_openai_api を patch）。

最後に
------
まずは .env を作成（python -m kabusys.config_setup）し、python -m kabusys.validate_config で
チェックしてください。ペーパートレードで動作確認する場合は KABUSYS_ENV=paper_trading
を設定し、python -m kabusys.run_execution（および別プロセスで python -m kabusys.run_monitoring）
を起動して挙動を確認してください。

必要であれば、README に追記してほしいトピック（依存パッケージの具体的なバージョン一覧、
運用用 systemd / supervisor の設定例、テーブル定義の詳細など）を教えてください。