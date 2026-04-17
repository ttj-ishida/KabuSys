# KabuSys

日本株自動売買システムの一部を収めたリポジトリの README。  
この README はコードベース（src/kabusys 以下）から抽出した用途・起動方法・構成をまとめたものです。

重要: 本リポジトリは実務用の自動売買コンポーネント（ブローカー接続・発注ロジック・監視・AIモジュール等）を含みます。実際に稼働させる際は API キーやブローカーの取り扱い、テスト環境と本番データの分離等に十分ご注意ください。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコンポーネント群です。主な機能は以下の通りです：

- 発注エンジン（ExecutionEngine）と Order 管理
- 監視（Monitoring）: システム健全性、注文滞留、リスク（ドローダウン・ポジション上限）監視
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ（ファクター計算・特徴量分析）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 環境設定管理（.env 自動ロード、Settings）

コードは純粋関数と副作用を伴う DB/外部 API 呼び出し部分が分離されています。

---

## 主な機能一覧

- monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文滞留（stale order）・約定異常価格検出
  - RiskMonitor: ドローダウンとポジション上限監視、ダッシュボード更新
  - MonitoringDB: SQLite に監視ログを永続化
  - KillSwitch: 条件に応じて停止フラグを書き込み ExecutionEngine を停止させる
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を表示）

- execution（発注系）
  - ExecutionEngine（run_execution 起動スクリプトから起動）
  - Broker クライアントファクトリ（paper_trading の場合は MockBrokerClient を使用）
  - OrderManager / Reconciler / RiskManager / OrderRepository 等

- portfolio
  - 銘柄選定（select_candidates）
  - 重み計算（等配分・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（lot 単位丸め、資金スケーリング）

- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー

- ai
  - news_nlp: OpenAI を使ったニュースセンチメント（ai_scores へ書き込み）
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定

- tools
  - paper_verification_report: Paper Trading DB から検証レポート（稼働率・約定率・レイテンシ等）を生成

---

## セットアップ手順

以下はローカルで動かすための基本手順例です。

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（pip）
   - 必要パッケージ（最低限）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   実際には pyproject.toml / requirements.txt があればそれに従ってください。

3. プロジェクトルートに `data/` ディレクトリを作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（Settings が要求するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行時に使う可能性のある環境変数（主なもの）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

   - .env の簡単な例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_token
     - KABU_API_PASSWORD=your_kabu_password
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=development
     - PAPER_FILL_MODE=instant

5. データベース初期化
   - run_monitoring / run_execution の起動時に必要なテーブルは起動スクリプトが自動で作成（init_monitoring_db）します。DuckDB 側は該当テーブルがあることを前提に動きますので、prices_daily/raw_financials 等のデータは事前に準備してください（リサーチ・AI モジュール利用時）。

---

## 使い方（主要な起動コマンド）

プロジェクトルートで実行します。パッケージとして実行可能なので `python -m kabusys.<module>` 形式で起動できます。

- 監視ループ（SystemMonitor をポーリング）
  - MONITOR_POLL_INTERVAL 秒（環境変数）でポーリング。デフォルト 60 秒。
  - Stop フラグ: data/stop_requested.flag が存在するとループを終了します。
  - 実行:
    - python -m kabusys.run_monitoring
  - 例（ポーリング 30 秒）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は paper_trading 用に分離（data/paper_trading.db）。
  - 起動前に data/kill.flag が存在すると起動を行わず終了します（KillSwitch により停止シグナルが立った状態）。
  - ExecutionEngine の PID ファイル: data/execution.pid に書き込まれます（停止時や stale PID を検出した場合は削除されます）。
  - 実行:
    - python -m kabusys.run_execution
  - Paper trading で起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード（監視 DB の読み取り専用ビュー）
  - 起動コマンド例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読むレポート生成スクリプト。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を明示的に指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。各関数は DuckDB 接続と target_date を受け取って実行します。
  - 例（プログラム内呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, date(2026, 4, 1), api_key="sk-...")

---

## 運用に関するポイント

- KillSwitch / stop フラグ
  - KillSwitch はリスク条件（ドローダウン・ポジション上限）に応じて `data/kill.flag` を書き込み、ExecutionEngine 側は起動確認時やランタイムでこのフラグを検出して安全に停止します。
  - 手動で ExecutionEngine を停止させたい場合は `data/stop_requested.flag` を作成すると run_execution の監視ループが検出して停止します（run_monitoring では同様の stop フラグも使用）。

- 本番/ペーパーの分離
  - KABUSYS_ENV によって挙動が切り替わります。`paper_trading` では MockBroker と専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離されます。
  - 監視（Monitoring）は環境に関係なく本番 sqlite_path を使用する設計部分があります（注意して運用してください）。

- ログレベル
  - Settings.log_level で LOG_LEVEL を調整できます（DEBUG/INFO/...）。起動スクリプトは logging.basicConfig(level=logging.INFO) を設定しています。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB に対する簡易的なカラム追加マイグレーション（例: peak_value, latency_ms）を行います。

---

## 環境変数（主なもの）

- 必須（実行環境により必須となる）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API パスワード（Settings.kabu_api_password）

- 推奨 / 使用される
  - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
  - OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
  - SQLITE_PATH — 監視 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL — 監視ループ間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
  - PID_FILE_PATH / KILL_FLAG_PATH — ファイルパス上書き可能

---

## ディレクトリ構成（抜粋）

src/kabusys 以下を中心に説明します（主要ファイルのみ抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings の実装（.env 自動読み込み機能あり）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化 API（MonitoringDB）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — 停止フラグ生成ロジック
    - alert_manager.py       — LINE 通知
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード（読み取り専用）
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - execution_engine.py
    - broker_factory.py
    - (その他発注関連)
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
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ

- data/
  - monitoring.db            — デフォルト監視 SQLite（起動時に自動作成）
  - paper_trading.db         — Paper Trading 用 DB（paper_trading 時に使用）
  - kabusys.duckdb           — DuckDB（時系列価格・raw_news 等）
  - execution.pid            — ExecutionEngine の PID（起動時に作成）
  - kill.flag / stop_requested.flag — 各種停止フラグ

---

## 開発・テストに関する補足

- .env のパースは複雑なエスケープや引用を考慮した独自実装が組み込まれており、.env/.env.local の読み込み順序は OS 環境変数 > .env.local > .env です（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能）。
- process_priority.set_process_priority() により起動直後にプロセス優先度が設定されます。権限不足等で設定できない場合は警告が出ますが動作は継続します。
- AI 周りは外部 API（OpenAI）に依存するためキーの管理と API 利用料金に注意してください。API 呼び出しはリトライ／フォールバック設計が施されています（429/タイムアウト/5xx に対する指数バックオフ等）。
- DuckDB を用いたリサーチ関数は prices_daily / raw_financials 等のテーブルを前提にしています。テスト用に小さなサンプルデータを用意しておくと良いです。

---

## 参考: よく使うコマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb psutil requests openai streamlit

- 監視プロセス起動
  - python -m kabusys.run_monitoring

- 発注エンジン起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、この README をもとに .env.example のテンプレート、docker-compose / systemd ユニットのサンプル、あるいは実行フロー図（監視 → kill switch → execution の相互作用）を追補します。どの形式が必要か教えてください。