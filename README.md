README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための軽量なフレームワークです。本リポジトリには以下の主要機能が含まれます。

- 注文実行エンジン（ExecutionEngine）: ブローカー接続・注文管理・リスク管理を行う
- 監視（Monitoring）: システム状態、注文ログ、リスク指標のポーリング監視とアラート / Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定、重み付け、ポジションサイズ計算、セクター制約など
- リサーチモジュール: ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量探索
- AI 支援機能: ニュースの NLP によるセンチメントスコア（OpenAI を利用）・市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード、設定検証、ツール類（ペーパー検証レポート等）

主な設計方針:
- 設定は .env または環境変数で管理
- DuckDB を分析用、SQLite を監視・発注ログ用に利用（デフォルトは data/* 下）
- 本番（live）/ ペーパートレード（paper_trading）/ 開発（development）を環境で切替可能
- AI 呼び出しは環境変数 OPENAI_API_KEY を前提。失敗時はフェイルセーフで継続する設計

機能一覧
--------
- 実行:
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - Paper trading 時は MockBroker を使い、本番 DB と分離して data/paper_trading.db を使用
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング）
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - monitoring DB スキーマ作成 / 永続化（SQLite）
- ポートフォリオ:
  - 候補選定、等金額/スコア重み、リスクベースのポジションサイズ、セクターキャップ、レジーム乗数
- リサーチ:
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - Forward returns、IC（Information Coefficient）計算、統計サマリー
- AI:
  - ニュースの銘柄別センチメント集約と OpenAI (gpt-4o-mini) 呼び出し（結果を ai_scores に保存）
  - マクロニュース + ETF ma200 乖離から市場レジーム判定を行い market_regime テーブルへ保存
- ツール:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config (--strict オプション)
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

前提条件
--------
- Python 3.10 以上（| 型ヒントなどを使用しているため）
- 必要なパッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証を行う場合に必要）
- SQLite（Python 標準ライブラリに含まれます）
- ネットワーク接続（外部 API を使う機能を利用する場合）

インストール（例）
-----------------
1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

環境設定 (.env)
---------------
プロジェクトルートに .env を置いて環境変数を管理できます。用意されている対話式ウィザードで初期作成できます:

- python -m kabusys.config_setup
  → 対話式で .env を作成・更新します（.env は絶対に Git にコミットしないでください）

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading のときに使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — run_monitoring.py で参照

設定検証
--------
起動前に設定の妥当性をチェックできます:

- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い（exit code 1）

使用方法
--------
1) 監視（Monitoring）の起動
- python -m kabusys.run_monitoring
  - デフォルトでは MONITOR_POLL_INTERVAL=60 秒のポーリングループを実行します
  - stop フラグファイルを置くことでループを止められます:
    - data/stop_requested.flag を作成すると監視ループが終了します

2) 注文実行エンジン（ExecutionEngine）の起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - 実行中は pid ファイル（data/execution.pid）を書きます

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 簡易的な Pass/Fail 判定と指標（稼働率・注文成功率・レイテンシ等）を出力します

4) AI 機能（ニューススコアリング / レジーム判定）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定してください
- ニュースのスコア算出: kabusys.ai.score_news（プログラムから利用）
- レジーム判定: kabusys.ai.regime_detector.score_regime（プログラムから利用）
- これらは DuckDB 接続と target_date を引数に取る純粋関数として実装されています

停止制御 / Kill Switch
--------------------
- Kill Switch は監視モジュールが条件（ドローダウン超過・ポジション上限超過など）を満たした場合に data/kill.flag を作成します。ExecutionEngine はこのファイルを検知して安全に停止します。
- Kill Switch を手動でクリアするには data/kill.flag を削除します。Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に自動クリアされます（本番では 0 を推奨）。

ログ / DB
---------
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリ）
  - setup_logging を通して root ロガーを統一的に設定します
- DB:
  - DuckDB: 分析用（default: data/kabusys.duckdb）
  - SQLite: 監視・発注履歴（default: data/monitoring.db）
  - ペーパートレード用 SQLite は PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）

ディレクトリ構成（主なファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py
  - 設定読み込み・Settings クラス（.env 自動ロード・検証）
- config_setup.py
  - .env 作成ウィザード（対話式）
- validate_config.py
  - 起動前の設定検証 CLI
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を使用）
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite テーブルの初期化・CRUD ヘルパ
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 発注ログ監視（滞留注文・約定異常等）※（ソース内に実装あり）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py — kill.flag ロジック
  - alert_manager.py — （アラート送信管理、実装参照）
- execution/
  - execution_engine.py — ExecutionEngine 本体（発注ループ等）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（リスクベース等）
  - risk_adjustment.py — セクター制約・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / summary
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント合成）
- tools/
  - paper_verification_report.py — ペーパー検証レポート生成ツール

補足 / 運用上の注意
-----------------
- .env は決してリポジトリにコミットしないでください（シークレット含む）
- 本番（KABUSYS_ENV=live）では Kill Switch、通知先（LINE 等）の設定を十分に確認してください
- OpenAI を用いる処理は API コストが発生します。バッチサイズやトークン上限に注意してください
- ロギング・DB パスが作成できない場合、ログはコンソールのみになったり書き込み失敗します（setup_logging は作成失敗を警告します）

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__version__ にて管理されています（現状: 0.1.0）
- ライセンス情報はリポジトリの LICENSE 等を参照してください（存在する場合）

問い合わせ
----------
- 実装の詳細や拡張（ブローカープラグイン追加、AI プロンプト調整、ポートフォリオロジック変更など）については各モジュールの docstring を参照してください。各モジュールは概ね単一責務で記述されているため、差し替えやテストが行いやすい設計になっています。

以上。必要があれば README にサンプル .env のテンプレートや具体的な運用例（systemd ユニット / Supervisor / Dockerfile など）を追記します。どの情報を追加したいか教えてください。