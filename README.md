# KabuSys

日本株向け自動売買システムの参照実装 (KabuSys)。  
このリポジトリはトレーディングエンジン、監視機構、ポートフォリオ構築、リサーチ用ユーティリティ、LLM を用いたニュース NLP 等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを想定したモジュール群です。主な要素は次の通りです。

- ExecutionEngine：発注ロジック・注文管理・リスク管理の実行（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文ログ・リスク監視、Kill Switch によるエンジン停止
- Portfolio：銘柄選定、重み付け、ポジションサイズ算出（純粋関数群）
- Research：DuckDB 上でのファクター計算・特徴量解析ユーティリティ
- AI：OpenAI を使ったニュースセンチメント評価、レジーム判定
- Tools：ペーパートレード検証レポート生成などの補助スクリプト
- 設定管理：対話式 .env ウィザードと設定検証 CLI

設計方針として、データベース（SQLite / DuckDB）を用いた永続化、環境変数による構成、外部 API 呼び出し（kabuステーション, J-Quants, OpenAI）を抽象化して扱えるようにしています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker/本物を選択）
  - run_monitoring.py：SystemMonitor のポーリングループを起動
- 設定管理
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：環境変数・config/*.yaml の静的チェック CLI
- 監視 / 安全装置
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch による flag ファイルでの外部停止指示
  - ログ・アラートの一元管理（logging_setup）
- ポートフォリオ構築
  - 銘柄選定、スコア重み付け、等分配、リスクベースのポジションサイズ計算
  - セクター上限適用、レジーム乗数
- リサーチ
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI（任意）
  - ニュースのセンチメントスコア生成（OpenAI）
  - マクロ／ETF ベースの市場レジーム判定（OpenAI と組み合わせ）
- ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

---

## 必須要件（概要）

- Python 3.10+
- 推奨ライブラリ（抜粋）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML の検証を行う場合）
- OS: Windows / Linux / macOS（プロセス優先度設定や CPU affinity は OS により制限あり）

依存パッケージはプロジェクトが配布する requirements.txt があればそれを使用してください。無い場合は上記ライブラリを個別にインストールします。

例:
pip install duckdb psutil openai pyyaml

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（必須に準じる or 実行時に使用）:
- KABUSYS_ENV: execution 環境 ("development" / "paper_trading" / "live")。デフォルトは development
  - paper_trading の場合、MockBroker を使い、専用の paper DB に記録します
- SQLITE_PATH: 監視 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（paper_trading 環境で使用, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使用する AI 機能で必要
- LOG_LEVEL: ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（"instant" | "partial" | "never" | "reject"）

その他は Settings クラス（kabusys.config）を参照してください。

注意:
- .env ファイルは生成・編集可能（config_setup.py）。絶対に Git 等にはコミットしないでください。

---

## セットアップ手順（簡易）

1. レポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt  （ファイルがある場合）
   - または個別に: pip install duckdb psutil openai pyyaml

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザード完了後、.env がプロジェクトルートに保存されます

4. 設定検証（必須項目やパス等のチェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付けます

5. 初回起動前に logs/ や data/ ディレクトリの権限確認（自動作成されますが権限エラーに注意）

---

## 実行方法（代表的なコマンド）

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 注: KABUSYS_ENV=paper_trading の場合、MockBroker が使われ data/paper_trading.db に記録されます

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）

- .env ウィザード（再掲）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

## 停止 / Kill Switch / フラグファイル

- run_monitoring.py / run_execution.py はプロジェクトの data ディレクトリに置くフラグファイルを監視します。
  - stop_requested.flag: 監視ループやエンジン起動ループを安全に終了させるために使用
    - run_monitoring/run_execution は data/stop_requested.flag の存在を検知するとループを終了します
  - kill.flag: KillSwitch により書き込まれ、ExecutionEngine に対して停止指示を行うために使用
    - KillSwitch は RiskMonitor 等の判定によりこのファイルを生成します
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番では推奨しません）

---

## ログ・データベースについて

- ログ:
  - デフォルト出力先: logs/
  - 各アプリケーションは logs/<app_name>.log（日次ローテート）を出力します
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で決定

- データベース:
  - DuckDB（分析用）: デフォルト data/kabusys.duckdb
  - SQLite（監視 / トレードログ）: data/monitoring.db
  - ペーパートレード専用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時使用）

起動スクリプトは必要に応じて DB のスキーマを初期化（冪等）します。

---

## 主要モジュールと役割（抜粋）

- kabusys.config: 環境変数読み込み・Settings クラス
- kabusys.config_setup: .env 対話式ウィザード
- kabusys.validate_config: 設定検証 CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリング起動スクリプト
- kabusys.monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / monitoring DB
- kabusys.execution: 発注・オーダー管理・リスク管理（Engine）
- kabusys.portfolio: 銘柄選定・重み付け・ポジションサイズ計算
- kabusys.research: ファクター計算・特徴量探索
- kabusys.ai: news_nlp（ニュース NLP）、regime_detector（市場レジーム判定）
- kabusys.utils: logging_setup, process_priority などのユーティリティ

---

## ディレクトリ構成

（本 README 作成時点での主要ファイル群）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/              # ExecutionEngine 関連（broker_factory 等）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (runtime 用)
      - monitoring.db (デフォルト SQLite)
      - paper_trading.db (ペーパートレード用)
      - kabusys.duckdb (デフォルト DuckDB)
      - execution.pid, stop_requested.flag, kill.flag など

---

## 開発上の注意事項

- .env は絶対にリポジトリにコミットしないでください（機密情報含む）。
- 本番（KABUSYS_ENV=live）では特に LINE 通知設定や kill flag の取り扱いを慎重に確認してください（validate_config で警告が出ます）。
- OpenAI を使う処理は API 呼び出し・レート制限・料金が発生します。テスト時はモックを使うことを推奨します（モジュール内の API 呼び出し関数はテスト用に差し替え可能に設計されています）。
- Analytics / research 系は DuckDB に依存するためデータ投入（prices_daily / raw_financials / raw_news 等）が必要です。

---

## よく使うコマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はコードベースの現状に基づく概要です。実運用時は config/*.yaml（存在する場合）や各モジュールのドキュメント、運用手順書を参照してください。必要であればセクションを追加・展開します。