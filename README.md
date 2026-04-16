KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 監視 / リサーチ用ライブラリ兼実行フレームワークです。本リポジトリには以下の主要機能群が含まれます。

- 実行エンジン（ExecutionEngine）: ブローカーへ発注・状態管理・リスク制御を行う
- 監視（Monitoring）: システム状態・注文監視・リスク監視・アラート送信（LINE）等
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ算出、セクター制限
- 研究用モジュール: ファクター計算、特徴量探索、IC 計算など（DuckDB ベース）
- AI モジュール: ニュースのセンチメント算出（OpenAI）、市場レジーム判定
- ツール: Paper Trading の検証レポート生成、Streamlit 監視ダッシュボード等

主な特徴
--------
- 環境切替（development / paper_trading / live）に対応（Settings.env）
- Paper Trading 時は実口座と分離した専用 SQLite（data/paper_trading.db）を使用可能
- 監視用 DB（SQLite）と分析用 DB（DuckDB）を併用
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定を備える（API キー必要）
- モジュールは純粋関数設計や副作用を最小限に留めた設計（テスト容易性を考慮）
- 監視系は kill.flag/stop フラグや PID ファイルで外部停止や stale PID を検知

セットアップ
-----------
1. Python 環境を準備（推奨: venv）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必要最低限（例）:
     - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt を用意していることを想定してください。

3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 代表的な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI モジュールを使う場合必須）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - LOG_LEVEL（DEBUG/INFO/...）
   - Settings クラスが環境変数のバリデーションを行います。不足や不正な値は起動時に例外になります。

使い方（実行例）
----------------

基本的にパッケージを PYTHONPATH に含めてモジュールとして起動できます。開発環境ではルートから次のように実行します。

- ExecutionEngine 起動（本番 or paper_trading 切替）
  - PYTHONPATH=src python -m kabusys.run_execution
  - paper_trading にするには: export KABUSYS_ENV=paper_trading（または .env に設定）
  - paper_trading 時は MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
  - 実行時、data/execution.pid に PID を書き込み、data/stop_requested.flag により外部停止できます。

- Monitoring 起動（SystemMonitor のポーリング）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使って記録します
  - stop フラグ: data/stop_requested.flag を作成するとループが終了します

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - アクセスはブラウザから行います。DB は読み取り専用で開きます（URI に mode=ro を付与）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

注意: 上記コマンドは開発時に src を PYTHONPATH に含める前提です。パッケージをインストールした場合は python -m kabusys.run_execution などで動作します。

重要なファイル / フラグ
--------------------
- data/stop_requested.flag
  - run_monitoring/run_execution が参照する停止フラグ（存在するとループを終了）
- data/execution.pid
  - 実行エンジンの PID ファイル（SystemMonitor が存在・生存を検査）
- data/kill.flag
  - KillSwitch により書き込まれるファイル。存在すれば ExecutionEngine 停止シグナルとして扱う
- DB
  - 監視ログ（SQLite）: data/monitoring.db（Settings.sqlite_path）
  - Paper Trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - 分析用（DuckDB）: data/kabusys.duckdb（Settings.duckdb_path）

オプション / 環境変数の主な挙動
-----------------------------
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒）。1 未満や不正値はデフォルト 60 秒にフォールバック。
- KABUSYS_ENV: development / paper_trading / live（Settings.env）。paper_trading の場合は mock broker を使用。
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- OPENAI_API_KEY: AI モジュール（news_nlp, regime_detector）を使う際に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE push）を利用する場合に必要

開発者向けメモ
---------------
- .env 自動読み込み
  - プロジェクトルートは .git または pyproject.toml を元に自動判定し、.env / .env.local を読み込みます。
  - OS 環境変数は保護され、.env.local の強制上書きを防ぐ仕組みがあります（ただし override を許可する場合は上書き）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブル作成を行い、既存 DB に対して必要なカラム追加を行います（例: trade_logs.latency_ms, dashboard.peak_value）。
- プロセス優先度
  - run_monitoring/run_execution 起動直後に set_process_priority("high") を呼び出して優先度を上げる仕組みがあります（psutil を使用）。権限や OS により無視される場合があります。

ディレクトリ構成（主要ファイル）
------------------------------
下記は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/設定読み取り（Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — 監視用 SQLite のスキーマ初期化 / ラッパー（MonitoringDB）
    - system_monitor.py — CPU/MEM/DISK/データ鮮度/プロセス存否監視
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — 条件に応じて kill.flag を書くロジック
    - alert_manager.py — LINE Push による通知（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねるループ（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py — Streamlit ベースの監視 UI（起動コマンド参照）
  - execution/
    - order_manager.py — 発注フローの外向き API（OrderManager）
    - reconciler.py — 起動時の注文・ポジション同期処理
    - order_repository.py, order_record.py, broker_factory.py, execution_engine.py …（発注関連実装）
  - portfolio/
    - portfolio_builder.py — 候補選定、等金額/スコア重み
    - position_sizing.py — 発注株数計算（単元丸め、リスク/上限考慮）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores へ書込む
    - regime_detector.py — ETF MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
  - utils/
    - process_priority.py — psutil を用いた優先度 / affinity 設定ユーティリティ
  - data/ （ランタイムで利用するディレクトリ。DB・フラグ等を配置）

付記 / 運用上の注意
------------------
- AI モジュールは外部 API（OpenAI）に依存します。API 制限やエラー発生時にはフェイルセーフで継続する設計になっていますが、API キーの管理（レートや課金）に注意してください。
- Paper Trading モードは本番 DB と完全に分離される設計です。誤って本番 DB を上書きしないよう環境変数の設定に注意してください。
- Run スクリプト群は stop フラグ / kill.flag / PID に依存するため、適切なクリーンアップ運用（起動前に古いフラグを削除する等）を推奨します（Settings.kill_flag_clear_on_start を利用可能）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って .env の自動ロードを無効化できます。

ライセンス / コントリビューション
--------------------------------
- 本リポジトリ独自のライセンス表記やコントリビューションルールがあればプロジェクトルートに追加してください（このサンプルコードでは言及がありません）。

以上。設定や実行で不明点があれば、使用したいユースケース（ローカル開発 / 本番デプロイ / Paper Trading）を教えてください。具体的な .env の例や起動コマンドのテンプレートを用意します。