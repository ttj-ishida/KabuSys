# KabuSys

日本株自動売買システムの一部である Python コードベースの README（日本語）

注意: この README は src/kabusys 以下のコードを元に作成しています。実行前に .env を作成し、必須環境変数を適切に設定してください（.env を絶対にリポジトリへコミットしないでください）。

---

## 概要

KabuSys は日本株向けの自動売買／リサーチ／監視を行うモジュール群です。本リポジトリには以下の主要機能を実装したモジュールが含まれています。

- ExecutionEngine（発注エンジン）と Execution 用ユーティリティ
- Monitoring（システム／発注／リスク監視）と Kill Switch
- Portfolio 構築（候補選定・重み付け・ポジションサイジング）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、レポート生成 等）

コード設計上のポイント:
- 設定は .env または環境変数から読み込む（自動ロード機能あり）
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI を使った NLP 処理は冗長なエラー処理・リトライを備える
- ロギングは統一ユーティリティで stdout + 日次ローテートを行う

---

## 機能一覧（抜粋）

- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker を選択）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等の実装（発注・リスク・整合性処理）
- 監視系
  - run_monitoring.py: SystemMonitor を定期実行するポーリングスクリプト
  - MonitoringDB: SQLite ベースの監視ログ永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - MONITOR_POLL_INTERVAL によるポーリング周期変更
- ポートフォリオ構築
  - 候補選定、等重・スコア重み計算、セクター上限適用、ポジションサイズ計算（単元株単位）
- リサーチ
  - ファクター（モメンタム、ボラティリティ、バリュー）計算（DuckDB 使用）
  - 将来リターン、IC（Information Coefficient）、統計要約
- AI (OpenAI)
  - news_nlp: ニュース記事を集約して LLM により銘柄ごとのセンチメントを算出し DB へ保存
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定
- ユーティリティ / ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈で `X | None` などを使用しているため）
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- 標準ライブラリの sqlite3 を使用

インストール例（venv 推奨）:
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil openai PyYAML

（このリポジトリに requirements.txt がない場合は上記を手動でインストールしてください）

---

## セットアップ手順

1. プロジェクトルートへ移動（pyproject.toml/.git を基準に自動検出）
2. .env を作成
   - 手動で作るか、ウィザードを使う:
     - python -m kabusys.config_setup
   - 最低限設定が必要なキー（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - (paper_trading 使用時) PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=...（AI 機能を使う場合）
   - .env の生成後、設定の検証:
     - python -m kabusys.validate_config
     - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict
3. ディレクトリ作成（必要なら）
   - data/ と logs/ が必要
   - ログディレクトリは自動作成されますが、権限の設定に注意
4. DB 初期化
   - 実行スクリプトが起動時に monitoring DB のテーブルを冪等に作成します（init_monitoring_db）
   - DuckDB は指定した path にファイルを作成します

注意:
- KABUSYS_ENV が `paper_trading` のときは MockBroker を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に記録されます。本番 DB と完全分離されています。
- KABUSYS_ENV が `live` の場合は本番動作になります。LINE 通知などの設定を必ず確認してください（validate_config にも注意喚起あり）。

---

## 使い方（主要コマンド）

すべてのスクリプトはパッケージモジュールとして実行できます（プロジェクトルートで実行）。

- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - 概要: Engine を起動して発注セッションを走らせます。停止は data/stop_requested.flag を作るか、PID 連携で制御します。
  - Paper trading の場合: KABUSYS_ENV=paper_trading を設定してから起動（専用 DB に記録）
  - 実行中に停止フラグ file data/stop_requested.flag が存在すると優雅に停止します。

- 監視ループ
  - python -m kabusys.run_monitoring
  - 概要: SystemMonitor をポーリングし監視ログを SQLite に記録します。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（KABUSYS_ENV に依らず）を使用します。
  - 停止は data/stop_requested.flag の作成で行います。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict で警告も FAIL 扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能

- AI 関連（ライブラリアクセス用 API）
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - 注意: OPENAI_API_KEY を環境変数または引数で渡す必要があります

ログ出力:
- ログは stdout と logs/<app_name>.log（日次ローテート）に出力されます。
- LOG_LEVEL / LOG_DIR の環境変数で調整可能。

監視・停止フラグ関連:
- data/kill.flag — KillSwitch が書き込む（ExecutionEngine 停止用の永続フラグ）
- data/stop_requested.flag — run_monitoring/run_execution が監視する一時停止フラグ
- data/execution.pid — ExecutionEngine が PID を書き込む場所（デフォルト）

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能が必要な場合）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading のモック約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）

注意: .env の自動読み込みはプロジェクトルートが検出できる場合に行われ、OS 環境変数が優先されます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys
- __init__.py
- config.py                  — 環境変数 / Settings
- config_setup.py            — .env ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

subpackages / モジュール
- execution/                 — 発注エンジン周り（OrderManager, ExecutionEngine 等）
- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
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
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

サポートファイル・ディレクトリ（プロジェクトルート想定）
- .env (ユーザが作成)
- data/ (SQLite ファイル・フラグファイルなど)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 時)
  - kill.flag, stop_requested.flag, execution.pid …
- logs/
  - execution.log, monitoring.log, ...（日次ローテーション）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では必ず .env の設定を検証してください（LINE 通知設定等）。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番環境では危険です（Kill Switch を無効化する恐れ）。production では 0 を推奨します。
- OpenAI API 呼び出しは課金対象です。API キー・呼び出し回数に注意してください。
- paper_trading モードは本番 DB と完全分離設計ですが、DB パスの設定ミスに注意してください。
- ログディレクトリや DB パスの親ディレクトリが存在しない場合は自動作成されることがありますが、権限設定に注意してください。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの概要説明です。各モジュールの詳細な使い方・設計仕様は該当ソース（doc/ またはモジュールの docstring）を参照してください。問題や改善点があればソースコードのコメントや docstring を参照して実装方針に従ってください。