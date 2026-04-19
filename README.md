KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究／モニタリング用ユーティリティ群です。本リポジトリには以下の機能が含まれます：

- 実行エンジンの起動スクリプト（ExecutionEngine）
- システム監視・アラート用のモニタ（Monitoring）
- ペーパートレード用の分離 DB／モックブローカー対応
- ポートフォリオ構築（候補選定、重み算出、単元丸め）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュース NLP（OpenAI）連携（センチメント / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- レポート生成ツール（ペーパートレード検証レポート）

主要な設計方針
- 環境依存値は .env / 環境変数で管理（自動ロード機能あり）
- Paper trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- ログはコンソール + 日次ローテートファイル（logs/）で統一
- AI 系は OpenAI API（gpt-4o-mini 等）と疎結合に実装。APIキーが必要

主な機能一覧
- run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を利用し data/paper_trading.db に記録
- run_monitoring.py: SystemMonitor をポーリングして system_status / trade_logs / risk_logs / dashboard を更新し、Kill Switch を管理
- config_setup.py: .env を対話的に作成・更新するウィザード
- validate_config.py: .env と config/*.yaml の存在・基本整合性を検証する CLI
- tools/paper_verification_report.py: ペーパートレードの実績を集計して PASS/FAIL レポートを出力
- portfolio/*: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム補正
- research/*: DuckDB を使ったファクター計算・将来リターン・IC・統計サマリ
- ai/*: ニュースの NLP スコアリング（ai_scores に保存）、市場レジーム判定（market_regime への書き込み）
- monitoring/*: MonitoringDB（SQLite）への永続化、各種モニタ（System/Trade/Risk）、KillSwitch、アラート起動ロジック
- utils/*: ログ設定・プロセス優先度・CPU affinity ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10+（型ヒントの union 表記などを使用）
- 必要なパッケージ（最小例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（validate_config の YAML 検証で任意）
  - sqlite3（標準ライブラリ）
- 以降はプロジェクトルート（pyproject.toml や .git があるディレクトリ）を想定

1) 仮想環境を作成して依存をインストール
- 例:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

2) .env の準備
- 対話式ウィザードで作成:
  - python -m kabusys.config_setup
- もしくは .env ファイルを手動作成（主なキーは下記参照）

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution 環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（1 で有効・本番では 0 推奨）

注意: リポジトリは自動で .env と .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

使い方（起動・ユーティリティ）
--------------------------------

設定検証
- 設定検証を行う:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

設定ウィザード（.env 作成）
- python -m kabusys.config_setup

ExecutionEngine 起動
- 本番／ローカル実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に結果を保存
- 実行はデーモンスレッドで動き stop_requested.flag を検知すると停止します（data/stop_requested.flag を使うフロー）

Monitoring 起動
- SystemMonitor のポーリングループ起動:
  - python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
- 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依らず本番用 DB を見る設計）

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - --from YYYY-MM-DD --to YYYY-MM-DD
- DB 指定:
  - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数または呼び出し側で引数指定）
- ニューススコアリングは kabusys.ai.news_nlp.score_news を通して利用
- レジーム判定は kabusys.ai.regime_detector.score_regime を通して利用
- API レート制限・エラーはリトライやフォールバック（macro_sentiment=0 など）で安全化

ファイル / フラグの取り扱い
- 停止フラグ（監視・実行の停止トリガ）:
  - data/stop_requested.flag — run_monitoring と run_execution の外部停止検出に使用
  - data/kill.flag — KillSwitch による ExecutionEngine 停止シグナル（存在すると engine 起動や継続に影響）
- PID ファイル:
  - data/execution.pid — ExecutionEngine が PID を書き込む（Settings.pid_file_path で上書き可）

ログ
- デフォルトでは logs/<app_name>.log に日次ローテートで出力（30 日分保持）
- setup_logging を全起動スクリプトで呼び出して統一的にログを管理
- コンソール出力は stdout（cron 等でリダイレクトしやすい）

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソース内の主要モジュールの簡易構成です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env の読み込みと Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                 — 発注関連（BrokerFactory, Engine, OrderManager など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

簡単な開発／運用メモ
--------------------
- データベース:
  - DuckDB は分析用途（prices_daily, raw_financials 等）に使用
  - SQLite は監視・取引ログ保存用（monitoring.db / paper_trading.db）
- Paper trading:
  - KABUSYS_ENV=paper_trading のとき run_execution は paper_sqlite_path を使用し、本番 DB と分離される
- 設定読み込み:
  - config.py はプロジェクトルートの .env/.env.local を自動で読み込みます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
- ローカルで AI を試す際は OPENAI_API_KEY を設定し、まずは小規模（短期間）で挙動確認を行ってください（API コストに注意）

トラブルシューティング
----------------------
- validate_config で警告やエラーが出たら指示に従って .env や config/*.yaml を確認してください
- AI 周りで失敗が多い場合は OPENAI_API_KEY を見直し、レート制限に注意（実装は自動リトライあり）
- ログディレクトリ作成に失敗している場合は書き込み権限やパスを確認（LOG_DIR 環境変数で変更可）
- psutil によるプロセス優先度設定で AccessDenied が出る場合、権限を確認（Linux の nice 範囲など）

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（現行実装）
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（無い場合は作者に問い合わせてください）

その他
-----
- 本ドキュメントはソースコードのコメント・設計注釈をもとに作成しています。実運用前に必ず validate_config と小規模な検証（paper_trading モード）を実行してください。