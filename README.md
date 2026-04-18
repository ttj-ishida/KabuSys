# KabuSys

日本株向け自動売買システムのコアライブラリ（README）

このリポジトリは、システム監視・注文実行・ポートフォリオ構築・ファクター研究・LLM を用いたニュース評価などを含む自動売買プラットフォームの一部実装です。ここではプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのためのモジュール群です。主な役割は以下の通りです。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム健全性・注文状況・リスク監視、Kill Switch）
- Portfolio construction（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- Research（ファクター計算、特徴量解析、IC 計算）
- AI（ニュース NLP によるセンチメント評価、レジーム検出）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定、ツール類）

設計方針は「本番データ・発注 API に直接アクセスさせない」「冪等性・フォールトトレランス」「ルックアヘッドバイアスの回避」などが組み込まれています。

---

## 機能一覧

- 環境設定ウィザード（.env 作成/更新）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前検証）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（発注・注文管理・リスク制御）: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` の場合はモックブローカー（MockBrokerClient）を使用し、Paper Trading 用 DB（`data/paper_trading.db`）に記録。実運用と分離。
- 監視ループ起動スクリプト（SystemMonitor のポーリング）: `run_monitoring.py`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照（環境に依存せず監視 DB を使用）。
- Monitoring サブシステム
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度をチェック
  - TradeMonitor：注文の滞留や約定異常を検出（trade_logs 参照）
  - RiskMonitor：ドローダウン、ポジション上限などを監視し risk_logs / dashboard を更新
  - KillSwitch：条件に応じて `data/kill.flag` を作成し ExecutionEngine に停止を促す
  - MonitoringEngine：上記をまとめて定期的に実行しアラートを発行
- AI モジュール
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコア取得 → `ai_scores` テーブルへ保存
  - regime_detector: ETF(1321) の MA とマクロニュースの LLM 評価を合成して日次レジームを判定
- Research（DuckDB 接続を利用）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- Portfolio（純粋関数）
  - 候補選定、重み計算、セクターキャップ適用、ポジションサイズ計算（単元株丸め、aggregate cap）
- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポートを出力
- ユーティリティ
  - 設定読み取りと自動 .env ロード（`kabusys.config.Settings`）
  - ログ設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定

---

## 前提 / 必要要件

- Python 3.9+
- 必須（利用する機能に応じて）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config/*.yaml のパース検証をしたい場合）
- SQLite（標準ライブラリで OK）
- .env に各種 API キー・パスを設定

依存パッケージはプロジェクトの requirements ファイル（存在する場合）または README に記載を参照してください。

---

## 環境変数（主要なもの）

主に以下の環境変数が利用されます（デフォルト値は code 内のコメント参照）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...、デフォルト "INFO"）
- LOG_DIR: ログ出力ディレクトリ（デフォルト `logs/`）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知用）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（開発用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の fill モード（"instant" | "partial" | "never" | "reject"）

注意: `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成してアクティベートする。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする（例: pip）。
   - pip install -r requirements.txt
   - または必要に応じて: pip install duckdb psutil openai pyyaml

3. .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（.env.example があれば参照）。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳密モード（警告もエラー扱い）: python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - デフォルトでは `data/` や `logs/` を利用するため作成しておくとよい:
     - mkdir -p data logs

---

## 使い方（起動・実行コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  停止:
  - プロセスは `data/stop_requested.flag` ファイルの存在を確認して安全にループを終了します。停止させたい場合はそのファイルを作成してください。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - Paper Trading モードで起動するには:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading では MockBrokerClient を使用し、記録先は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に分離されます。

  停止:
  - ExecutionEngine も `data/stop_requested.flag` を監視します。`data/stop_requested.flag` を作成するとエンジンを停止します。
  - Kill Switch（`data/kill.flag`）は RiskMonitor 等の条件により作成され、Execution 側に停止を要求します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニュース評価 / レジーム判定）
  - `kabusys.ai.score_news(conn, target_date, api_key=None)` — DuckDB 接続を渡して実行
    - 内部で OPENAI_API_KEY を参照可能。API キーが渡されない場合は環境変数を使います。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` — レジーム判定を実行
  - 注意: OpenAI API 呼び出しはネットワーク失敗やレート制限に対してリトライ・フェイルセーフ実装がありますが、API キーは必須です。

---

## ファイル・フラグの扱い（運用メモ）

- stop flag:
  - data/stop_requested.flag — run_monitoring.py / run_execution.py のループ停止信号（存在を検出して正常終了）
- kill flag:
  - data/kill.flag — KillSwitch が生成する ExecutionEngine 停止のための永続フラグ（実行時に Settings.kill_flag_clear_on_start を参照して自動クリアするか選択可能）
- pid file:
  - data/execution.pid — ExecutionEngine が PID を書き込む（プロセス生存監視に利用）

---

## 主要スクリプトの動作ポイント

- run_monitoring.py
  - プロセス優先度を high に設定（`utils.process_priority.set_process_priority`）
  - Settings から sqlite_path（監視 DB）と duckdb_path を取得して接続
  - SystemMonitor を使い定期的に `check_once()` を呼ぶ
  - MONITOR_POLL_INTERVAL 環境変数で間隔指定（デフォルト 60 秒）
  - 停止フラグ検知で正常終了

- run_execution.py
  - 環境に応じて本番 DB / paper_trading DB を切替
  - BrokerClientFactory によりブローカークライアントを生成（paper_trading 時はモック）
  - ExecutionEngine を別スレッドで起動し停止フラグを監視

- config.py
  - プロジェクトルートを自動検出して `.env` / `.env.local` を自動ロード（必要時無効化可）
  - Settings クラス経由で設定を取得（プロパティでバリデーションを実施）

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python パッケージ構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在暗示)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在暗示)
  - execution/
    - execution_engine.py (存在暗示)
    - broker_factory.py (存在暗示)
    - order_manager.py (存在暗示)
    - order_repository.py (存在暗示)
    - reconciler.py (存在暗示)
    - risk_manager.py (存在暗示)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (runtime の SQLite / flag / pid / paper DB を想定)
  - logs/ (ログファイル出力先、デフォルト)

注: 一部ファイルはここに示した一覧の他に存在する可能性があります。各モジュール内の docstring に使い方や設計が記載されています。

---

## 運用上の注意点・ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env や設定ファイル、LINE 通知先などを慎重に設定してください。`validate_config` は live 時に警告を出します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番では無効（0）を推奨します。誤って自動クリアさせるとセーフティ機構が無効になります。
- Paper Trading 用 DB は本番とは別に保管してください（PAPER_TRADING_SQLITE_PATH）。
- ログは stdout と日次ローテーションファイルの両方に出力されます。ログディレクトリ（LOG_DIR）が作成できない場合はファイル出力をスキップしてコンソール出力のみになります。
- AI 機能を使う場合は OpenAI API の利用料金・レート制限に注意してください。API エラーは一定回数リトライされますが、失敗時はフェイルセーフ（スコア = 0 など）で続行する実装です。

---

## 参考コマンドまとめ

- .env 作成ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視起動
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースに含まれる docstring と仕様に基づいて作成しています。詳細な API 仕様や挙動は各モジュールの docstring を参照してください。もし追加で「導入手順の自動化」「例となる .env.example の作成」「Dockerfile / systemd ユニットの例」などが必要であればお知らせください。