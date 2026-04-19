# KabuSys

日本株自動売買システムの一部コードベース（README）。  
この README はリポジトリ内の主要スクリプト／モジュールを元に、日本語でプロジェクト概要・機能・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

注意: 実運用前に必ず .env を作成し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム（プロトタイプ〜運用支援ツール群）です。  
主な責務は次の通りです。

- 発注エンジン（ExecutionEngine）による注文管理・リスク管理（本番 / ペーパートレード対応）
- システム状態・注文状況の監視（Monitoring）
- ポートフォリオ構築・ポジションサイジング・リスク調整の純粋関数群
- リサーチ（ファクター計算、特徴量探索）
- ニュース NLP / LLM を用いたセンチメント解析・市場レジーム判定
- 運用検証ツール（Paper Trading 検証レポート等）
- ログ・プロセス優先度管理などのユーティリティ群

設計方針として、
- DB 層は SQLite / DuckDB を使用（分析と監視を分離）
- Paper Trading は本番 DB と分離（`data/paper_trading.db`）
- LLM 呼び出しは冪等性・エラーハンドリング重視（リトライ・フォールバック）
- ルックアヘッドバイアス対策（date.today() 等を直接参照しない設計）  
などが反映されています。

---

## 機能一覧

主要機能・モジュールの概要:

- 実行（Execution）
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBroker / paper DB を使用。
  - order_manager / order_repository / risk_manager / reconciler 等の発注関連コンポーネント。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（停止フラグ対応、ポーリング間隔は環境変数で変更可）。
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager（アラート管理）等。
  - monitoring_db: 監視用 SQLite スキーマ定義・永続化ロジック。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定、等重/スコア重み、株数算出、セクター上限・レジーム乗数。

- リサーチ（Research）
  - factor_research: Momentum, Volatility, Value などのファクター計算（DuckDB を用いた SQL 実行）。
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）や統計サマリー。

- AI（LLM）
  - ai.news_nlp: raw_news を集約して OpenAI (gpt-4o-mini) で銘柄ごとのセンチメントを算出し ai_scores に保存。
  - ai.regime_detector: マクロニュース + ETF MA200 乖離を組み合わせて市場レジーム判定。

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（コンソール + 日次ローテートファイル）。
  - utils/process_priority.py: プロセス優先度設定 / CPU affinity。
  - config.py: 環境変数読み込み・Settings クラス（.env 自動ロード含む）。
  - config_setup.py: 対話式 .env 作成ウィザード。
  - validate_config.py: 起動前設定検証 CLI。

- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析し検証レポートを出力。

---

## システム要件（推奨）

- Python 3.10 以上（型注釈や `X | Y` 構文を利用しているため）
- 必須パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）:
  - PyYAML（config 検証で YAML のパースを行う場合）
- SQLite は標準ライブラリで利用可能

依存パッケージはプロジェクトの requirements.txt が存在すればそれを利用してください。存在しない場合は上記を pip でインストールしてください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンしプロジェクトルートへ移動。

2. 仮想環境を作成して有効化（任意だが推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール。
   - pip install -r requirements.txt  （存在する場合）
   - または個別に: pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワードなど必須項目を入力します。
   - もしくは .env を手動作成（.env.example を参考に）。

5. 設定検証（起動前に必ず実行推奨）
   - python -m kabusys.validate_config
   - 注意: --strict オプションを付けると警告も失敗扱い（exit code 1）になります。

6. データディレクトリ作成
   - デフォルトでは data/, logs/ が使用されます。必要に応じて作成してください。
   - 実行時にもコードが自動で作成する場合があります。

---

## 環境変数（重要なもの・説明）

主な環境変数とデフォルト:

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか (0/1、デフォルト: 0)
- KILL_FLAG_PATH / PID_FILE_PATH: kill.flag / pid ファイルのパス（Settings から取得）

実行スクリプトによる挙動の差:
- run_execution: KABUSYS_ENV=paper_trading の場合は paper DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
- run_monitoring: 監視（monitoring）は環境にかかわらず production sqlite_path（Settings.sqlite_path）を使用する点に注意。

---

## 使い方（主要コマンド例）

前提: project root から実行する。パッケージをインストール済みか、プロジェクト root を PYTHONPATH に含めること。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: 起動前に kill.flag が存在すると起動せず終了します。
  - Paper trading: export KABUSYS_ENV=paper_trading（もしくは .env で設定）

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: export MONITOR_POLL_INTERVAL=30
  - 停止: data/stop_requested.flag を作成するとループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム判定・ニューススコアリングはライブラリ関数経由で呼び出す:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- ログ設定
  - 各起動スクリプトは最初に kabusys.utils.logging_setup.setup_logging(app_name=...) を呼び出します。
  - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます。

---

## 運用上の注意・振る舞い

- Kill Switch
  - RiskMonitor が一定閾値を超えると KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされますが、本番では危険なので推奨されません。

- DB 分離
  - Paper Trading は paper_sqlite_path に保存され、本番 monitoring DB（SQLITE_PATH）とは分離されています。これにより検証と本番のデータ混在を防ぎます。

- ロギング / 優先度
  - 起動スクリプトはプロセス優先度を "high" に設定しようとします（psutil を利用）。権限がない場合は警告が出ますが継続します。

- LLM 呼び出し
  - OpenAI API の呼び出しはリトライ・バックオフ・レスポンスバリデーションを実装しています。API キーが未設定の場合、エラーまたはフォールバック（0.0）となる処理があるため、挙動を理解した上で運用してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリ（この README の作成元コードに基づく）:

- src/kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - config.py                       — 環境変数・Settings 管理（.env 自動ロード含む）
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py              — monitoring 用 SQLite スキーマ & 永続化層
    - monitoring_engine.py          — 複数 Monitor を束ねるエンジン
    - system_monitor.py             — システム状態・データ鮮度監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 書き込みユーティリティ
    - (trade_monitor.py, alert_manager.py 等が想定される)
  - execution/                       — Execution 系（order_manager, risk_manager 等）
    - (各コンポーネント、BrokerFactory 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                    — ニュース NLP（OpenAI 呼び出し・スコアリング）
    - regime_detector.py             — レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - data/                            — データファイル（例: monitoring.db, paper_trading.db）を想定
  - logs/                            — ログ出力先（デフォルト）

（実際のリポジトリには上記以外にも多数のモジュール・スクリプトがある想定です）

---

## 追加のヒント / トラブルシュート

- .env の自動読み込み:
  - config.py はプロジェクトルートを `.git` または `pyproject.toml` から推定し、`.env` / `.env.local` を自動で読み込みます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- DuckDB / SQLite のパス:
  - validate_config はデフォルトパスの親ディレクトリが存在するかをチェックし、存在しない場合は警告を出します。起動時に自動作成される場合もありますが、事前に data/ ディレクトリを作成しておくと権限問題を避けられます。

- ログが出力されないまたはファイルが作成されない:
  - LOG_DIR の作成に失敗するとファイルハンドラはスキップされ、コンソール出力のみになります。権限とパスを確認してください。

- OpenAI API の呼び出し:
  - API キーは OPENAI_API_KEY に設定するか、関数呼び出し時に明示的に渡してください。請求やレート制限に注意して運用してください。

---

以上がこのコードベースの README.md 相当の概要です。実際の運用・デプロイ時は、環境固有の設定・監査ログ・エラーハンドリングルール等を付け加えてください。必要であれば README の補足（例: systemd / Supervisor 用のユニットファイル例、Docker 化手順、CI/CD の設定例 等）も作成します。ご希望があれば教えてください。