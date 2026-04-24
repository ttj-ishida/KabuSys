KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を支援するためのモジュール群をまとめた Python コードベースです。  
主な目的は以下のとおりです。

- 戦略（ファクター計算・特徴量解析）を DuckDB 上で実行する研究 / リサーチ機能
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群
- ExecutionEngine（発注実行）と Monitoring（稼働監視・Kill Switch）
- Paper Trading 用の分離された DB / モックブローカー
- ニュース NLP / LLM を使ったスコアリング・レジーム判定
- 各種運用ユーティリティ（設定ウィザード、設定検証、検証レポート等）

特徴一覧
--------
- modular 化されたポートフォリオ構築ロジック（選定 / 重み付け / リスク調整 / 株数算出）
- DuckDB を利用したデータ処理（prices_daily / raw_financials 等）
- Execution と Monitoring が分離（監視は別プロセスで polling）
- Paper trading（KABUSYS_ENV=paper_trading）時はモックブローカーと専用 SQLite を利用して本番 DB と完全分離
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定（API キー必須）
- ログはコンソール + 日次ローテートファイル出力（logs/<app>.log）
- 設定ウィザード（.env 自動生成）と設定検証 CLI を提供

前提・依存
-----------
主に以下のパッケージが必要です（プロジェクトに依存ファイルは含まれていません）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合に推奨）

pip でインストールする場合の例:
    pip install duckdb psutil openai pyyaml

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化し依存パッケージをインストール
3. .env を作成する（2通りの方法あり）
   - 対話式ウィザード:
       python -m kabusys.config_setup
   - 手動で .env ファイルを作成（ルートに配置）
     例（必須は JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）:
       JQUANTS_REFRESH_TOKEN=your_jquants_token
       KABU_API_PASSWORD=your_kabu_password
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO

注意:
- 自動で .env をロードする仕組みが有効（デフォルト）。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- .env は機密情報を含むため Git にコミットしないでください。

設定検証
--------
起動前に設定をチェックできます:
    python -m kabusys.validate_config
警告を FAIL として扱いたい場合:
    python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う場合は必須（ai.score_news / regime）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（起動・主要コマンド）
-------------------------

- 環境設定ウィザード（.env 作成・更新）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Monitoring プロセス起動（監視ループ）
    python -m kabusys.run_monitoring
  補足:
    - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
    - 停止フラグファイル: data/stop_requested.flag（作成されるとループを抜けます）
    - Monitoring は本番 sqlite_path を常に参照（環境に関わらず）

- Execution（発注エンジン）起動
    python -m kabusys.run_execution
  補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、data/paper_trading.db に発注ログ等を記録（本番 DB と完全分離）
    - 停止フラグ: data/stop_requested.flag を作成するとエンジン停止を要求
    - PID ファイル: data/execution.pid が使われます

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  補足:
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - ニューススコア: kabusys.ai.news_nlp.score_news（内部で DuckDB の raw_news / news_symbols を参照）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテート）に出力されます。
- ログディレクトリは環境変数 LOG_DIR または引数で変更可能（utils.logging_setup.setup_logging を利用）。

データベース（デフォルトパス）
-----------------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db

監視（Monitoring）について（簡易）
--------------------------------
- Monitoring は SystemMonitor、TradeMonitor、RiskMonitor を組み合わせた MonitoringEngine がポーリングします。
- KillSwitch: リスク条件（例: ドローダウン閾値超過）を満たした場合に data/kill.flag を書き込み、Execution を停止させます。
- MonitoringDB（monitoring_db.py）: system_status / trade_logs / positions / risk_logs / dashboard のテーブルを管理します（init_monitoring_db がスキーマ作成／マイグレーションを行います）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

packages / サブモジュール
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
  - regime_detector.py     — レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — 監視用 SQLite の永続化層
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （発注ログ監視）※実装参照
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch 制御（flag ファイル）
  - monitoring_engine.py   — モニタの束ねとループ
  - alert_manager.py       — 通知管理（LINE 等、参照実装）
- execution/
  - execution_engine.py    — 発注エンジン本体
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py      — ブローカークライアント生成（Mock を含む）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — ファクター計算（momentum, volatility, value）
  - feature_exploration.py — IC / 将来リターン / 統計
- tools/
  - paper_verification_report.py — Paper Trading レポート生成
- utils/
  - logging_setup.py       — 共通ロギング設定
  - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ

注意事項・運用メモ
-----------------
- 本番運用時は KABUSYS_ENV=live に設定し、LINE の通知設定や Kill Switch 動作を十分に確認してください。
- paper_trading モードは本番データベースと完全に分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI API を利用するコードは外部課金が発生します。API キー管理・利用制限に注意してください。
- .env の自動ロード順は OS 環境 > .env.local > .env。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- logs/ と data/ ディレクトリは自動作成されますが、パーミッション等に注意してください。

貢献・拡張
----------
- 各モジュールは比較的独立しているため、新しい戦略やブローカー実装、通知チャネルを追加しやすい設計です。
- duckdb のスキーマ（prices_daily 等）に合わせて research / ai モジュールを拡張してください。

ライセンス
---------
（この README にはライセンス情報が含まれていません。実際のプロジェクトでは LICENSE を追加してください。）

お問い合わせ
------------
実装上の設計意図や使い方、追加したい機能があれば README を出発点にドキュメントを拡張してください。README の記載内容はソースコードのコメント・ドキュメントストリングに基づいています。