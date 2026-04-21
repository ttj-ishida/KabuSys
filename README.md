README
=====

以下はこのコードベース（KabuSys）の概要、セットアップ方法、使い方、ディレクトリ構成などのまとめです。日本株自動売買システムのコンポーネント群（監視、発注エンジン、ポートフォリオ構築、リサーチ、AI 補助機能など）を含みます。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買補助システムです。主な目的は以下です。

- シグナルに基づく銘柄選定・配分・株数算出（ポートフォリオ構築）
- 注文発行・約定管理・リスク管理を行う Execution エンジン
- システム稼働状況・注文ログの監視とアラート（Monitoring）
- DuckDB を用いたファクター計算やリサーチ機能
- OpenAI を用いたニュース NLP（センチメント）と市場レジーム判定
- ペーパートレード用の完全分離 DB による検証機能

設計上の特徴：
- 設定は .env または環境変数で管理（自動ロード機構あり）
- モジュールはライブラリとしても呼び出せる（純粋関数の多用）
- 監視/実行はプロセス優先度設定や PID / flag ファイルを利用して制御

機能一覧
---------
- config: 環境変数の抽象化（Settings クラス）、.env 自動読み込み
- config_setup: 対話式ウィザードで .env を作成・更新
- validate_config: 起動前の設定検証 CLI（--strict オプションあり）
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading で MockBroker）
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- monitoring:
  - monitoring_db: SQLite による永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager 等
- portfolio:
  - portfolio_builder, position_sizing, risk_adjustment（候補選定・重み・株数算出・セクター制限・レジーム乗数）
- research:
  - factor_research (momentum/value/volatility)、feature_exploration（forward returns、IC、統計サマリー）
- ai:
  - news_nlp: ニュース記事を LLM (gpt-4o-mini) でセンチメントして ai_scores へ書き込み
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定・書き込み
- tools:
  - paper_verification_report: ペーパートレード DB（デフォルト data/paper_trading.db）から検証レポートを生成

前提条件（主な依存）
-------------------
主に以下が必要です（実行環境により追加ライブラリあり）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- （任意）PyYAML — validate_config が config/*.yaml を検証する場合に必要

インストール（例）
-----------------
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai

（プロジェクトに requirements.txt があればそちらを使ってください）

環境変数・.env の準備
---------------------
このプロジェクトは .env / 環境変数を通じて設定を管理します。自動ロードの挙動：

- プロジェクトルート（.git または pyproject.toml が基準）を検出し、.env を読み込みます。
- OS 環境変数を優先します。.env.local は .env を上書き可能。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — monitoring 用（monitoring は常に本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — paper_trading 時の専用 DB
- PAPER_FILL_MODE（paper_trading の MockBroker fill 動作: instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI 機能を利用する際に必要）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動で消すか。0/1、デフォルト 0）

設定ウィザード / 検証
--------------------
- .env を対話式に作る: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config  （--strict で警告も FAIL 扱い）

セットアップ手順（基本）
---------------------
1. .env を作成（config_setup を利用するか手動で作成）
2. data ディレクトリや logs ディレクトリは起動時に自動作成されますが、必要なら手動で作る
3. DuckDB / SQLite のファイルパスを確認（設定またはデフォルト）
4. 必要に応じて PAPER_TRADING_SQLITE_PATH を設定してペーパートレード用 DB を準備

使い方（実行例）
----------------

- Execution エンジン起動（本番/ペーパー判定は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution

  挙動ポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - PID ファイルは data/execution.pid（Settings.pid_file_path）に書かれます。
  - 起動時にプロセス優先度を "high" に設定する仕組みがあります（psutil が必要）。

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring

  挙動ポイント:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使います
  - 停止フラグ: data/stop_requested.flag。検知するとループを抜けて終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うか --db で明示可能

- AI 系機能（プログラムから）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか OPENAI_API_KEY を設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  注意:
  - OpenAI API キー未設定だと ValueError を投げます（AI 機能は必須ではありません）。
  - AI 呼び出しはリトライやフェイルセーフ処理を備えていますが、API 利用制限や課金に注意してください。

ログ / ローテーション / プロセス管理
-----------------------------------
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（TimedRotatingFileHandler、30 日保持）。
- setup_logging() により stdout にもログを出力（デフォルトは stdout）。
- プロセス優先度・CPU affinity の設定は utils.process_priority を通して行います（psutil が必要）。
- Kill Switch:
  - RiskMonitor 等の結果により KillSwitch が data/kill.flag を作成すると、Execution 側で検出して停止する仕組みがあります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では推奨しません）。

開発者向けメモ
--------------
- 多くのポートフォリオ / リスク / ポジション計算関数は「純粋関数」として実装されており、ユニットテストしやすい設計です（DB 参照なしで計算）。
- monitoring_db モジュールは SQLite のスキーマ管理（初期化・簡易マイグレーション）を行います。
- DuckDB は分析用に利用され、prices_daily / raw_financials / raw_news 等のテーブルを参照する設計です。
- validate_config は PyYAML が未インストールでも動作しますが、config/*.yaml の内容検証は PyYAML が必要です。

ディレクトリ構成（主要ファイル）
----------------------------
以下はコードベースの主要なファイル・ディレクトリ構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境設定読み取り / Settings クラス
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — Execution 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py  (存在する場合)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/                  — Execution 系の実装群（BrokerFactory, Engine, OrderManager 等）

（注）上は抜粋です。細かいモジュールはソースツリーを参照してください。

よくある運用フロー（例）
-----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. 必要に応じてデータベース（DuckDB/SQLite）を準備
4. 監視プロセスを起動（推奨: 常時稼働）
   - python -m kabusys.run_monitoring
5. Execution を起動（トレード実行）
   - python -m kabusys.run_execution
6. 運用中に重大リスク検出 → monitoring が data/kill.flag を書き込み → Execution は停止

補足（重要事項）
----------------
- 本リポジトリは実際の発注 API を扱うため、KABU_API_PASSWORD 等の機密情報は .env を Git にコミットしないでください。
- 本番運用時は KABUSYS_ENV=live の設定に十分注意してください。validate_config は live に対する追加警告を出します。
- AI 機能（news_nlp / regime_detector）は API キーと利用料が必要です。スコアリングは外部 API 呼び出しのためレート制限や課金に注意してください。

問い合わせ / 貢献
-----------------
- コードやドキュメントの改善提案は Pull Request を送ってください。
- 実運用の設定例や運用手順（systemd / supervisor スクリプトなど）は別途ドキュメント化すると便利です。

以上。README の内容について補足や特定モジュール（例: position_sizing のパラメータ説明、news_nlp の実行サンプル等）を追記したい場合は、用途に応じて具体的に指示してください。