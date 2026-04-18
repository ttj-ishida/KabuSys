# KabuSys

日本株向け自動売買システムのコアライブラリ群（実行エンジン / 監視 / リサーチ / ポートフォリオ構築 / AI 補助など）。

このリポジトリは、取引ロジック・監視・レポート生成・AI を使ったニュースセンチメント判定等のユーティリティ群を含みます。パッケージは Python モジュールとして提供され、コマンドラインから各種スクリプトを起動できます。

---

## 概要（Project概要）

- 名称: KabuSys
- 目的: 日本株の自動売買を支援するための実行エンジン、監視、ポートフォリオ構築、ファクター算出、ニュース NLP（LLM）スコアリング等の機能を提供する。
- 主な実装言語: Python
- 主な外部依存: duckdb, psutil, openai, （任意）PyYAML

---

## 機能一覧（Highlights）

- 実行エンジン起動用スクリプト（run_execution）  
  - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）を切替可能。ペーパートレード時は専用 SQLite（data/paper_trading.db）へ記録。
  - プロセス優先度設定 / PID ファイル管理 / ストップフラグ監視を備える。

- 監視プロセス（run_monitoring / MonitoringEngine）  
  - システム状態（CPU / メモリ / ディスク）、データ鮮度、トレードログやリスク指標の監視。
  - Kill Switch ロジック（リスク閾値超過時にフラグファイルを出力して停止要求）やアラート通知連携の仕組みを持つ。

- 監視 DB 永続化（monitoring_db）  
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブル作成・マイグレーション補助。

- リスク監視（risk_monitor）  
  - ドローダウン、ポジション上限の判定・ログ出力。

- ポートフォリオ構築モジュール（portfolio）  
  - 候補選定、等重・スコア重み付け、セクター上限適用、ポジションサイズ決定（単元株丸め・集計スケールダウン等）。

- リサーチ / ファクター計算（research）  
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC 計測、統計サマリ等（DuckDB を利用）。

- AI（news_nlp / regime_detector）  
  - raw_news を LLM（OpenAI）で評価して銘柄ごとに ai_score を生成（score_news）。
  - マクロ記事と ETF MA を合成して市場レジーム（bull/neutral/bear）を判定し DB に書き込み（score_regime）。

- ツール群  
  - 設定ウィザード（config_setup）で .env を対話式生成。
  - 設定検証 CLI（validate_config）で必須環境変数や YAML ファイルのチェック。
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）。

---

## セットアップ手順（Setup）

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストールします（pip）。requirements.txt が無い場合は少なくとも以下を準備してください。
   ```
   pip install duckdb psutil openai
   # YAML の検証を行う場合:
   pip install PyYAML
   ```

3. .env を作成します（推奨: 対話式ウィザードを利用）。
   ```
   python -m kabusys.config_setup
   ```
   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主な設定（デフォルト値）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - LOG_LEVEL: INFO
   - OPENAI_API_KEY: OpenAI を使う機能で必要

   自動読み込み
   - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

4. （任意）config/*.yaml を生成・確認します（ツール提供スクリプトがあればそちらを使用）。

---

## 使い方（Usage）

主なエントリポイント（Python -m で実行可能）:

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # 警告を FAIL とする場合:
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  備考:
  - KABUSYS_ENV=paper_trading の場合はモックブローカーが使われ、data/paper_trading.db に取引履歴を記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - Execution 起動中はプロセス優先度を高く設定する処理が行われます。

- 監視プロセス（SystemMonitor のポーリングループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  挙動:
  - 監視は常に Settings.sqlite_path（data/monitoring.db のデフォルト）を使用して監視用テーブルを初期化します。
  - data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - ニューススコアリング（duckdb 接続を渡して利用）
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY / api_key 引数）が必要です。

停止方法（手動）
- 実行中プロセスを順次停止させたい場合、プロジェクトルートの data/stop_requested.flag を作成してください。run_execution / run_monitoring はこのフラグを監視して順次停止します。

注意: 監視側の KillSwitch は data/kill.flag を書き込んで「Kill Switch 発動」を示します。運用上のフローは環境に合わせて調整してください。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行 / 動作関連
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効、デフォルト "0"）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジンの PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — KillSwitch のフラグファイルパス（デフォルト data/kill.flag）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- 監視
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env 読み込み:
- プロジェクトルートにある `.env` と `.env.local` が自動的に読み込まれます（OS 環境変数 > .env.local > .env の順）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用してログを設定します。デフォルトでは以下のハンドラが設定されます:
  - コンソール出力（stdout）
  - 日次ローテーションのファイル出力（logs/<app_name>.log、30 日分保管）
- `LOG_DIR` 環境変数または setup_logging の引数で出力先を変更できます。

---

## ディレクトリ構成（Directory構成）

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env 読込）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル初期化 / DB 操作）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （トレード挙動監視：未列挙ファイルあり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — フラグファイル書き込みによる停止要求
    - monitoring_engine.py   — 監視コンポーネントまとめ
    - alert_manager.py       — （アラート送信関連：未列挙ファイルあり）
  - execution/
    - execution_engine.py    — 実行エンジンコア（メインロジックは別ファイル）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数決定 / スケール・丸めロジック
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/                    — （実行時に使用する DB / フラグファイル等の格納場所）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/                    — デフォルトのログ出力先

---

## 運用メモ / 実装上の注意

- run_execution / run_monitoring は両方ともプロセス優先度を "high" に設定する処理を持ちます（psutil に依存。権限により失敗する場合は警告が出ます）。
- Monitoring は monitoring DB（SQLite）を初期化します（init_monitoring_db）。既存スキーマに対するマイグレーション（列追加）も備えています。
- Paper Trading（KABUSYS_ENV=paper_trading）は実環境 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能は OpenAI SDK を利用しています。API 呼び出しはリトライ処理やレスポンス検証を備えているものの、API キーの設定漏れ・レート制限等に注意してください。
- 設定検証（validate_config）を運用前に必ず実行し、必須環境変数やファイルパスの問題を確認してください。
- 停止フラグについて：
  - `data/stop_requested.flag` を作成すると run_execution/run_monitoring は検知して順次停止します（手動停止手段）。
  - `KillSwitch` は `data/kill.flag` を書き込むことで「Kill Switch 発動」を記録します。運用でのフラグ連携方法は環境に応じて調整してください。

---

必要に応じて README を拡張します。特にデプロイ手順（systemd / Supervisor / Docker）、CI/CD 設定、さらなる運用ガイド（ログローテーション設定、バックアップ方針、監視のしきい値パラメータ等）を追加可能です。どの部分を詳しく追記希望か教えてください。