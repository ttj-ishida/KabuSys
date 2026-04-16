# KabuSys

日本株自動売買システム（部分実装）。このリポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース/NLP）などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するコンポーネント群を提供します。主な機能は次のとおりです：

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム状態・注文滞留・リスク監視、アラート送信）
- Portfolio construction（候補選定、重み計算、ポジションサイズ決定）
- Research（ファクター計算、特徴量解析）
- AI サブシステム（ニュースセンチメント：OpenAI を利用）
- ユーティリティ（プロセス優先度設定、DB 初期化、Streamlit ダッシュボード 等）

設計方針の一部：
- DuckDB（時系列データ・リサーチ）と SQLite（監視ログ・紙トレード用DB）を併用
- Paper trading 環境は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI を用いた NLP モジュールは API キーが必要（フォールバックやリトライ処理あり）
- .env ファイルの自動読み込み機能あり（プロジェクトルートを探索）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV によって paper_trading（モックブローカー）と live を切り替え。
  - 起動時に再同期（Reconciler）やリスク制御（RiskManager）を行う。
- run_monitoring.py
  - SystemMonitor をポーリングして system_status 等を SQLite に記録。MONITOR_POLL_INTERVAL で間隔を指定可能。
- Monitoring サブシステム
  - SystemMonitor / TradeMonitor / RiskMonitor による監視
  - AlertManager（LINE push）による通知
  - KillSwitch によるフラグファイルベースのエンジン停止
  - streamlit_dashboard.py による簡易ダッシュボード
- Portfolio モジュール
  - 候補選定、重み計算（等配分 / スコア加重）、ポジションサイズ算出、セクター上限適用、レジーム乗数
- Research モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリー
- AI モジュール
  - news_nlp: raw_news を集約し OpenAI により銘柄別センチメントを算出、ai_scores テーブルへ保存
  - regime_detector: ma200 乖離 + マクロニュースの LLM センチメントで市場レジーム判定
- tools
  - paper_verification_report.py: Paper Trading DB を集計して検証レポートを出力

---

## セットアップ手順

前提：Python 3.9+ を想定（duckdb, openai 等が必要）。

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主なライブラリ例：
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数／.env
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（アプリ起動に必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合：
     - OPENAI_API_KEY
   - その他の主要な環境変数（デフォルト値はコード内参照）：
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ポーリング秒数, default 60）
     - LOG_LEVEL（DEBUG/INFO/...）

4. データディレクトリ
   - デフォルトで `data/` 以下に .db やフラグファイルが置かれます。必要に応じて作成してください。
   - 例: mkdir -p data

5. DB 初期化
   - monitoring 用の SQLite テーブルは各スクリプト起動時に自動初期化（init_monitoring_db）されます。DuckDB のスキーマは外部パイプラインやスクリプトから準備してください。

---

## 使い方

いくつかの主要なコマンド例を示します。

- ExecutionEngine を起動
  - 本番（live）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper trading（モックブローカー、DB を分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行フロー: プロセス優先度を上げ、DB に接続、ブローカーを生成して ExecutionEngine を別スレッドで実行します。
  - 停止:
    - data/stop_requested.flag を作成すると run_execution は検知して停止します。
    - KillSwitch（監視が書き込む data/kill.flag）を使うと安全に停止させることができます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings（環境設定）を読み取り、monitoring 用の SQLite（settings.sqlite_path）を開いて init_monitoring_db を呼び出します。
    - SystemMonitor を作成してポーリング（デフォルト 60 秒）。MONITOR_POLL_INTERVAL で上書き可能。
    - stop 用フラグ: data/stop_requested.flag を検知するとループを抜けて終了します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db PATH を使って PAPER_TRADING_SQLITE_PATH を上書きできます。
  - 出力: 稼働率、注文成功率、送信率、レイテンシ指標、PASS/FAIL 判定等。

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定して利用してください。
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行。
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API 呼び出しはリトライ（429/5xx 等）を含むが、API キー未設定時は ValueError を投げます。

---

## 主要な設定（環境変数の概要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時 必須)
- KABUSYS_ENV (default: development) — development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動
- PID_FILE_PATH / KILL_FLAG_PATH / MONITOR_POLL_INTERVAL / LOG_LEVEL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効にできます。

---

## 停止・フラグファイル

- data/stop_requested.flag
  - run_execution / run_monitoring のスクリプト内で監視され、存在するとループを抜けて終了します（ユーザ手動停止用）。
- data/kill.flag
  - KillSwitch が書き込み、ExecutionEngine に対する停止要求を表します。ExecutionEngine 起動時にこのフラグをクリアするオプションが設定されています（Settings.kill_flag_clear_on_start）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント算出（OpenAI 利用）
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py — 複数モニタの統合ポーリング
  - alert_manager.py — LINE push 通知
  - kill_switch.py — kill.flag 生成・管理
  - streamlit_dashboard.py — GUI ダッシュボード
- execution/
  - reconciler.py — 起動時の注文・ポジションリコンシリエーション
  - order_manager.py — 発注フロー、状態遷移管理
  - （他：broker_factory, execution_engine, order_repository 等は実コードベースに含まれます）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は本リポジトリに含まれる主要ファイルの抜粋です）

---

## トラブルシューティング / 注意点

- psutil による優先度設定や CPU affinity は OS によって挙動が異なります。権限不足で設定できない場合は警告を出してスキップします。
- DuckDB / SQLite のファイルパスは Settings により指定します。読み取り専用で開きたい場合は streamlit のコマンドのように URI に ?mode=ro を付ける方法があります。
- OpenAI API 呼び出しはレート制限や一時的なネットワークエラーを考慮し、標準的なリトライロジックを実装しています。API キーを厳重に管理してください。
- Paper Trading は本番 DB と分離するため、PAPER_TRADING_SQLITE_PATH を必ず確認してください。
- monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書きできます。0 以下を指定するとデフォルトにフォールバックします。

---

以上がコードベースの利用開始手順とコンポーネント概要です。必要であれば各モジュール（ExecutionEngine の起動引数、OrderRepository の DB スキーマ、DuckDB のテーブル定義等）についてさらに詳しいドキュメントを作成します。どの部分を優先して詳述しましょうか？