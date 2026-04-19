README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究支援ライブラリ兼実行フレームワークです。  
主に以下の目的を持ちます。

- 実行エンジン（ExecutionEngine）による発注管理（実口座 / ペーパートレード対応）
- 監視コンポーネント（Monitoring）によるシステム・オーダー・リスク監視と Kill Switch
- ポートフォリオ構築・ポジションサイジング等の純粋関数群（戦略ロジック）
- DuckDB を用いた研究用ファクター計算・特徴量解析
- OpenAI を用いたニュース NLP / レジーム判定（任意）

特徴
----
- 実行（live）とペーパートレード（paper_trading）を明確に分離（ペーパートレードは専用 SQLite に記録）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による自動停止機構
- DuckDB を用いた高速な時系列・ファクター計算（research モジュール）
- OpenAI（gpt-4o-mini など）を利用したニュースセンチメント / レジーム判定モジュール（オプション）
- ログはコンソールと日次ローテートファイルに統一的に出力（logs/ ディレクトリ、30日保持）
- .env ベースの設定管理と対話式ウィザード・検証 CLI を備える

セットアップ
----------
1. Python 3.9+ を用意してください（typing の記法から 3.10+ を推奨します）。
2. 必要なパッケージをインストールしてください（プロジェクトに requirements.txt が無い場合の一例）:

   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（config の検証を有効にする場合）

   例:
   pip install duckdb psutil openai pyyaml

3. プロジェクトルートに .env を配置します。自動読み込みの仕組みは Settings モジュールが提供し、
   OS 環境変数 > .env.local > .env の優先順位で設定を読み込みます。自動ロードを無効化する場合は
   KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL / LOG_DIR — ログ出力設定

例 (.env)
---------
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方
------

設定ウィザード（対話的）
- 初回セットアップ用に .env を対話的に作成できます:
  python -m kabusys.config_setup

設定検証
- .env と config/*.yaml（存在する場合）を起動前に検証します:
  python -m kabusys.validate_config
  --strict を付けると警告もエラー扱いになります

ExecutionEngine（取引実行）
- 実行エンジンを起動します。KABUSYS_ENV により実挙動（live）かペーパー（paper_trading）かが変わります。
  python -m kabusys.run_execution

  特記事項:
  - paper_trading 環境では MockBrokerClient を使い、記録は data/paper_trading.db へ行います（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在するとエンジンは起動せず終了します。
  - エンジンは data/execution.pid に PID を書きます（設定でパス変更可）。
  - 停止は data/stop_requested.flag を作成するか、監視側の Kill Switch（data/kill.flag）で行います。

Monitoring（監視ループ）
- システム／注文／リスク監視を行う監視プロセスを起動します:
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。無効な値は 60 にフォールバック。
  挙動:
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず監視は一元化）。
  - data/stop_requested.flag が出現するとポーリングループは終了します。

Paper Trading 検証レポート
- ペーパートレードのログを解析して検証レポートを生成します:
  python -m kabusys.tools.paper_verification_report
  オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

AI 機能
- ニュース NLP（ニュースのセンチメント付与）:
  kabusys.ai.score_news を利用。OpenAI API キーが必要です。
- レジーム判定:
  kabusys.ai.regime_detector.score_regime を利用。OpenAI API キーが必要です。

ログ
- デフォルトでは logs/<app_name>.log に日次ローテートで出力されます（30日分保持）。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で設定できます。

停止・Kill Switch
- 実行停止用フラグ:
  - data/stop_requested.flag — 監視・実行スクリプトが確認して正常終了します
  - data/kill.flag — KillSwitch が書き込み実行エンジンに停止を促します
- Settings.kill_flag_clear_on_start=1 を設定すると ExecutionEngine 起動時に kill.flag を自動で削除します（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
--------------------------------
プロジェクトルート（src 以下を想定）:

src/kabusys/
- __init__.py
- config.py                 — 環境変数・.env 自動読み込みロジック
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリングループ起動スクリプト

src/kabusys/ai/
- news_nlp.py               — ニュースを OpenAI でスコアリング
- regime_detector.py        — マクロ + MA を合成したレジーム判定
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py          — SQLite 永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
- system_monitor.py         — CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
- trade_monitor.py          — （取引系監視、ファイル内に存在）
- risk_monitor.py           — ドローダウン・ポジション上限監視
- monitoring_engine.py      — 各モニタを束ねる
- kill_switch.py            — kill.flag の作成・判定
- alert_manager.py          — （アラート送信管理）

src/kabusys/portfolio/
- portfolio_builder.py      — 候補選定・重み計算
- position_sizing.py        — 発注株数算出・集約キャップ
- risk_adjustment.py        — セクターキャップ・レジーム乗数
- __init__.py

src/kabusys/research/
- factor_research.py        — Momentum / Volatility / Value 等のファクター計算（DuckDB）
- feature_exploration.py    — 将来リターン・IC / 統計サマリー計算
- __init__.py

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- __init__.py

src/kabusys/utils/
- logging_setup.py          — 共通のログ設定ユーティリティ
- process_priority.py       — プラットフォーム横断的なプロセス優先度 / CPU affinity 設定
- __init__.py

その他（データ・ログ）
- data/                      — デフォルトの DB / フラグ / pid ファイル置き場
  - monitoring.db (SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                      — ログファイル出力先（LOG_DIR）

設計上の注意点
-------------
- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意書きあり）。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にしておくことを推奨します。
- AI 機能は OpenAI API の利用料金・レイテンシを伴います。API キー管理と呼び出しレートに注意してください。
- DuckDB を使用する研究系モジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データ投入パイプラインは別途必要です。
- Monitoring は本番 DB を参照して常時ログを残す設計です（監視データは環境にかかわらず同一 sqlite_path に記録されます）。

よく使うコマンド一覧
-------------------
- .env 作成（ウィザード）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視ループ起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

サポート / 貢献
----------------
バグ報告や機能追加提案は Issue を立ててください。改修の際は既存の .env / DB マイグレーションに注意して下さい（monitoring_db では一部マイグレーション処理を行っています）。

以上。