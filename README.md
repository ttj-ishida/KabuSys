# KabuSys

日本株向け自動売買・リサーチ基盤のサンプル実装です。  
このリポジトリは以下の機能群を持ち、実運用／ペーパートレード／リサーチ用途を想定しています。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視サブシステム（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクター制約）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア化）とレジーム判定
- 各種ユーティリティ（設定ウィザード・設定検証・ログ設定など）
- ペーパートレード検証レポート生成ツール

以下は本プロジェクトの概要、セットアップ、使い方、ディレクトリ構成の説明です。

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ペーパートレード（KABUSYS_ENV=paper_trading）時は MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）に記録
  - プロセス優先度を起動時に設定

- 監視（Monitoring）
  - System / Trade / Risk Monitor を組み合わせた MonitoringEngine（run_monitoring.py 経由で起動）
  - SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch（条件を満たしたら data/kill.flag を出力して Execution を停止）
  - MONITOR_POLL_INTERVAL 環境変数で監視間隔を調整

- ポートフォリオ構築
  - 候補選定（スコア降順、signal_rank によるタイブレーク）
  - 等比配分 / スコア加重配分
  - リスクベースの株数決定、単元株（lot）丸め、aggregate cap のスケーリング
  - セクター上限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）

- リサーチ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC（Spearman）や統計サマリー等のユーティリティ

- AI（OpenAI）
  - ニュース記事をまとめ、銘柄ごとのセンチメントを LLM（gpt-4o-mini を想定）で算出して ai_scores に格納
  - マクロニュース + ETF ma200 を使った市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・バックオフ処理あり。APIキーは OPENAI_API_KEY から読み込むか引数で渡す

- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈の union 型や from __future__ アノテーションを用いているため 3.10 以上を推奨）
- SQLite は標準ライブラリで利用可能
- DuckDB, psutil, openai 等の外部パッケージが必要

1. リポジトリをクローンする
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   例:
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

4. 初回設定
   - 対話式で .env を作る（推奨）
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考）

5. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱い（exit 1）

6. データディレクトリ（logs, data 等）の確認／作成
   - ログはデフォルトで logs/ に出力されます（logs/<app_name>.log）
   - SQLite / DuckDB のデフォルトパス:
     - SQLITE_PATH: data/monitoring.db
     - DUCKDB_PATH: data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (ペーパートレード用)

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（デフォルト値や説明を併記）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（INFO 等）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

ファイルによる制御:
- data/kill.flag — Kill Switch のフラグファイル（存在すれば Execution 停止シグナル）
- data/stop_requested.flag — run_monitoring / run_execution が検知する停止フラグ
- data/execution.pid — ExecutionEngine 起動時に使われる PID ファイル

注意:
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を検索）を基準に行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定して起動（専用 DB に記録）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI スコアリング / レジーム判定（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用

ログの確認:
- デフォルト: logs/execution.log, logs/monitoring.log 等

停止フラグの利用:
- data/stop_requested.flag を作成すると、run_monitoring・run_execution は安全にシャットダウンします
- Kill Switch により data/kill.flag が作成されると ExecutionEngine に停止シグナルが送られます

---

## ディレクトリ構成（主要ファイルと役割）

（ルートは src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の読み込みと Settings クラス（アプリ設定）
  - config_setup.py
    - .env を対話式に作成するウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 接続・エンジン起動）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定（Stream + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度と CPU affinity 設定（psutil）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 注文発行・注文管理・リスク管理の主要モジュール（サンプル）
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite スキーマ初期化と CRUD
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文監視（滞留・異常約定など）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — フラグファイルベースの停止シグナル生成
    - alert_manager.py — 通知／アラート統括（LINE などに送信する実装想定）
    - monitoring_engine.py — 各 Monitor を定期実行するエンジン
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出 / スケーリング / 単元丸め
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC 計算・統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM でセンチメント評価して ai_scores に保存
    - regime_detector.py — マクロ記事 + ETF MA を合成して市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - data/ (実行時に生成されるディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid などフラグ／PID ファイル

---

## 監視 DB（monitoring_db）について（概要）

init_monitoring_db() により以下テーブルが作成されます（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type (Created / Sent / Filled 等), client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 の単一行に集約: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

これらを MonitoringDB クラス経由で読み書きします。

---

## 開発・運用上の注意点

- KABUSYS_ENV=live の場合は設定を慎重に（LINE 通知・Kill Switch 設定など本番向けガードあり）
- OpenAI API を利用する機能は API キーが必須。API 呼び出しの失敗はフェイルセーフでスコア 0 やスキップで継続する実装方針
- ペーパートレード時は本番 DB と完全分離されるよう PAPER_TRADING_SQLITE_PATH を使用
- ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ出力する仕様
- .env ファイルは絶対に Git にコミットしないこと

---

## 参考コマンド一覧

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- ExecutionEngine 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に「コマンドの実行例」「環境変数の完全一覧」「DB スキーマ詳細」「API の入力／出力仕様（ai のプロンプト・JSON フォーマット）」などをさらに追記できます。どの項目を詳しく載せたいか教えてください。