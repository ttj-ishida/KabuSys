# KabuSys

日本株向けの自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリはトレード実行、監視、リサーチ、ポートフォリオ構築、AI（ニュースセンチメント）等の主要コンポーネントを含みます。

注意: README はソースコードの現状（src/kabusys 以下）に基づいて作成しています。実際の運用前に必ず設定検証（validate_config）を行ってください。

---

## プロジェクト概要

- ExecutionEngine による発注ロジック（本番／ペーパートレード切替）  
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor 等）による稼働監視と Kill Switch（停止スイッチ）  
- 研究用モジュール（ファクター計算、特徴量探索）とポートフォリオ構築ユーティリティ（候補選定・配分・株数算出）  
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）  
- 各種 CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

---

## 主な機能一覧

- 設定管理（.env 自動ロード / Settings クラス）
- 起動ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config, --strict オプションあり）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を用い、paper_trading DB に記録して本番 DB と分離
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor（CPU/メモリ/Disk/データ鮮度/プロセス存在チェック）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（危険時に data/kill.flag を書き込む）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- AI: news_nlp（ニュースを OpenAI でスコアリング）、regime_detector（市場レジーム判定）
- Research: ファクター計算（momentum/value/volatility）、IC 計算、統計サマリ
- Portfolio: 候補選定・重み付け・株数算出・セクター制限・レジーム乗数
- ロギングユーティリティ（統一的な Stream + 日次ローテートファイル出力）
- ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
   - 主な依存: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定検証で YAML 検証を行う場合）

4. .env を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動: .env.example を参考に .env を作成
   - 自動ロード: Settings モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env を自動読み込みします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグは data/ 以下に格納されます。README 内の「重要な環境変数」を参照してパスを確認してください。

---

## 使い方（主要コマンド例）

- .env ウィザード（対話）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（実行エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV による（例: export KABUSYS_ENV=paper_trading）

  挙動:
  - paper_trading モードでは MockBrokerClient が使用され、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag が存在する場合はエンジンを起動しません。
  - 停止させるには data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）を用います。
  - 実行時に PID ファイル（デフォルト data/execution.pid）を書きます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能。

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数、または関数引数で指定）。
  - 例: kabusys.ai.news_nlp.score_news(conn, target_date, api_key="...")

---

## 重要な環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト logs/）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）（デフォルト "instant"）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1: クリア、0: クリアしない。production では 0 推奨）

---

## 停止・Kill Switch の扱い

- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag（または設定で指定したパス）を監視し、存在すれば安全停止します。
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件を検出した場合に data/kill.flag を作成します。ExecutionEngine は起動時に kill.flag を検出すると起動しない/停止するよう設計されています。
- Kill flag を手動で削除する場合はファイルを削除してください（運用上の注意: 本番で自動クリアを有効にするのは危険です）。

---

## ロギング

- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - stdout（StreamHandler）に出力し、ファイルは日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に保存します。
  - デフォルトで 30 日分のローテーションを保持します。
  - LOG_LEVEL / LOG_DIR 環境変数で上書き可能。
  - ログディレクトリ作成に失敗した場合はコンソール（stdout）のみで継続します。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要コンポーネントを抜粋した構成です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数読み込み・Settings クラス（デフォルト値・バリデーション）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/  (発注エンジン関連: ExecutionEngine, BrokerClientFactory, OrderManager, RiskManager, Reconciler, 等)
  - monitoring/
    - monitoring_db.py — SQLite を用いた監視ログ永続化層
    - system_monitor.py — システム状態 / データ鮮度チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （滞留注文・約定異常などの）注文監視（コード参照）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — Kill Switch 実装（flag ファイル管理）
    - alert_manager.py — アラート送信管理（LINE など）（参照されるが詳細は実装を参照）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け（等金額・スコア加重）
    - position_sizing.py — 株数計算・資金制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）スコアリング
    - regime_detector.py — マクロ + ETF MA 合成によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートを生成する CLI

（実際のファイル全体はリポジトリを参照してください。ここに記載していない補助モジュールや詳細実装があります。）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env の管理・シークレット保持には十分注意してください。 .env は絶対に Git にコミットしないでください。
- validate_config を CI / デプロイ前に実行して設定不備を検出してください（--strict オプション推奨）。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番で有効にしないでください（安全上のリスク）。
- AI 機能はネットワーク依存・コスト発生・レイテンシがあるため、重要な意思決定に直接依存させる場合は慎重に運用してください。
- ログ・DB ファイルの容量管理とバックアップポリシーを用意してください（DuckDB / SQLite / logs）。

---

もし README に追加してほしいコマンドや、各モジュールの詳細な API ドキュメント（引数・戻り値・例）等があれば知らせてください。必要に応じて追記します。