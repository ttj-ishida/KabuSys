KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 補助）を想定した Python コードベースです。  
主な目的は「安全に」「再現可能に」「本番・ペーパートレードを分離して」トレーディングを行うことです。

主なコンポーネント
- execution: 発注エンジン（ExecutionEngine）／注文管理／ブローカークライアント切替（本番 / ペーパートレード）
- monitoring: システム稼働監視、注文監視、リスク監視、Kill Switch（停止フラグ）とアラート管理
- portfolio: 候補選定・重み計算・リスク調整・ポジションサイジング
- research: DuckDB を用いたファクター計算・特徴量探索（ファクター、IC、将来リターン等）
- ai: OpenAI を使ったニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）
- utils: ロギング設定、プロセス優先度などのユーティリティ
- tools: ペーパートレード検証レポート生成スクリプトなど
- config: 環境変数の自動読み込み、Settings クラス、対話式 .env ウィザード、設定検証 CLI

機能一覧
--------
- 発注エンジン（実際発注 / モック発注の切替）
- 監視ループ（CPU/メモリ/ディスク/プロセス状態/データ鮮度）
- リスク監視（ドローダウン検出、ポジション数上限検出）と Kill Switch（data/kill.flag 生成）
- 監視ログ永続化（SQLite）と簡易 DB マイグレーション（monitoring_db）
- ポートフォリオ構築（候補選定、等配分・スコア加重、リスク調整、ポジションサイジング）
- ファクター計算（モメンタム、ボラティリティ、バリュー）および特徴量解析（IC, summary）
- OpenAI を用いたニュースセンチメント・マクロセンチメント（スコアリング、リトライ・バリデーション）
- ペーパートレード検証レポート出力（成功率・レイテンシ・稼働率等の判定）
- 対話式 .env 作成ウィザードと設定検証 CLI

前提 / 推奨環境
----------------
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証用; 任意）
- ファイルベース DB（DuckDB/SQLite）を利用（デフォルトパスは data/ 配下）

セットアップ手順
----------------

1. リポジトリをクローンし仮想環境を作成
   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 例（pip）:
     - pip install duckdb psutil openai
     - （開発時）pip install PyYAML

   ※ requirements.txt が用意されていれば pip install -r requirements.txt を使ってください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います:
     - python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリを確認
   - デフォルト DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - ログ:
     - デフォルト logs/ ディレクトリにアプリ毎のログ（例: logs/execution.log）

使い方
------

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API 用
- 選択 / デフォルトあり
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知設定（任意）
  - OPENAI_API_KEY: OpenAI を使う機能（ai/）で必要
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリア禁止推奨（0 が推奨）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
  - その他: PAPER_FILL_MODE（paper_trading の fill 動作制御）

起動スクリプト
- ExecutionEngine 起動（発注系）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
    - 実行中に data/stop_requested.flag が存在すると実行スレッドを停止します
    - data/execution.pid に PID を書きます

- Monitoring 起動（監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を上書き可能（秒）
  - 監視は本番 sqlite_path を使って永続化（KABUSYS_ENV に依らず本番 DB を使用）

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

設定の検証 / ウィザード
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

Kill Switch / 停止フラグ
- KillSwitch は特定条件（ドローダウン超過等）で data/kill.flag を書き込み、ExecutionEngine 側で停止する仕組みです。
- 管理者が手動で停止を要求する場合は data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して停止します。
- 再起動時に kill.flag を自動クリアしたくない場合は KILL_FLAG_CLEAR_ON_START を 0 にしてください（本番推奨）。

ログ
- setup_logging により stdout とファイル（logs/<app_name>.log、日次ローテーション、30日保持）が設定されます。
- LOG_DIR 環境変数でログディレクトリを変更可能。

ディレクトリ構成（主要ファイル）
--------------------------------
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — Settings クラス、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 経由のセンチメント）
    - regime_detector.py      — 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py        — SQLite のスキーマ + MonitoringDB ラッパー
    - system_monitor.py       — システム監視（CPU/メモリ/プロセス/データ鮮度）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — （注文監視; コードベースに存在）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - kill_switch.py          — kill.flag の管理
    - alert_manager.py        — （アラート送信ロジック; コードベースに存在）
  - execution/
    - execution_engine.py     — ExecutionEngine 実装（スレッド制御等）
    - broker_factory.py       — ブローカークライアント生成（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
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
  - data/                      — データ / DB（実行時に作成されることがある）
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

注意点 / 運用上のヒント
-----------------------
- 本番環境では KABUSYS_ENV=live を設定し、LINE 通知等のアラートを有効にすることを検討してください。ただし本番では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。
- paper_trading は本番 DB と物理的に分離するよう設定されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 使用機能は API キー（OPENAI_API_KEY）が必要です。API の呼び出しはリトライとレスポンス検証を行いますが、コストとレイテンシには注意してください。
- ログディレクトリ作成に失敗した場合はコンソールログのみになります。権限等を確認してください。
- DuckDB/SQLite の初期化はスクリプト内で行われますが、prices / raw_news 等のデータは外部からロードする必要があります（データパイプラインは kabusys.data.pipeline 等に実装想定）。

貢献 / 拡張のポイント
---------------------
- 戦略モデル（signal generator）やブローカークライアントを独自実装して差し替え可能
- ポートフォリオ構築やサイジングのパラメータは設定化して実験できるように拡張可能
- モニタリング・アラートのチャネル追加（メール/Slack 等）は alert_manager を拡張
- DuckDB 内の prices / raw_financials 等の ETL を別モジュールで実装して投入

ライセンス / その他
-------------------
- この README ではソース内の利用方針・設計意図を要約しています。実運用で使用する場合は十分な QA とリスクレビューを行ってください。

必要であればサンプル .env テンプレート、より詳細な運用手順（systemd/cron/uWSGI でのデーモン化、バックアップ方針）、DB 初期化スクリプト、及び各モジュールの API 仕様書を追加で作成します。どのドキュメントを優先して追加しますか？