# KabuSys

KabuSys は日本株を対象とした自動売買システムのコアライブラリ群です。ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、ニュース NLP を用いた AI スコアリングなど、実運用を意識したコンポーネントを含みます。

以下はこのリポジトリの README（日本語）です。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とその周辺ツール群。
- モニタリング（System / Trade / Risk）による安全性確保とアラート送信（LINE）。
- Paper Trading モード（本番 DB と分離し、モックブローカーで検証可能）。
- DuckDB / SQLite を用いたデータ解析・永続化。
- ニュース記事を LLM（OpenAI）でスコアリングしてシグナルに組み込むためのモジュール。
- 研究用途のファクター計算、特徴量解析ユーティリティ。

設計方針：
- 本番運用を想定したフェイルセーフ（API失敗時のフォールバック、冪等書き込み等）。
- ルックアヘッドバイアスを避けるため、日時参照に注意した実装。
- OS 関連の差分（プロセス優先度など）は抽象化して扱う。

---

## 主な機能一覧

- Execution
  - エンジン起動 / 発注管理 / リコンシリエーション（再起動時の同期）
  - Paper Trading モード（モックブローカー、専用 SQLite）
- Monitoring
  - システム状態（CPU / メモリ / ディスク）監視と DB 永続化
  - 注文滞留・約定異常検知
  - ドローダウン・ポジション上限監視と kill switch（停止フラグ出力）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio Construction
  - 候補選定、等重・スコア加重配分、株数決定（単元丸め含む）
  - セクターキャップ・レジーム乗数
- Research
  - momentum/value/volatility ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン・IC・統計サマリーなど
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント集約と ai_scores への書き込み
  - 市場レジーム検出（ma200 とマクロニュースの組合せ）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

※ 以下は最小限の手順・依存パッケージの例です。プロジェクトに requirements.txt がある場合はそちらを使ってください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロダクションではバージョン固定した requirements.txt を用意してください）

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数または .env の準備
   - ルートに `.env` / `.env.local` を置くと自動ロードされます（デフォルト）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

6. DB 初期化
   - monitoring 用の SQLite テーブルは起動時に自動作成（init_monitoring_db）されます。特別な手順は不要です。

---

## 必要（推奨）環境変数一覧

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI を利用する場合
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録されます
- PAPER_FILL_MODE — paper_trading の fill モード（"instant" | "partial" | "never" | "reject"、デフォルト: "instant"）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか ("1" で有効)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値（%）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら通知は発行されずログのみ）

Settings モジュールは .env / .env.local を自動ロードします（OS 環境変数が優先されます）。詳細は `kabusys.config` を参照してください。

---

## 起動・使い方

以下は主要なスクリプトの起動方法です。

- ExecutionEngine を起動（本番 / paper_trading の切替は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 勝手に実行中の stop flag（data/stop_requested.flag）があれば起動を中止します。
  - 実行中は `data/execution.pid` に PID が書かれます。
  - 停止は stop_requested.flag を作成するか、ExecutionEngine の kill.flag を利用します。

- Monitoring を起動（ポーリングで監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（監視 DB）に書き込みします。run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（意図的な設計）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは `--db` で別 DB を指定可能。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは `data/paper_trading.db`。`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI モジュール（プログラム内呼び出し）
  - ニューススコア生成:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  — 引数に DuckDB 接続と日付を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- 研究モジュール（プログラム内呼び出し）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - それぞれ DuckDB 接続と target_date を渡して使用

注意事項：
- run_execution / run_monitoring はプロセス優先度を "high" に設定しようとします（psutil を使用）。設定に失敗した場合は警告を出して継続します。
- 実行の停止制御には以下のフラグファイルを利用します:
  - data/stop_requested.flag — run_* スクリプトが監視している停止フラグ（存在するとループ終了）
  - data/kill.flag — KillSwitch により ExecutionEngine 停止を要求するために書かれる（存在確認・削除ロジックあり）
  - PID ファイル: data/execution.pid

---

## 操作例

- 簡易（開発）起動例:
  - export KABUSYS_ENV=development
  - export LOG_LEVEL=DEBUG
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution

- Paper Trading で起動（本番 DB と分離）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - （paper_trading は `PAPER_TRADING_SQLITE_PATH` に記録）

- 監視間隔を 30 秒に設定して起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Streamlit：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## ディレクトリ構成（主要ファイル）

（ルートの `src/kabusys` 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                       — 環境変数/.env 読み込み・Settings 定義
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ... (発注関連の実装)
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 永続化層（system_status 等）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ (runtime)
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - execution.pid
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag

---

## 注意・補足

- DB スキーマやマイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブル・インデックスを作成します。起動時に自動的に実行されます。
  - 既存 DB に対する軽微なカラム追加（例: trade_logs.latency_ms, dashboard.peak_value）はコード内で検出・追加します。

- OpenAI / ネットワーク呼び出し
  - news_nlp と regime_detector は OpenAI API を利用します。API 呼び出しは冪等ではなく課金発生するため、本番 API キーの管理に注意してください。
  - API 呼び出しで失敗した場合はフェイルセーフ（スコアを 0 にフォールバックする、あるいはスキップ）する実装になっています。

- 権限
  - プロセス優先度設定や CPU affinity の設定は OS の権限に依存します。権限がない場合は警告ログが出ますが処理自体は続行します。

---

開発者向けに更に詳細な使い方や API 仕様（OrderRecord/OrderRepository のインターフェース、DuckDB スキーマ等）が必要でしたら追って README を拡張します。