KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を行うための小規模フレームワークです。本リポジトリには以下の主要機能を実装しています。

- ExecutionEngine：発注・リスク管理・注文照合を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文状態・リスクをポーリングしてアラート／Kill Switch を管理
- Portfolio construction：候補選定、重み付け、株数決定などの純粋関数群
- Research：ファクター計算・特徴量探索（DuckDB を使った分析）
- AI モジュール：ニュースの NLP スコアリング・市場レジーム判定（OpenAI API を使用）
- ユーティリティ：設定読み込み、対話式 .env ウィザード、設定検証、ログ設定、プロセス優先度設定 など
- ツール：Paper Trading の検証レポート生成スクリプト

主な機能一覧
--------------
- 環境設定管理（.env 自動読み込み・Settings クラス）
- 対話式 .env ウィザード（python -m kabusys.config_setup）
- 起動前チェック（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading DB に記録
  - stop フラグ（data/stop_requested.flag）および PID ファイル管理
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - 環境に関わらず本番 sqlite_path を監視用に使用
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視用 DB 層（SQLite）と MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- AI: OpenAI を用いたニュースセンチメント（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- DuckDB ベースの research モジュール（ファクター計算、将来リターン、IC 等）
- portfolio モジュール：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- ツール: Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

セットアップ手順
-----------------
前提: Python 3.10 以上（PEP604 の | 型表記を使用）

1. リポジトリをクローン
   - 例: git clone <repo_url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ（プロジェクトに合わせて requirements.txt を用意している場合はそれを使ってください）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. データ・ログ用ディレクトリを作成
   - mkdir -p data logs

5. .env を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考にする）

必須環境変数（主なもの）
-----------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — AI 機能を使う場合（news_nlp / regime_detector）

主な任意／デフォルト
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG 等に設定可能）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）

使い方（主要コマンド）
---------------------
- .env の対話式作成／更新
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード用 DB を使用（環境変数で PAPER_TRADING_SQLITE_PATH を上書き可）
  - 実行はスレッドで行われ、data/stop_requested.flag を作成することで停止シグナルを送れる
  - 実行中は data/execution.pid に PID を書き込む

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=<秒> でポーリング間隔を変更可能（デフォルト 60）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を明示する場合: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - ニューススコア: kabusys.ai.score_news（DuckDB 接続と date を渡して実行）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（DuckDB 接続と date を渡して実行）

注意点 / 運用に関する概略
------------------------
- 監視（Monitoring）は監視 DB（SQLite）に状態を永続化します。init_monitoring_db により必要テーブルを作成します。
- Execution は paper_trading モードと本番モードで DB を分離しているため、ペーパートレードの記録は本番 DB を汚さない設計です。
- Kill Switch：リスク閾値（ドローダウンやポジション上限）を超えた場合に data/kill.flag を書き込むことで ExecutionEngine を停止する仕組みがあります。KILL_FLAG_CLEAR_ON_START 環境変数に注意（本番では自動クリアを推奨しない）。
- ログ: logs/<app_name>.log に日次ローテートで出力されます。コンソールは stdout に出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- config.py                  — 環境変数 / Settings 管理、.env 自動ロード処理
- config_setup.py            — .env 対話式ウィザード CLI
- validate_config.py         — 設定検証 CLI

src/kabusys/ai/
- news_nlp.py                — ニュースを OpenAI でスコアリングして ai_scores に書き込む
- regime_detector.py         — マクロ + MA を組み合わせた市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py           — SQLite 監視テーブルの作成・永続化 API
- system_monitor.py          — CPU/Mem/Disk、データ鮮度、実行プロセス監視
- trade_monitor.py           — （注文関連の監視ロジック；コードベースに一部あり）
- risk_monitor.py            — ドローダウン・ポジション上限監視
- kill_switch.py             — kill.flag の作成 / 管理
- monitoring_engine.py       — 各 Monitor を束ねるエンジン
- alert_manager.py           — （通知送信ラッパー：LINE などを想定）

src/kabusys/portfolio/
- portfolio_builder.py       — 候補選定・重み計算
- position_sizing.py         — 株数計算・キャップ処理
- risk_adjustment.py         — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py         — Momentum / Volatility / Value 等のファクター計算（DuckDB）
- feature_exploration.py     — 将来リターン・IC・統計サマリ

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート生成 CLI

src/kabusys/utils/
- logging_setup.py           — ロギング初期化ユーティリティ
- process_priority.py        — プロセス優先度 / CPU affinity 設定

補足（実装上のポイント）
-----------------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数（秒）で変更可能。0 以下や不正値は無視されデフォルト 60 秒にフォールバックします。
- AI モジュールは OpenAI のレスポンス不安定時に指数バックオフでリトライし、失敗してもフェイルセーフ（スコア 0 や処理スキップ）で継続する設計になっています。
- DuckDB / SQLite を使うため、分析用 DB（duckdb）と運用ログ（sqlite）の両方を管理します。

トラブルシューティング
-----------------------
- PyYAML がないと config/*.yaml のパースチェックはスキップされます（validate_config が警告を出します）。インストールするには pip install PyYAML。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。LOG_DIR を確認してください。
- OpenAI API 呼び出しには有効な OPENAI_API_KEY が必要です。キー未設定時は該当機能は起動時に例外を投げます（使用箇所で明記）。

開発者向けメモ
----------------
- 各モジュールは可能な限り副作用を避け、純粋関数（portfolio, research）と副作用を持つ I/O 層（monitoring_db, execution 層）を分離する設計です。
- テストのために外部 API 呼び出し（OpenAI 等）は _call_openai_api を patch して差し替えられるように実装されています。
- DuckDB 接続は関数に注入（引数で渡す）する設計なので、ユニットテストで in-memory DB を使うことが容易です。

最後に
-------
この README はコードベースの主要部分をカバーしています。実運用する際は .env の取り扱いや Kill Switch の挙動、ペーパートレード/本番 DB の分離ルールに特に注意してください。要件に合わせて config/*.yaml や設定値を調整してください。