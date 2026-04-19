# KabuSys README

KabuSys は日本株の自動売買システム向けライブラリ／ランブック群です。ポートフォリオ構築、ポジションサイジング、モニタリング、ペーパートレード検証、LLM を用いたニュースセンチメントやレジーム判定などのユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド、ツール）
- 環境変数（主なもの）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- 日本株の自動売買システムのための共通コンポーネント群。
- 監視（Monitoring）・実行（Execution）・リサーチ（Research）・ポートフォリオ構築（Portfolio）・AI（ニュースNLP/レジーム判定）・ユーティリティ（ログ設定、プロセス優先度等）を提供。
- DBは主に SQLite（監視 / ペーパートレード）と DuckDB（分析）を使用。
- LLM（OpenAI）を使ったニュースセンチメント、マクロセンチメントによるレジーム判定機能を備える。

---

主な機能一覧
- 設定管理
  - .env 自動ロード（プロジェクトルートに .env / .env.local があれば読み込み）
  - Settings クラスによる環境変数アクセス（型チェック・検証）
  - 対話式セットアップウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行系
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading では専用の paper_trading DB（data/paper_trading.db）と MockBrokerClient を使用し、本番DBと分離
    - 停止は data/stop_requested.flag 等のフラグで制御（pidファイル: data/execution.pid）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更可能（デフォルト60秒）
    - 監視 DB（SQLite）の初期化・永続化ユーティリティ
    - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止させる
- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分／スコア配分の重み計算、ポジションサイジング（単元株丸め、集計上限・リスクベース）
  - セクター集中制限・レジーム乗数
- リサーチ（DuckDB を利用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC（情報係数）・特徴量サマリー等の解析関数
- AI（OpenAI）
  - ニュースNLP: raw_news を集約して LLM へ送り銘柄ごとのセンチメントを ai_scores テーブルへ書き込む（kabusys.ai.news_nlp）
  - レジーム判定: ETF ma200 乖離 + マクロニュースセンチメントで market_regime を算出・永続化（kabusys.ai.regime_detector）
  - どちらも OPENAI_API_KEY を参照または引数で渡す設計。gpt-4o-mini を使用する想定。

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
    - 稼働率、注文成功率、レイテンシ等を集計し PASS/FAIL を判定

- ユーティリティ
  - 統一的なロギング設定（stdout + 日次ローテーションファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - SQLite / DuckDB の初期スキーマ（監視テーブル等）

---

セットアップ手順（ローカル開発時の例）
1. リポジトリをクローンして src を Python path に含めるかパッケージをインストールします（pyproject.toml があれば pip install -e .）。
2. Python 依存関係（主なもの）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証時にあれば設定ファイル YAML の構文チェックが行われる）
   - （標準ライブラリ: sqlite3 等）
   例: pip install duckdb psutil openai pyyaml
   （requirements.txt はリポジトリに含まれていないためプロジェクト側で管理してください）
3. 環境変数設定
   - 対話式で .env を作る: python -m kabusys.config_setup
   - 生成後、設定を検証: python -m kabusys.validate_config
   - なお、自動で .env/.env.local をロードする仕組みがあり、環境変数が存在する場合は上書きされません。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
4. データディレクトリ（data/）・ログディレクトリ（logs/）は起動時に自動作成されますが、権限に注意してください。

---

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading のとき Execution は paper_trading DB を使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring 用 DB
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — paper_trading 用 DB
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。0/1、デフォルト 0）

validate_config（検証 CLI）は .env と config/*.yaml の存在や基本的な値の妥当性をチェックします。--strict を付けると警告も FAIL 扱いになります。

---

使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告もエラーにする）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番／ペーパー両対応）
  - python -m kabusys.run_execution
  - ペーパートレードを使う場合は KABUSYS_ENV=paper_trading を設定してから起動
  - 停止制御: data/stop_requested.flag を作成するとエンジン停止。起動時に既に stop フラグがあると起動せず終了。

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: export MONITOR_POLL_INTERVAL=30（秒）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）に書き込む（Monitoring は環境にかかわらず本番 sqlite_path を使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能の呼び出し例（ライブラリ API）
  - ニューススコア計算:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ
  - デフォルト: logs/<app_name>.log（app_name は実行スクリプトで指定: "execution" / "monitoring" 等）
  - stdout にも出力（StreamHandler）。ファイルは日次ローテーション、30日分保持。

---

停止フラグ / PID / Kill Switch
- stop フラグ（起動スクリプト間の短絡停止）
  - run_monitoring / run_execution はプロジェクト直下の data/stop_requested.flag を監視しており、存在するとポーリングループやスレッドを終了します。
- kill.flag（Kill Switch）
  - KillSwitch が条件を評価して必要なら data/kill.flag を書き込みます（ExecutionEngine はこれを検出して停止する仕組み）。KILL_FLAG_CLEAR_ON_START 設定に注意してください。
- PID ファイル
  - 実行時に data/execution.pid を使用（設定により変更可）。run_execution は _EXECUTION_PID を作る仕組みがある（Engine に渡される）。

---

スキーマ / DB 初期化
- monitoring_db.init_monitoring_db(conn) が監視テーブル群（system_status / trade_logs / positions / risk_logs / dashboard）を作成します（冪等）。
- マイグレーション処理（カラム追加）も一部含む（例: trade_logs.latency_ms, dashboard.peak_value）。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- __init__.py
- config.py                — Settings クラス、.env 自動ロード
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント取得（OpenAI 経由）
  - regime_detector.py     — 市場レジーム判定（ma200 + マクロニュース）

- monitoring/
  - monitoring_db.py       — SQLite 永続化層（監視テーブル）
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - trade_monitor.py       — （存在する想定）注文ログ監視
  - alert_manager.py       — （アラート送信管理, 実装に依存）

- execution/
  - execution_engine.py    — ExecutionEngine（起動ロジック）
  - broker_factory.py      — BrokerClientFactory（本番 / mock の切替）
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

- tools/
  - __init__.py
  - paper_verification_report.py

- utils/
  - logging_setup.py       — ログ設定
  - process_priority.py    — 優先度・CPU affinity 設定
  - __init__.py

- data/                   — 実行時に使用するデフォルトの格納先（DB・フラグ等）
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード)
  - kill.flag / stop_requested.flag / execution.pid

--- 

注意事項 / 実運用ガイド
- KABUSYS_ENV を live にする前に validate_config を実行し、LINE 通知等の本番ガードを確認してください。
- OpenAI API を利用する機能は外部 API へのアクセスを伴いコストがかかります。APIキーの管理に注意してください（.env を絶対に Git にコミットしない）。
- Monitoring は sqlite_path（デフォルト data/monitoring.db）を使用しているため、複数プロセスで同一ファイルへ同時書き込みが発生しないよう実行計画を立ててください。
- ログディレクトリ作成失敗などの際はコンソール（stdout）への出力にフォールバックします。権限・ディスク容量に注意してください。
- ペーパートレード時は paper_trading の DB に完全分離される設計です（本番 DB を汚染しません）。

---

貢献 / 拡張ポイント（参考）
- stocks マスタに個別単元（lot）情報を追加して position_sizing を拡張
- trade_monitor / alert_manager の実装を充実させ LINE / Slack 通知を統合
- YAML ベースの細かい設定を validate_config でさらに厳密にチェック
- DuckDB スキーマの自動構築スクリプト追加（research 用テーブル初期化）

---

以上。必要であれば README の英語版や、実行フロー図（Execution ↔ Monitoring ↔ KillSwitch 等）を追加で作成します。どの部分を詳しくドキュメント化したいか教えてください。