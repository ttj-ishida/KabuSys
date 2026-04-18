KabuSys — 日本株自動売買システム
================================

このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買・リサーチ基盤の一部実装です。
主に実行エンジン、監視、ポートフォリオ構築、ファクター計算、AI（ニュース）スコアリングなどのモジュールを含みます。

本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
- 目的: 日本株の自動売買システムのコア機能（注文実行、監視、ポートフォリオ構築、ファクター計算、ニュースNLP等）をライブラリ化・実装する。
- 設計方針:
  - 監視・実行ロジックは DB（SQLite / DuckDB）へ記録して永続化。
  - Paper Trading（模擬発注）と Live（本番発注）を環境変数で切り替え可能。
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価やレジーム判定機能を提供（APIキー必須）。
  - CLI ツールで .env ウィザードや設定検証、ペーパートレード・検証レポート生成をサポート。

主な機能一覧
-------------
- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、本番 DB と分離された data/paper_trading.db を使う。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine と起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視結果は SQLite（デフォルト data/monitoring.db）に永続化。
    - Kill Switch（データベース上のリスク／ドローダウン等に応じて data/kill.flag を書く）をサポート。
- ポートフォリオ構築
  - 銘柄選定（select_candidates）、重み付け（等分／スコア加重）、ポジションサイズ計算（calc_position_sizes）、セクター制約適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）等。
- リサーチ / ファクター
  - DuckDB 接続を受け取りファクター計算（momentum, volatility, value）や将来リターン、IC 計算、統計サマリ等を実行。
- AI（ニュース）関連
  - raw_news を OpenAI に送り銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む（kabusys.ai.news_nlp）。
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成する kabusys.ai.regime_detector）。
  - 上位レイヤは OpenAI API のエラーに対してリトライやフェイルセーフを備える。
- ツール
  - .env 対話ウィザード（kabusys.config_setup）: .env の初期作成・更新を支援。
  - 設定検証 CLI（kabusys.validate_config）: 必須環境変数や config/*.yaml の確認。
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）: 稼働率・成功率・レイテンシ等を集計して PASS/FAIL を判定。

セットアップ手順
----------------
前提:
- Python 3.10 以上を推奨（型注釈や union 型表現を使用しているため）。
- SQLite は標準ライブラリに含まれます。

推奨パッケージ（例: pip install）:
- duckdb
- psutil
- openai
- PyYAML（config ファイルのパース検証を行う場合に必要）

例:
- 仮想環境作成・有効化（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 依存インストール（requirements.txt がない場合は個別インストール）
  - pip install duckdb psutil openai PyYAML

初期設定:
1. プロジェクトルート（.git または pyproject.toml がある場所）に移動。
2. 環境変数設定:
   - 対話ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（一部、デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 時）
     - OPENAI_API_KEY: OpenAI API を使う機能は必須
     - LOG_LEVEL, LOG_DIR 等
   - .env 自動ロード:
     - config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
3. 設定検証:
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告もエラー扱いになる

データディレクトリ作成:
- デフォルトでは data/ と logs/ にファイルを書きます。アクセス権やディスク容量に注意してください。
  - mkdir -p data logs

使い方（主要コマンド）
--------------------
起動スクリプト（モジュール実行）:
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）が使われ、MockBroker を利用します。
- 監視（SystemMonitor のポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用する実装です

設定関連:
- .env ウィザード（対話形式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

ツール:
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI 機能:
- OpenAI を使う機能（news_nlp.score_news、regime_detector.score_regime）を呼ぶ際は OPENAI_API_KEY を設定してください。これらはライブラリ関数として呼び出す形です（CLI スクリプトは同梱されていません）。

停止 / 停止フラグ:
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag や data/kill.flag を検知して動作を調整します。
  - stop_requested.flag: 実行スクリプトの即時停止シグナル（スクリプト起動時にこのフラグがあると起動を抑制する場合がある）。
  - kill.flag: Monitoring 側から ExecutionEngine 停止命令を伝えるために書かれるファイル（Kill Switch）。
- Execution 起動時に PID ファイル（デフォルト data/execution.pid）を書き、プロセスの存在を監視する実装があります。

ロギング:
- kabusys.utils.logging_setup.setup_logging を使用して統一的にログ出力を行います。
- デフォルト: logs/<app_name>.log に日次ローテーションで保存（30日保持）。コンソール出力は stdout。
- ログレベルは LOG_LEVEL 環境変数で指定可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）

ディレクトリ構成
----------------
以下は src/kabusys 配下の主要ファイルとディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み・Settings クラス
  - config_setup.py               — .env 対話ウィザード CLI
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースの OpenAI スコアリング
    - regime_detector.py           — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py            — SQLite テーブル定義 / 永続化層
    - system_monitor.py           — システム・データ鮮度監視
    - trade_monitor.py            — 注文関連監視（存在）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 操作
    - monitoring_engine.py        — Monitor を束ねるエンジン
    - alert_manager.py            — （アラート送信管理）
  - execution/
    - execution_engine.py         — 実行エンジン（Session 管理）
    - order_manager.py            — 注文管理
    - order_repository.py         — 注文 DB 操作
    - reconciler.py               — 注文状態の再整合化
    - broker_factory.py           — BrokerClient の生成
    - risk_manager.py             — 注文件数/資金制限等のリスク管理
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 株数算出・キャップ
    - risk_adjustment.py          — セクター制約・レジーム乗数
  - research/
    - factor_research.py          — Momentum/Value/Volatility 等の計算
    - feature_exploration.py      — 将来リターン・IC・統計
  - utils/
    - logging_setup.py            — ロギング設定ユーティリティ
    - process_priority.py         — プロセス優先度・CPU affinity
    - __init__.py
  - data/ （実行時に作成される想定）
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper_trading 用)
    - kabusys.duckdb (DuckDB)

注意点 / 運用メモ
----------------
- 環境変数は .env / .env.local から自動ロードされますが、OS 環境変数が優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時（KABUSYS_ENV=live）は LINE 通知や kill_flag の挙動等、慎重に設定を確認してください（validate_config にてライブガードチェックあり）。
- OpenAI の呼び出しはコストやレート制限に注意してください。news_nlp と regime_detector はリトライとフェイルセーフを備えていますが、API 使用量は監視してください。
- データ鮮度チェックや PID チェック等、ローカル環境では権限不足や依存ライブラリの未導入で一部処理がスキップされることがあります（ログに警告が出ます）。

貢献 / 拡張案
---------------
- Strategy / Execution ロジックの詳細化（ブローカ実装、order state machine の拡張）
- 銘柄別 lot_size 対応、手数料・スリッページモデルの導入
- 単体テストと CI の整備（モックや依存切り離しを活用）
- observability（Prometheus / Grafana）や外部通知チャネルの追加

ライセンス
----------
- ソースコード内に明示的なライセンスファイルが無い場合はリポジトリオーナーに確認してください。

補足（よく使うコマンドまとめ）
------------------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

何か補足してほしい項目（例: 依存関係の詳細なバージョン、実行時のログ例、サンプル .env テンプレート等）があれば教えてください。README に追記します。