# KabuSys

日本株自動売買システムのパッケージ（ドキュメント用 README）。本 README はリポジトリ内の主要スクリプト・モジュールから仕様をまとめたものです。

注意: .env は機密情報を含みます。絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・モニタリングを行うための統合的な Python パッケージです。主な目的は以下の通りです。

- 戦略に基づいた銘柄選定・配分（portfolio モジュール）
- 発注・注文管理・リスク制御を行う ExecutionEngine（execution）
- システム稼働状況・注文ログ・リスク監視（monitoring）
- DuckDB を用いたファクター計算・リサーチ（research）
- LLM を用いたニュースセンチメント・レジーム判定（ai）
- ユーティリティ（ロギング、プロセス優先度設定など）

本リポジトリは「本番（live）」「ペーパートレード（paper_trading）」「開発（development）」の3つの実行環境を想定しています（環境変数 `KABUSYS_ENV` で切替）。

---

## 機能一覧

- Execution
  - 実際のブローカークライアント or Mock クライアント（`KABUSYS_ENV=paper_trading` の場合）
  - 発注管理、注文履歴の永続化（SQLite）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
- Monitoring
  - システムリソース（CPU / メモリ / ディスク）の定期監視
  - データ鮮度チェック（price データの更新確認）
  - トレードログ監視・滞留注文検出
  - Kill Switch：条件を満たすと `data/kill.flag` を書き、Execution を停止
- Portfolio
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算
  - セクター集中制限、レジームに応じた資金乗数
- Research
  - モメンタム / バリュー / ボラティリティファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリー
- AI
  - ニュースの LLM センチメント評価（OpenAI）
  - マクロセンチメントと ETF MA を組合せた市場レジーム判定
  - API 呼び出しはリトライ / バックオフを実装
- ツール
  - ペーパートレードの検証レポート出力（`tools/paper_verification_report.py`）
  - 対話式の .env 作成ウィザード（`config_setup.py`）
  - 起動前の設定検証 CLI（`validate_config.py`）

---

## 前提（依存関係）

最低限必要なパッケージ（代表例）:

- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml（`validate_config.py` の YAML 検証を行う場合に必要）

インストール例:

pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt が無い場合は上記を個別にインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone … && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 各種 API トークンや DB パス、`KABUSYS_ENV` を設定できます。
     - 重要項目（例）:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
       - KABUSYS_ENV: development | paper_trading | live
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
       - OPENAI_API_KEY（AI 機能を使う場合）
     - .env は必ず Git 管理から除外してください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. ログディレクトリ・データディレクトリ
   - デフォルトで `logs/` と `data/` を使用します。`logs/` はログ出力、`data/` は DB やフラグファイルを配置します。
   - `data/` 配下のファイル:
     - data/monitoring.db（監視ログ）
     - data/paper_trading.db（ペーパートレード用 DB）
     - data/kabusys.duckdb（DuckDB データベース）
     - data/kill.flag（Kill Switch 用フラグ）
     - data/stop_requested.flag（プロセスシャットダウン用フラグ）
     - data/execution.pid（Execution の PID ファイル）

---

## 使い方（実行例）

- Execution（エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い、`data/paper_trading.db` に記録（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動しません。
    - 実行中に `data/stop_requested.flag` を作成するとエンジン停止をリクエストできます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番用の sqlite_path（Settings.sqlite_path）を使用して監視 DB を初期化します。
  - 停止: `data/stop_requested.flag` を作成するか、Ctrl+C。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告を FAIL 扱いにできます

- AI モジュール（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様にキーが必要

注意: AI 機能は `openai` クライアントを使用し、429・タイムアウト・5xx に対するリトライを備えていますが、API キーが未設定の場合は例外が発生します。

---

## 主要な環境変数（一覧・説明）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に `data/kill.flag` を自動クリアするか（0/1、本番では 0 推奨）

重要: 本番（live）では `KILL_FLAG_CLEAR_ON_START=1` は危険です。Kill Switch を誤ってクリアして本番発注を続けないよう注意してください。

---

## 動作の停止 / Kill Switch

- Execution 停止
  - `data/stop_requested.flag` を作成すると監視・実行側が検知して安全停止します（両スクリプトで利用）。
- Kill Switch（自動停止トリガ）
  - RiskMonitor 等の判定によって `data/kill.flag` が書き込まれます。Execution はこのフラグを参照して停止できます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動で削除しますが、本番では推奨されません。

---

## DB とログ

- デフォルトのファイルパス
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- ログ
  - デフォルト出力先: logs/
  - ログはアプリ名別（例: logs/execution.log, logs/monitoring.log）に日次ローテーションで保存されます（30 日保持）。

---

## ディレクトリ構成（主なファイル / モジュール）

リポジトリの主要構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込み・Settings
  - config_setup.py — .env 作成ウィザード（CLI）
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル初期化・CRUD）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信 / 実装あり）
  - execution/
    - execution_engine.py — ExecutionEngine（発注セッション）
    - broker_factory.py — BrokerClient の生成（モック含む）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定、スケーリング、丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計機能
  - data/ （実行時に作成）
    - monitor / DB / flag / pid 等
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - など

---

## 開発時のヒント / 注意点

- .env の自動読み込み
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` を自動読み込みします。テスト等で自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は起動時に必要テーブルを冪等に作成し、既存テーブルにカラムがない場合は ALTER TABLE による簡易マイグレーションを行います。
- ロギング
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出して統一されたログ出力方式を使用します。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を最初に呼び出し、重要なプロセス優先度を設定しようとします。権限不足等で失敗した場合は警告を出してスキップします。
- 本番運用のガード
  - `validate_config.py` は `KABUSYS_ENV=live` のときに LINE 通知設定や `KILL_FLAG_CLEAR_ON_START` の警告を行います。必ず起動前に設定内容を確認してください。

---

## よくある操作例

- 開発用: ペーパートレードで起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視のみ起動（60 秒間隔）
  - python -m kabusys.run_monitoring
- 監視の間隔を 30 秒に変更
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート（DB 指定）
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

---

必要があれば README に具体的な .env のサンプル（機密情報を除く）や、よく使う CLI の例、開発フロー（ユニットテスト、CI）なども追記します。どの部分を詳細化したいか教えてください。