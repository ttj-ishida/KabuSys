# KabuSys — 日本株自動売買システム（README）

このリポジトリは、日本株向けの自動売買／研究／監視ツール群をまとめたパッケージです。主要な機能は取引実行エンジン、監視モジュール、ポートフォリオ構築ユーティリティ、リサーチ（ファクター計算）、LLM を使ったニュースNLP / レジーム判定などを含みます。

以下はプロジェクトの概要、機能一覧、セットアップ手順、基本的な使い方、およびディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的：日本株向けの自動売買システム（ExecutionEngine）およびそれを支える監視・リスク制御・分析ツール群の提供。
- 設計方針：
  - 実行系と監視系を分離（監視は production の monitoring DB を参照）。
  - Paper Trading（模擬発注）と Live（本番）を切り替え可能。
  - DuckDB を分析用 DB として、SQLite を監視・発注ログ用に使用。
  - LLM（OpenAI）連携は外部 API キーで明示的に制御。失敗時はフェイルセーフで継続する設計。

バージョン: __version__ = 0.1.0

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）。
  - Paper Trading モード: KABUSYS_ENV=paper_trading のとき MockBroker を使用し、専用 SQLite（data/paper_trading.db など）に記録。
  - リスク管理（RiskManager）と Reconciler、OrderManager、OrderRepository を提供。

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - run_monitoring スクリプトでポーリング監視を実行（MONITOR_POLL_INTERVAL で間隔を指定可能）。
  - kill.flag による外部停止（Kill Switch）、stop_requested.flag によるプロセス停止制御。
  - 監視ログ永続化用 MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard。

- ポートフォリオ構築（Portfolio）
  - 候補選定（select_candidates）、等金額・スコア重み計算（calc_equal_weights, calc_score_weights）。
  - セクターキャップ適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - 発注株数決定（calc_position_sizes）：リスクベース／等分配／スコア配分対応、単元株丸め処理、aggregate cap 適用。

- リサーチ（Research）
  - ファクター計算（momentum, volatility, value）: DuckDB の prices_daily / raw_financials を利用。
  - 将来リターン計算、IC（Spearman ランク相関）、ファクター統計サマリ等。

- AI（LLM）連携
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成し ai_scores に保存。
  - regime_detector.score_regime: ETF（1321）MA200 乖離 + LLM マクロセンチメントで市場レジーム（bull/neutral/bear）を判定して保存。
  - API 呼び出しはリトライとフェイルセーフ実装あり。

- ツール
  - config_setup: 対話式ウィザードで .env を生成/更新（python -m kabusys.config_setup）。
  - validate_config: 起動前チェック（必須環境変数・ファイル存在・YAML パース確認 等）（python -m kabusys.validate_config）。
  - paper_verification_report: Paper Trading DB のレポート生成ツール（python -m kabusys.tools.paper_verification_report）。

- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーションファイル）。
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ。

---

## セットアップ手順（開発 / 実行環境構築）

1. リポジトリをクローンして Python 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（例）:
   - pip install -r requirements.txt
   - 必須例: duckdb, psutil, openai
   - オプション: PyYAML（config バリデーションで YAML をパースする場合）

   ※ 本リポジトリに requirements.txt がない場合は duckdb, psutil, openai, （PyYAML）を個別にインストールしてください。

3. .env の作成:
   - 対話式で作成: python -m kabusys.config_setup
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...  （LLM 機能を使う場合）

4. 設定検証（オプション）:
   - python -m kabusys.validate_config
   - 本番環境を厳密にチェックしたい場合は --strict を追加。

5. ログディレクトリ:
   - デフォルトは logs/（setup_logging が自動作成します）。失敗時はコンソール出力のみ。

---

## 使い方（主要コマンド）

- 監視ループを起動（本番では systemd / Supervisor 等で起動想定）:
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（秒、デフォルト 60）でポーリング間隔を上書き可能。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（環境にかかわらず production sqlite_path を使う実装になっています）。
  - 監視停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は mock ブローカーを使用し、paper_sqlite_path（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
  - 実行中の停止は stop flag や kill flag（監視側が条件を満たすと作成）で制御されます。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数: PAPER_TRADING_SQLITE_PATH を使用するか、--db で指定可能。

- .env の作成 / 更新:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config [--strict]

- AI 関連（プログラムから利用する API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースをスコアリング。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを判定して DB に保存。

---

## 重要な環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO, DEBUG）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: (0/1) Execution 起動時に kill.flag を自動クリアするか

---

## 停止／フラグ制御

- データディレクトリ内のフラグファイル:
  - data/stop_requested.flag — run_monitoring / run_execution がチェックする停止フラグ（存在すると安全に停止）。
  - data/kill.flag — KillSwitch により書き込まれると ExecutionEngine に停止シグナルとして扱われる（設定により起動時に自動クリア可）。

---

## ログ

- ロギングは kabusys.utils.logging_setup.setup_logging で統一。
- 出力先:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- LOG_DIR 環境変数でログディレクトリを上書き可能。

---

## ディレクトリ構成（抜粋）

ルートの src/kabusys 以下の主要ファイル／ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定読み込み
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — 監視ポーリング起動スクリプト
  - run_execution.py        — 実行エンジン起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ & 永続化 API
    - system_monitor.py
    - trade_monitor.py      — （ファイル存在、実装例あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （通知ロジック）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/              — 監視関連（上記）
  - tools/
    - paper_verification_report.py

（この README はコードベースの主要モジュールを抜粋して解説しています。実際の全ファイルは src/kabusys 以下を参照してください。）

---

## 開発時の注意事項 / 実装上の重要ポイント

- run_monitoring は MONITOR_POLL_INTERVAL（環境変数）でポーリング間隔を制御。0 以下や不正な値はデフォルト 60 秒にフォールバック。
- run_monitoring の監視 DB 接続は「監視用 sqlite_path（Settings.sqlite_path）」を常に使用します（環境にかかわらず本番監視 DB を使う仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して発注ログを本番 DB から分離します。
- LLM（OpenAI）連携は API キーが必須。API 呼び出しはリトライやフェイルセーフ処理を実装しているが、利用時は料金・レート制限に注意してください。
- MonitoringDB.init_monitoring_db はマイグレーション（カラム追加）を安全に行う処理を持ちます（冪等化）。

---

## よく使うコマンド例

- .env を作る（対話式）:
  - python -m kabusys.config_setup

- 設定を検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視を起動（デフォルト間隔 60s）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（paper_trading 等を .env で設定）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含めるサンプル .env のテンプレートや、システム運用時の systemd ユニット / Supervisor のサンプルも追加できます。どの情報をより詳細に載せたいか教えてください。