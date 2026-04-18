# KabuSys

KabuSys は日本株向けの自動売買システムのコードベースです。  
ポートフォリオ構築、ポジションサイジング、監視（Monitoring）、注文実行（Execution）、AI（ニュース NLP / レジーム判定）、および各種ユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- 目的: 日本株の自動売買を安全に運用するためのフレームワーク。戦略（ファクター計算） → ポートフォリオ構築 → 注文生成 → 実行 → 監視 の流れをサポートする。
- データストレージ: DuckDB（分析用）・SQLite（監視・発注ログ・ペーパートレード用）を使用。
- 実行モード:
  - `development`：ローカル開発・検証向け（発注なしなど）
  - `paper_trading`：ペーパートレード（実際の売買は行わず MockBroker を使用）
  - `live`：本番（実際に発注）
- Python 3.10+ を想定（型記法に `|` を使用）。

---

## 主な機能一覧

- 戦略 / リサーチ
  - factor_research: モメンタム・バリュー・ボラティリティなどのファクター計算（DuckDB ベース）
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）等の統計解析ユーティリティ
- ポートフォリオ構築
  - 銘柄選定（スコア順）、等配分/スコア加重、セクター制限、レジーム乗数の適用
  - ポジションサイズ計算（ロット丸め、リスクベース配分、aggregate cap 対応）
- 実行（Execution）
  - ExecutionEngine、OrderManager、RiskManager 等（kabuステーション API または MockBroker）
  - Paper trading を本番 DB と分離（`data/paper_trading.db` がデフォルト）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（閾値超過時に `data/kill.flag` を書き込み、Execution を停止）
- AI 機能
  - news_nlp: OpenAI を用いたニュースセンチメント評価（銘柄別スコア）
  - regime_detector: ETF（1321）の MA とマクロニュースを使った市場レジーム判定
- ユーティリティ
  - config_setup: 対話式 `.env` 作成ウィザード
  - validate_config: 起動前チェック（必須環境変数や config/*.yaml の検証）
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（開発環境）

※ 下記は一般的な手順例です。環境に応じて適宜調整してください。

1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限の依存（例）:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - pyyaml  （validate_config で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそちらを利用）

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または `.env.example` を参照して `.env` を作成（リポジトリに例ファイルがある場合）
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨設定:
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - LOG_DIR（ファイルログ格納先、デフォルト: logs/）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳密にエラー扱いにする: python -m kabusys.validate_config --strict

6. データディレクトリ・権限
   - デフォルト DB / ログ保存先（data/, logs/）への書き込み権限を確認

---

## 使い方（起動 / コマンド）

各モジュールはパッケージモードで実行できます（ルートディレクトリで実行）。

- 実行（Execution）エンジン起動
  - python -m kabusys.run_execution
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、ペーパートレード DB（デフォルト: data/paper_trading.db）へ記録します。
    - 起動時に `data/stop_requested.flag` が存在すると起動を中止します（停止フラグ）。

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化します。
  - 監視ループ内で `data/stop_requested.flag` の存在をチェックし、検知するとループを終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に `.env` を作成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI / レジーム判定・ニューススコアリング（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも `OPENAI_API_KEY` を環境変数か引数で指定する必要があります。

---

## 環境変数一覧（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / 動作モード
  - KABUSYS_ENV: development | paper_trading | live

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch フラグパス（デフォルト: data/kill.flag）

- AI / OpenAI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

- 実行設定
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - LOG_DIR: ログファイル保存ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## 停止 / Kill Switch

- Stop フラグ（強制停止 / 起動抑止）
  - data/stop_requested.flag
    - run_execution.py / run_monitoring.py は起動時およびループ中にこのファイルの存在をチェックします。
    - 存在すると起動を抑止／ループ終了します。

- Kill Switch（監視→実行停止）
  - KillSwitch は監視結果（ドローダウン・ポジション上限）によって `data/kill.flag` を書き込みます。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定に応じて kill.flag を削除するか判断します（設定に注意。production では自動クリアを無効にすること推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys/` 以下の主要なディレクトリとファイルです（抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコア
    - regime_detector.py     — 市場レジーム判定
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・DB 操作ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity
  - data/                    — 実行時に生成される想定の格納場所（DB・PID・flag 等）
  - logs/                    — ログファイル（デフォルト）

---

## 運用上の注意

- 本番運用時は `KABUSYS_ENV=live` を設定します。validate_config は `live` の場合に追加の警告を行います（LINE 通知設定など）。
- `.env` ファイルは機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- 実行ユーザーに `data/` と `logs/` の書き込み権限があることを確認してください。
- AI 機能を使う場合、OpenAI の利用料金・レート制限に注意してください。Retry / backoff ロジックは実装されていますがコストはかかります。
- Paper Trading と本番 DB は分離されています（paper_trading モード時は専用 SQLite を使用）。本番 DB を汚さない運用が可能です。

---

## よく使うコマンドまとめ

- 仮想環境作成 / 有効化
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージ依存のインストール（例）
  - pip install duckdb psutil openai pyyaml

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれている内容で不足があれば、特に以下について追記できます:
- 実際の ExecutionEngine の起動・停止手順（systemd / supervisor / cron 用のサンプル unit）
- broker の具体的な設定方法（kabuステーション API の接続詳細）
- CI / テストの実行方法
- config/*.yaml の内容説明（各設定項目の詳細）

必要であればどれを優先して追加するか教えてください。