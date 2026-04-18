README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の Python パッケージです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を担うコンポーネント
- 監視コンポーネント（Monitoring）: システム稼働状況・注文挙動・リスクを定期監視し、必要に応じて Kill Switch を発動
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算・セクター制約などの純粋関数群
- リサーチ機能: DuckDB を用いたファクター計算・特徴量探索
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュースNLP や市場レジーム判定
- 運用ツール: .env ウィザード、設定検証、ペーパートレード検証レポート生成 等

主な特徴
--------
- 環境変数・.env ベースの軽量設定管理（config_setup による対話式生成）
- 実行環境（development / paper_trading / live）を切り替えてペーパートレードと本番の分離をサポート
- DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- OpenAI API を用いたニュースセンチメント評価（失敗時はフェイルセーフで継続）
- psutil を用いたプロセス優先度設定 / リソース監視
- 監視ループはファイルフラグ（data/stop_requested.flag / data/kill.flag）で安全に終了や停止指示が可能

セットアップ
-----------
1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 推奨: pip install duckdb psutil openai PyYAML
   - ※sqlite3 は標準ライブラリに含まれます。
   - 必要に応じて開発用依存を追加してください。

3. 環境変数（.env）を作成
   - 対話的に作る: python -m kabusys.config_setup
   - 手動で作る場合はリポジトリルートに .env を配置
   - .env に記載する主な鍵（簡易）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
     - OPENAI_API_KEY — AI 機能利用時に必要
     - LOG_LEVEL — デフォルト INFO
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用（任意）
     - PAPER_FILL_MODE — paper_trading の MockBroker の振る舞い（instant|partial|never|reject、デフォルト "instant"）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0/1、デフォルト 0）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict

基本的な使い方
--------------
各コンポーネントはモジュール実行で起動できます（プロジェクトルートで実行）。

- 環境設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ExecutionEngine を起動（注文処理）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 停止は data/stop_requested.flag を作成することで行う（実行中は flag を検知して安全終了）

- Monitoring のポーリングループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - Monitoring は環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを保管
  - 停止はプロジェクトルートの data/stop_requested.flag を作る

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

- AI 機能（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数か OPENAI_API_KEY 環境変数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に API キーが必要

運用上の注意
-------------
- ログ: デフォルトで logs/ ディレクトリに日次ローテートログを出力します（kabusy.utils.logging_setup.setup_logging）。
- PID / flag:
  - data/execution.pid — ExecutionEngine の PID（設定で変更可能）
  - data/stop_requested.flag — 手動停止指示（両プロセスで参照）
  - data/kill.flag — KillSwitch が書き込む停止フラグ（本番で ExecutionEngine を停止するための自動フラグ）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）
- Monitoring は監視用 DB（SQLite）に対して永続化を行います。monitoring_db.init_monitoring_db は必要なテーブルを冪等に作成します。
- OpenAI を利用する機能はネットワークエラーやレート制限を考慮してリトライ／フェイルセーフを実装していますが、API キーの未設定は ValueError を送出する点に注意してください。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution モード（development|paper_trading|live）デフォルト: development
- DUCKDB_PATH — duckdb ファイルの保存先（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト 0）

ディレクトリ構成（抜粋）
----------------------
リポジトリの主要ファイル・モジュール構成の例:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py        — （trade_monitor の実装は省略したが monitoring 系の一部）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py       — （アラート送信の責務）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - (その他: data/, config/, logs/ 等はランタイムに作成されます)

開発者向けメモ
--------------
- DuckDB を利用したリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルを参照します。データ投入は別パイプラインにより行ってください。
- 各モジュールはできるだけ副作用を抑えた純粋関数群（research / portfolio）と、DB 書き込みなどの副作用を持つ層（monitoring_db / ExecutionEngine）に分離されています。
- テスト時は環境変数自動ロード（config.py の自動読み込み）を無効化できます:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

トラブルシューティング
---------------------
- .env を作成しても設定エラーが出る:
  - python -m kabusys.validate_config を実行して何が不足しているか確認してください。
- ログファイルが作れない（permissions 等）:
  - logs/ ディレクトリの作成権限を確認してください。作成失敗時はコンソール出力のみになります（警告が出ます）。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY が正しいか、ネットワーク・レート制限を確認してください。API エラーは一部リトライ後にゼロフォールバックする実装です。

ライセンス・バージョン
----------------------
パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

（ライセンス表記等はリポジトリのトップレベルに別途配置してください）

補足
----
この README はリポジトリ内に含まれる主要スクリプトとユーティリティの要点をまとめたもので、詳細なアーキテクチャや設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途存在する想定です。必要であれば各モジュールの API 仕様や具体的な実運用手順（systemd ユニット例、コンテナ化手順など）を追加で記述できます。