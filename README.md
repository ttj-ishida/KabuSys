# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリおよび実行／監視スクリプト群です。  
本リポジトリには、戦略（シグナル生成・銘柄選定・配分）、ポジションサイズ計算、リスク監視、ExecutionEngine起動スクリプト、監視エンジン（Monitoring）など、実運用を想定した機能群が含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成（主要ファイル一覧）
- 主要環境変数（抜粋）
- 補足・運用メモ

---

## プロジェクト概要

KabuSys は「日本株自動売買システム」のコアライブラリ群です。  
主な目的は次のとおりです。

- 戦略（ファクター計算・特徴量探索）とポートフォリオ構築ロジックの提供
- Execution（発注）とそれを支えるユーティリティの提供（本番/ペーパートレード対応）
- システム監視（プロセス・データ鮮度・取引ログ等）と Kill Switch による安全措置
- News の NLP を用いたセンチメント評価や市場レジーム判定のサポート
- DuckDB / SQLite を用いたデータアクセスと永続化

設計方針としては「フェイルセーフ」「ルックアヘッドバイアス回避」「外部 API 呼び出しの抽象化（テスト容易性）」を重視しています。

---

## 機能一覧

主要な機能（抜粋）:

- Execution
  - run_execution.py: ExecutionEngine の起動スクリプト（本番/ペーパー分離）
  - ブローカークライアントを抽象化（BrokerClientFactory）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等

- Monitoring
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - MonitoringEngine: System / Trade / Risk モニタを束ねる
  - MonitoringDB: SQLite に監視ログを保持（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch: フラグファイルによる Execution 停止
  - AlertManager（通知用フック：LINE 等）

- ポートフォリオ・ポジション管理
  - portfolio.portfolio_builder: 候補選定・重み計算（等分・スコア加重）
  - portfolio.position_sizing: 発注株数計算（リスクベース等）、単元丸め、aggregate cap
  - portfolio.risk_adjustment: セクターキャップ、レジーム乗数

- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - research.feature_exploration: 将来リターン、IC 計算、統計サマリ

- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM でセンチメント評価し ai_scores に書き込む
  - ai.regime_detector: ETF MA とマクロニュースを合成して市場レジームを判定

- ツール
  - tools.paper_verification_report: Paper Trading DB に対する性能検証レポート生成

- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定（環境変数・config ファイル）検証

- ユーティリティ
  - utils.logging_setup: 統一的ログ設定（stdout + 日次ファイルローテーション）
  - utils.process_priority: プロセス優先度・CPU affinity 設定

---

## セットアップ手順

以下は一般的なセットアップ手順（Linux / macOS / Windows 共通）。環境や運用ポリシーに合わせて調整してください。

1. Python 環境（推奨: 3.10+）
   - pyproject.toml 等がある前提ですが、仮想環境を作成してください。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt がない場合は上記を目安にしてください）

3. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作る（例は後述）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合は:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - ログや DB のデフォルトはプロジェクト直下の data/, logs/
   - 必要に応じて作成:
     - mkdir -p data logs

6. DB 準備
   - 初回起動時に monitoring のテーブルは初期化されます（init_monitoring_db が実行されます）。
   - DuckDB ファイルは解析用に利用します（デフォルト: data/kabusys.duckdb）。

---

## 使い方（起動例・主要コマンド）

- 環境変数読み込みの前提:
  - .env をプロジェクトルート（.git または pyproject.toml のある階層）に置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid が書かれます。停止は data/stop_requested.flag を作成するか、Kill Switch による kill.flag を利用します。

- Monitoring 起動（SystemMonitor のポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（例）
  - OpenAI API を使う機能は OPENAI_API_KEY を環境変数で設定する必要があります。
  - 例（ニューススコア）: 呼び出しはライブラリ API を通じて行います（score_news 等）。

---

## デフォルトの重要ファイル / パス

- DuckDB: data/kabusys.duckdb （Settings.duckdb_path）
- SQLite（監視）: data/monitoring.db （Settings.sqlite_path）
- Paper Trading SQLite: data/paper_trading.db （PAPER_TRADING_SQLITE_PATH）
- PID / flag:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- ログ: logs/<app_name>.log（日次ローテーション、デフォルト logs/）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルとモジュールの一覧です（完全版ではありません）。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite 監視データ層（テーブル定義・CRUD）
    - system_monitor.py          — システム状態 / データ鮮度監視
    - trade_monitor.py           — （取引ログ監視: ファイル内の実装参照）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みユーティリティ
    - monitoring_engine.py       — 各モニタを束ねる実行エンジン
    - alert_manager.py           — 通知（LINE 等）インターフェース
  - execution/
    - execution_engine.py        — ExecutionEngine 実装
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み
    - position_sizing.py         — 発注株数計算
    - risk_adjustment.py         — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py         — Momentum / Volatility / Value 等
    - feature_exploration.py     — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                — ニュース→LLMセンチメント
    - regime_detector.py         — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py

（上記に加えて、strategy / data / research 等サブモジュールが存在します）

---

## 主要環境変数（抜粋）

Settings で参照される主な環境変数（.env に設定）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB。デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- PAPER_FILL_MODE（paper_trading の MockBrokerClient の振る舞い: instant|partial|never|reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）

簡易 .env 例（.env は絶対にリポジトリにコミットしないでください）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 補足・運用メモ

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 を推奨します。
- run_execution は KABUSYS_ENV によって本番 DB とペーパートレード DB を分離します。paper_trading 時は PAPER_TRADING_SQLITE_PATH を利用。
- Monitoring は Settings.env に依存せず、常に本番 sqlite_path を使用して監視ログを記録します（監視が本番 DB を見るため）。
- AI（OpenAI）周りは API エラー時に堅牢に動作するようリトライとフォールバック処理がありますが、API キーとコスト管理は運用上の注意が必要です。
- ロギングは utils.logging_setup.setup_logging を通して統一して下さい。ログ出力先は logs/<app_name>.log（デフォルト / 日次ローテーション）です。
- テストを書く際は、OpenAI 呼び出し部分やファイル I/O はモック化して行うことを推奨します（コードにもモック差替えを想定した関数設計が含まれています）。

---

必要であれば README に「インストール用 requirements.txt の推奨内容」「運用用 systemd / Supervisor の Unit サンプル」「より詳細なアーキテクチャ図」などを追記できます。どの情報が必要か教えてください。