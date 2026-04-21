# KabuSys

日本株自動売買システムの Python コードベース（README）

この README はリポジトリ内の主要スクリプト・モジュール群の概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤を想定したモジュール群です。主な役割は以下です。

- 発注エンジン（ExecutionEngine）による売買ロジック実行（実口座 / ペーパートレード対応）
- 監視コンポーネント（Monitoring）によるシステム安定性・注文状況・リスクの監視
- ポートフォリオ構築（選定・配分・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP（OpenAI）を用いたセンチメント集計・レジーム判定
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証など）
- 各種ツール（ペーパートレード検証レポート生成など）

設計方針の一例：
- DuckDB を分析用データベースとして使用
- SQLite を監視・トレードログ保存用に使用（ペーパートレードは分離）
- OpenAI を使った NLP 機能はオプション（API キー必須）
- .env による環境変数管理を自前で実装（自動読み込みウィザードあり）

---

## 主な機能一覧

- 設定管理
  - .env の対話式生成（`kabusys.config_setup`）
  - 起動前の設定検証 CLI（`kabusys.validate_config`）
- 実行エンジン
  - ExecutionEngine の起動スクリプト（`run_execution.py`）
  - ペーパートレード時は MockBroker を使用し、紙上トレード用 DB を利用
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor の統合（`monitoring_engine.py`）
  - 監視ループ起動スクリプト（`run_monitoring.py`）
  - Kill Switch（`data/kill.flag`）で ExecutionEngine 停止制御
- ポートフォリオ構築
  - 銘柄選定、等配分/スコア配分、ポジションサイジング、セクター制約
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）分析、統計サマリー
- AI（任意）
  - ニュースのセンチメント評価と ai_scores への保存（OpenAI）
  - マクロ + ETF MA による市場レジーム判定（OpenAI）
- ツール
  - ペーパートレード検証レポート生成（`kabusys.tools.paper_verification_report`）
- ユーティリティ
  - 統一ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（ローカル開発向け・基本）

下記は最小限の手順例です。実際にはプロジェクトに付属の requirements.txt を参照してください。

1. Python（推奨 3.10 以上）を用意する。

2. 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要ライブラリをインストール:
   - 必須（本リポジトリの機能をフルに利用する場合）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
   - オプション:
     - pyyaml（`kabusys.validate_config` の YAML 検証を有効にするため）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動で配置。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（一部）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading 時に使用）
     - LOG_LEVEL — ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - MONITOR_POLL_INTERVAL — 監視ループの間隔（秒）。run_monitoring 固有の上書き用

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

6. ログディレクトリ
   - デフォルトでは `logs/` にログを出力します。必要に応じて LOG_DIR を設定してください。

---

## 使い方（主要コマンド例）

- .env の作成（対話式）:
  - python -m kabusys.config_setup

- 設定の検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動:
  - 通常（KABUSYS_ENV によって動作が変わります）:
    - python -m kabusys.run_execution
  - ペーパートレードで起動する場合:
    - 環境変数: KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時のポイント:
    - ペーパートレード時は MockBrokerClient が使用され、デフォルトで data/paper_trading.db にログを保存して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を保存します（設定によりパス変更可能）。

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番 sqlite_path）を使用します（KABUSYS_ENV にかかわらず）。
  - 停止は `data/stop_requested.flag` を作成するか、Ctrl+C。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH、または `--db` オプションで変更可能。

- AI（ニュースセンチメント / レジーム判定）
  - これらは関数ベースで提供されます（Python からインポートして利用）。
    - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
    - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API を使うため `OPENAI_API_KEY` を設定するか、明示的に api_key を渡してください。

---

## 重要な動作/ファイル（運用時の注意）

- stop/kill フラグ
  - data/stop_requested.flag
    - run_execution/run_monitoring の外部停止用フラグ。存在するとループを抜ける／起動をスキップするなどの動作をします。
  - data/kill.flag
    - KillSwitch により ExecutionEngine を停止させるために書き込まれるフラグ（監視側が書き込み）。
    - `KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に自動クリアされます（本番環境では `0` を推奨）。
- データベース
  - DuckDB（分析用）: デフォルト `data/kabusys.duckdb`（Settings.duckdb_path）
  - SQLite（監視 / トレードログ）: デフォルト `data/monitoring.db`（Settings.sqlite_path）
  - Paper trading 用 SQLite: `data/paper_trading.db`（Settings.paper_sqlite_path）
  - 監視 DB は monitoring モジュール内で必要なテーブルを自動生成・マイグレーションします（init_monitoring_db）。
- ログ
  - デフォルト `logs/` にアプリケーションごとに日次ローテーションで出力（TimedRotatingFileHandler）。
  - 既存ハンドラの二重登録防止のため、setup_logging() はルートロガーのハンドラを一度クリアして設定します。
- プロセス優先度
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足等で失敗する場合は警告ログを出力して続行します。
- MONITOR の注意
  - run_monitoring は Monitoring 用の SQLite を環境にかかわらず本番 sqlite_path を使う設計になっています（監視ログは本番 DB に保存する想定）。

---

## 環境変数一覧（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / よく使う:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
  - OPENAI_API_KEY — AI 機能を利用する場合に必須
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1 = 有効。production では 0 推奨）

詳しくは `kabusys.config.Settings` クラスのプロパティを参照してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内 `src/kabusys/` 以下の主なファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — 統一ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 + DB ラッパー
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン/ポジション上限チェック
    - kill_switch.py         — Kill Switch（flag 書込）
    - ...（TradeMonitor, AlertManager 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算、単元丸め、集計キャップ
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py — 将来リターン・IC 等の解析ユーティリティ
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）集計ロジック
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - execution/               — Execution 関連（BrokerFactory, Engine, OrderManager 等）
  - data/                    — 実行時生成データ（DB, pid, flag など）
  - logs/                    — デフォルトログ出力先（起動時に作成）

（実装ファイルはリポジトリによって多少差があります。上は主要な責務ごとの配置例です）

---

## 開発・運用上の注意点

- 本番（KABUSYS_ENV=live）では設定の確認を厳密に行ってください（`validate_config` を利用）。
- Kill Switch や stop flag の取り扱いは慎重に行ってください。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険です。
- OpenAI API 呼び出しにはコスト・レイテンシが発生します。rate limit / retry ロジックは実装されていますが、API キー・料金には注意してください。
- DuckDB / SQLite のパスは運用環境に合わせて設定し、バックアップやアクセス権限を整備してください。
- ログディレクトリや DB の親ディレクトリが存在しない場合、起動時に自動作成されますが、ファイルシステム権限に注意してください。

---

必要であれば README に「環境変数の完全な一覧」「サンプル .env」「起動スクリプトの systemd / Supervisor 用 Unit 例」などを追加します。どの情報を詳しく追記したいか教えてください。