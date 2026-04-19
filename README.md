# KabuSys README

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）。

以下はこのコードベースの概要、機能、セットアップ方法、実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの骨格を提供する Python パッケージです。  
主な責務は次のとおりです：

- 市場データ（DuckDB）を用いたリサーチ・ファクター計算
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注の管理、ブローカークライアント抽象化）
- 監視（System / Trade / Risk のポーリングとログ記録）
- Paper Trading 用の検証レポート生成
- ニュースの NLP によるセンチメント評価・レジーム判定（OpenAI 利用オプション）

本リポジトリはモジュール単位に分かれており、開発・テスト・ペーパートレード・本番（live）を環境変数で切り替えられる設計です。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成）: config_setup.py
- 設定検証 CLI（.env と config/*.yaml の整合性チェック）: validate_config.py
- ExecutionEngine 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、Paper 用 DB（data/paper_trading.db）に記録
- Monitoring 起動スクリプト: run_monitoring.py
  - ポーリングで SystemMonitor を実行し監視情報を永続化
  - 環境変数 MONITOR_POLL_INTERVAL で間隔上書き可（デフォルト 60 秒）
- 監視・リスク管理：
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine
  - kill.flag により ExecutionEngine を停止させる Kill Switch 機構
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等重・スコア重み付け、単元株丸め、セクターキャップ、レジーム乗数
- 研究（research）モジュール
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC、統計サマリー
- AI 関連
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores テーブルへ書き込み）
  - regime_detector: MA200 とマクロ NLP を使った市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率や約定成功率など）

---

## 必要条件（主な環境変数）

必須（最低限設定が必要）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨：
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` は MockBroker を使用し paper DB に分離
  - `live` は実取引モード（慎重に設定）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（`instant|partial|never|reject`。デフォルト `instant`）
- OPENAI_API_KEY: AI 機能を使う際に必要（news_nlp / regime_detector）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

備考:
- .env を使って設定を管理できます（自動ロード機能あり）。.env は絶対にコミットしないでください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして Python 仮想環境を作る：
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -r requirements.txt   # 存在する場合
   ```
   ※ DuckDB、psutil、openai 等が必要な箇所があります。requirements.txt がない場合は必要なパッケージを個別にインストールしてください。

2. .env の作成（対話式ウィザード推奨）：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで入力後、.env が作成されます。

3. 設定の検証：
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL としたい場合：
   ```
   python -m kabusys.validate_config --strict
   ```

4. （任意）データディレクトリ作成：
   ```
   mkdir -p data logs
   ```

---

## 実行方法（主要スクリプト）

- ExecutionEngine（発注エンジン）を起動：
  ```
  python -m kabusys.run_execution
  ```
  挙動：
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し paper DB（PAPER_TRADING_SQLITE_PATH）に結果を記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しない。
  - 実行中に data/stop_requested.flag を作るとスレッド停止をトリガー。
  - PID ファイル: data/execution.pid（Settings の pid_file_path で変更可能）。

- Monitoring（監視ループ）を起動：
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数でポーリング間隔を上書き：
  ```
  export MONITOR_POLL_INTERVAL=30  # 30 秒毎に監視
  python -m kabusys.run_monitoring
  ```
  挙動：
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境に依存しない）。
  - 監視ループは data/stop_requested.flag を検知すると終了する。

- Paper Trading 検証レポート生成（ツール）：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB 指定（デフォルトは data/paper_trading.db）：
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出すAPI）：
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要。失敗時はフェイルセーフ（多くのケースで 0.0 にフォールバック）。

---

## 停止・Kill フラグ

- data/stop_requested.flag
  - run_execution と run_monitoring がループ継続をチェックする停止フラグ。
  - 手動でファイル作成すると両スクリプトが検知して終了または停止処理を実行します。

- data/kill.flag
  - KillSwitch がトリガー条件（大きなドローダウンやポジション上限超過）を満たした場合に書き込まれるファイル。
  - ExecutionEngine はこのファイルの存在を起点に安全に停止される仕組みです。
  - Settings の KILL_FLAG_CLEAR_ON_START が `1` の場合、起動時に自動クリアされます（本番では `0` 推奨）。

---

## ログ

- setup_logging() を経由して設定されます（kabusys.utils.logging_setup）。
- デフォルトのログディレクトリ: logs/
- アプリケーション別ログファイル:
  - logs/execution.log
  - logs/monitoring.log
  - など
- ログはコンソール出力（stdout）と日次ローテートファイル（TimedRotatingFileHandler）に出力され、30 日分保持されます。

---

## データベース（デフォルトパス）

- DuckDB: data/kabusys.duckdb (Settings.duckdb_path)
- 監視 SQLite: data/monitoring.db (Settings.sqlite_path)
- Paper Trading SQLite: data/paper_trading.db (Settings.paper_sqlite_path)

monitoring_db モジュールは起動時に必要なテーブルを作成（冪等）します。マイグレーション（カラム追加）も含まれます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・ディレクトリです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (実装あり)
    - monitoring_engine.py
  - execution/
    - broker_factory.py        (ブローカ抽象)
    - execution_engine.py      (メイン発注エンジン)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（リポジトリ内のコメントや docstring を参照すると各モジュールの詳細や設計方針が確認できます）

---

## 開発時の注意点・設計上のポイント

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- run_* スクリプトはプロセス優先度を高めに設定します（psutil を使用）。実行環境によっては権限が不足して警告が出ますが実行は継続します。
- AI 機能は OpenAI SDK に依存します。API の失敗や結果パースエラーは基本的にフェイルセーフ（処理をスキップして継続）で設計されています。
- Paper Trading は本番 DB と完全分離されるよう設計されています（Settings.is_paper フラグで制御）。

---

## よく使うコマンドまとめ

- .env 作成ウィザード：
  ```
  python -m kabusys.config_setup
  ```

- 設定検証：
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動：
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動（30秒間隔例）：
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコード内の docstring と設計コメントに基づいて作成しています。各モジュールの詳細や追加設定については該当ソース（src/kabusys 以下）の docstring を参照してください。追加で README に追記したい内容（例: デプロイ手順、CI 設定、インストール可能パッケージ一覧など）があれば教えてください。