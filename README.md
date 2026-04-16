# KabuSys

日本株自動売買システムのパッケージ（抜粋）。この README はリポジトリ内の主要コンポーネントと使い方をまとめたものです。

主な設計方針・注意点：
- 本リポジトリは実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースのセンチメント等）など複数コンポーネントで構成されています。
- 環境変数（.env / .env.local / OS 環境変数）から設定を読み込みます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。
- Paper Trading（検証）モードでは本番 DB と完全分離された SQLite を使用します。

---

## プロジェクト概要

KabuSys は日本株の自動売買を前提としたコンポーネント群です。主な機能は以下の通り：

- ExecutionEngine：発注・注文管理・リスク管理・リコンシリエーション等を行う実行エンジン
- Monitoring：システム状態、注文状態、リスク（ドローダウン・ポジション上限）を監視し、ログを書き出す
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数等の純粋関数群
- Research：ファクター計算（モメンタム、ボラティリティ、バリュー）や IC 計算などの解析ユーティリティ
- AI：ニュースセンチメント（OpenAI 利用）／市場レジーム判定のための LLM 呼び出しラッパー
- Tools：Paper Trading 検証レポート生成や Streamlit ベースの監視ダッシュボード等

---

## 機能一覧

- 実行・注文管理
  - 発注、重複チェック、注文状態同期（Reconciler）
  - Risk Manager による上限 / ドローダウン監視
- 監視（Monitoring）
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常チェック
  - RiskMonitor：ドローダウン、ポジション上限の検出とログ化
  - KillSwitch：致命的リスクにより `kill.flag` を書き込み外部停止トリガーを送る
  - AlertManager：LINE Messaging API による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（監視データの可視化）
- ポートフォリオ構築
  - 候補選定、等加重/スコア加重、リスクベースのポジションサイズ計算
  - セクター上限やレジーム乗数の適用
- リサーチ
  - DuckDB 上の時系列データを用いたファクター計算・将来リターン計算・IC/統計サマリ
- AI（OpenAI）
  - ニュースを集約して LLM に投げ、銘柄単位のセンチメントスコアを ai_scores に書き込む
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - `.env` のパーサと自動ロード

---

## セットアップ手順

前提
- Python 3.10+（typing の新しい構文を使用）
- Git リポジトリルートに配置されていることを想定

1. リポジトリをクローン・チェックアウトし、作業ディレクトリをプロジェクトルートに合わせる。

2. 仮想環境を作成して有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は一例）：
   - pip install duckdb psutil openai requests streamlit

   実運用ではブローカークライアント等の依存も必要です（実装による）。

4. 環境変数の設定
   - ルートに `.env`（または `.env.local`）を作成して環境変数を定義できます。自動ロードはデフォルトで有効です。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL (例: INFO)
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - PID_FILE_PATH / KILL_FLAG_PATH 等
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）

   - 自動ロードを無効にする:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）:
   - mkdir -p data

---

## 使い方

基本的にパッケージ内のモジュールをモジュール実行して起動します。プロジェクトルートに移動して実行してください。

1. 監視プロセスの起動（Monitoring）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します。

2. 実行エンジンの起動（Execution）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - `data/stop_requested.flag` を作成するとエンジン停止をトリガーします。
   - 起動時に `data/execution.pid` を書き込みます。監視プロセスはこの PID を確認してプロセス生存チェックを行います。

3. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

4. Streamlit 監視ダッシュボード
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは DB を読み取り専用モードで開きます（起動中の MonitoringEngine が書き込んでいることが想定）。

5. AI 系機能
   - `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` は OpenAI API を利用します。`OPENAI_API_KEY` を環境変数または関数引数で指定してください。
   - レート制限や 5xx 系エラーに対しては指数バックオフでリトライする実装があります。

6. ログレベル
   - Settings クラスは `LOG_LEVEL` を読みます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。起動スクリプトは logging.basicConfig(level=logging.INFO) を設定していますが、環境変数で上書きできます。

---

## 主要ファイル・ディレクトリ構成

（トップレベルは src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス。`.env` / `.env.local` の自動読み込みロジックを含む。
  - run_monitoring.py
    - SystemMonitor をポーリングして監視 DB に書き込む起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する起動スクリプト（paper_trading モード対応）
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, execution_engine.py など（発注・リコンシリエーション等）
  - monitoring/
    - monitoring_db.py : SQLite スキーマ初期化 & 永続化 API
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - kill_switch.py, alert_manager.py, streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py（DuckDB を使った分析）
  - ai/
    - news_nlp.py（ニュースセンチメント取得）, regime_detector.py（市場レジーム判定）
  - tools/
    - paper_verification_report.py
  - data/ (実行時に生成を想定)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (PAPER_TRADING 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid / stop_requested.flag / kill.flag

注：上記は主要ファイルを抜粋した一覧です。細かい実装は各モジュールを参照してください。

---

## DB スキーマ（監視用 - monitoring_db.py の概要）

init_monitoring_db により以下テーブルが作成されます（冪等）：

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type (Created/Sent/Filled 等), client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PRIMARY KEY), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - 単一行（id=1）で集計値を保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default 60）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（MockBroker の挙動）
- OPENAI_API_KEY: OpenAI API を使う場合必須
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の機密情報
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- PID_FILE_PATH, KILL_FLAG_PATH: 実行時のファイルパス指定

詳しい設定は `src/kabusys/config.py` を参照してください。

---

## 運用メモ / 注意点

- Paper Trading は本番データベースと分離されます（paper_trading モード）。
- `data/stop_requested.flag` はモジュール起動ループの安全停止シグナルです。手動で作成するとプロセスは順次終了します。
- `data/kill.flag` は KillSwitch が作成する停止フラグ（ExecutionEngine に対する致命的停止トリガ）です。`KillSwitch.clear()` を使って削除できます。
- OpenAI 利用時はレート制限や API エラーに対するリトライ処理が組み込まれていますが、実運用では API コスト・利用制限に注意してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くため、DB ファイルのパーミッションやロックに注意してください。
- `config._load_env_file` は既存 OS 環境変数を保護するため `.env` の上書きに制限があります。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用できます。

---

以上がこのコードベースの概要と利用手順です。必要であれば、以下の追加ドキュメントも作成できます：
- 各モジュール（ExecutionEngine / RiskManager / Broker API）の詳細ドキュメント
- 運用手順書（起動・停止・緊急対応）
- サンプル .env.example ファイル

どのドキュメントを優先して作成しましょうか？