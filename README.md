# KabuSys — 日本株自動売買システム（簡易 README）

本リポジトリは、日本株の自動売買システム KabuSys の一部実装です。  
この README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

※ 実行には Python 3.10 以上を推奨します（型注釈に `X | None` を使用しているため）。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引を想定したモジュール群です。主な要素は以下です。

- データ処理・リサーチ（DuckDB を利用したファクター計算）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ決定）
- Execution（発注エンジン）とモニタリング（監視・アラート・Kill Switch）
- AI 補助（ニュースの NLP スコアリング / レジーム判定）
- 開発用ユーティリティ（.env ウィザード、設定検証、レポート生成）

コードはモジュール化され、DuckDB / SQLite を永続ストレージとして利用します。

---

## 主な機能一覧

- 環境設定の対話式ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
- Execution エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時にモックブローカー／専用 DB に分離
  - 停止フラグ（data/stop_requested.flag / data/kill.flag / execution.pid）による制御
- Monitoring（kabusys.run_monitoring / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite にシステム・注文ログを永続化
  - Kill Switch による ExecutionEngine 停止トリガー
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
- Portfolio モジュール
  - 銘柄選定、等ウェイト／スコア加重計算、リスク調整（セクター制限等）、株数算出
- Research モジュール（DuckDB 接続を受け取りファクター計算等を実行）
- AI モジュール
  - news_nlp: ニュースを OpenAI に送信して銘柄ごとのセンチメントを ai_scores テーブルに保存
  - regime_detector: ETF + マクロ記事を組合せて市場レジームを判定
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 依存関係（代表例）

必要なパッケージ例（プロジェクト内の import を元に）:

- Python 3.10+
- duckdb
- psutil
- openai
- pyyaml（config 検証で YAML を確認する場合）
- その他標準ライブラリ（sqlite3 等）

インストール例:

    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

（実プロジェクトでは requirements.txt を用意して pip install -r することを推奨します）

---

## 環境変数（主要なもの）

必須・重要な環境変数（validate_config でもチェック）:

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

その他よく使う設定:

- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- OPENAI_API_KEY — OpenAI API Key（AI モジュール利用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- PAPER_FILL_MODE — Paper Trading のフィルモード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリア（0/1）

.env の自動読み込み:
- .env と .env.local をプロジェクトルートから自動読み込みします（OS 環境変数を優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローンし、仮想環境を作る:

    git clone <repo>
    cd <repo>
    python -m venv .venv
    source .venv/bin/activate

2. 必要パッケージをインストール:

    pip install duckdb psutil openai pyyaml

3. .env を作成（ウィザード推奨）:

    python -m kabusys.config_setup

   - ウィザードは .env を生成します。生成後、機密情報（APIキー等）は絶対に Git にコミットしないでください。

4. 設定検証（任意）:

    python -m kabusys.validate_config
    # 警告もエラー扱いにする場合:
    python -m kabusys.validate_config --strict

5. データディレクトリやログディレクトリが自動作成されます（ログは logs/、DB は data/ に保存されるのがデフォルト）。

---

## 基本的な使い方（CLI）

- Execution（発注エンジン）を起動:

    # module 実行例（プロジェクトルートから）
    python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すれば起動せず終了します。
  - 実行中に stop フラグが作成されるとエンジンを停止します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring（監視ループ）を起動:

    python -m kabusys.run_monitoring

  挙動:
  - SystemMonitor を定期実行して system_status などを SQLite（設定の SQLITE_PATH）に保存します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60 秒）。
  - stop フラグ（data/stop_requested.flag）を検知するとループを抜けて終了します。

- 設定ウィザード（.env 生成）:

    python -m kabusys.config_setup

- 設定検証:

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading レポート生成:

    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB パスを指定したい場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB 接続を受け取り、OpenAI API キーを参照して動作します。スクリプトから直接 CLI エントリはありませんが、ユーティリティとして import して利用できます。

---

## 停止フラグ / Kill Switch の扱い

- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring はこのファイルを検知すると安全に停止します（手動で作成して停止指示が可能）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch がトリガーされた場合に作成され、ExecutionEngine に停止指示を出す用途で使用されます。
  - Settings.KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされます（本番では 0 推奨）。
- PID ファイル: data/execution.pid（Execution 起動時に書き込まれる想定）

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging を参照。
- デフォルトでは stdout に StreamHandler、日次ローテートのファイルハンドラ（logs/<app_name>.log）が設定されます。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイル/ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU アフィニティ設定
  - monitoring/
    - monitoring_db.py        — SQLite 永続層
    - system_monitor.py       — システム監視ロジック
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - trade_monitor.py        — （存在）取引監視（ファイル抜粋では一部）
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （存在）通知管理（抜粋では詳細なし）
  - execution/                — 発注エンジン周り（OrderManager 等、抜粋外）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py      — 市場レジーム判定（OpenAI 使用）
  - data/                     — 実行時に生成される (logs/, data/*.db, flags 等)

（上記は抜粋です。実コードベースにはさらに多くのモジュールが含まれます）

---

## 開発上の注意点 / ベストプラクティス

- .env は機密情報を含むため Git にコミットしないでください。
- KABUSYS_ENV が `live` の場合は本番設定として扱われるため設定を慎重にチェックしてください（validate_config で警告が出ます）。
- OpenAI API を使用する機能は API 利用料とレート制限に注意してください。失敗時のフォールバックが組み込まれていますが、実運用では制御が必要です。
- モニタリングループや Execution は stop フラグ / kill.flag により安全に停止できる設計です。運用時はこれらのフラグ管理を運用手順に組み込んでください。
- DuckDB と SQLite のパスは Settings で指定できます。paper_trading は本番 DB と分離するように設計されています。

---

必要であれば、README に「実行例」「環境変数の詳細表」「ユニットテストの実行方法」などを追記できます。どの項目を詳しく書きたいか教えてください。