# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部モジュール群です。  
README はコードベース（src/kabusys 以下）に基づいて、日本語でプロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

注意: 本 README は提供されたソースコードスニペットをもとに作成しています。実行には追加のモジュールや設定ファイルが必要な場合があります。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・モニタリングのためのライブラリ/ツール群です。主な目的は以下:

- 注文管理・発注（ExecutionEngine、OrderManager、Reconciler 等）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- ポートフォリオ構築（候補選定・重み・ポジションサイズ計算・リスク調整）
- 研究用ファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- Paper Trading 検証用レポート生成、Streamlit による監視ダッシュボード

設計方針の一部:
- DuckDB/SQLite を用いたローカル分析・監視
- 環境変数／.env による設定管理
- 実行プロセスの優先度設定・PID 管理・kill.flag による安全停止
- AI 呼び出し（OpenAI）に対するリトライ・バリデーションを備えたフェイルセーフ実装

---

## 機能一覧

- Execution
  - 起動エントリ: `kabusys.run_execution`
  - Broker クライアントを切り替え可能（本番 / paper_trading）
  - OrderManager、OrderRepository、RiskManager、Reconciler 等を組み合わせた実行フロー
- Monitoring
  - 起動エントリ: `kabusys.run_monitoring`
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格を検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新
  - KillSwitch: 条件により `data/kill.flag` を書き、ExecutionEngine に停止シグナル
  - AlertManager: LINE Push による通知（設定があれば）
  - Streamlit ダッシュボード: `monitoring/streamlit_dashboard.py`
- Portfolio construction
  - 候補選定（スコア/ランク）、等重・スコア重み配分
  - セクター制限、レジーム乗数適用
  - ポジションサイズ計算（ロット丸め、リスクベース、利用可能現金によるスケール）
- Research
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン計算、IC（Spearman rank）や統計サマリー
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメントスコアリング: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（ma200 + マクロセントメント合成）: `kabusys.ai.regime_detector.score_regime`
- Tools
  - Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`
- Utilities
  - 環境変数/.env ロードと Settings 管理
  - プロセス優先度・CPU affinity 制御ユーティリティ (`kabusys.utils.process_priority`)
  - Monitoring 用の SQLite 永続層（テーブル自動作成 / マイグレーション）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈や構文から推奨）
- DuckDB、psutil、requests、openai、streamlit などの依存が必要

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を利用してください。

3. 環境変数 / .env の準備
   - ルートに `.env` または `.env.local` を置くと自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合は必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE（paper_trading 時の挙動）: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（monitoring 用 SQLite、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill flag、デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト: 60）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用、未設定時は通知スキップ）

   - Settings モジュールは .git か pyproject.toml を基準にプロジェクトルートを検索し、.env/.env.local を読み込みます。

4. データディレクトリ作成
   - mkdir -p data

---

## 使い方

以下は一般的な起動例です。コードは `src/kabusys` パッケージを前提としています（パッケージとしてインストールしている場合は `-m` で実行）。

1. Monitoring（監視ループ）の起動
   - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書きできます（例: 30）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 実行内容:
     - process 優先度を "high" に設定し、監視用 SQLite と DuckDB に接続、SystemMonitor のポーリングループを回します。
     - 監視情報は monitoring DB（デフォルト: data/monitoring.db）の system_status、risk_logs、trade_logs、positions、dashboard に記録されます。

2. Execution（取引エンジン）の起動
   - KABUSYS_ENV によって挙動が変わります:
     - paper_trading: MockBrokerClient を使用し、Paper trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB とは分離されます。
     - live/development: 本番 DB を使用する想定
   - 実行:
     - python -m kabusys.run_execution
   - 実行内容:
     - process 優先度設定、BrokerClient 作成、OrderRepository 等を組み立てて ExecutionEngine を起動します。
     - 起動時に Reconciler（注文/ポジションの同期）を実行します。

3. Paper Trading 検証レポートの生成
   - スクリプト: `kabusys.tools.paper_verification_report`
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション `--db PATH` で DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
   - 出力: 標準出力に稼働率・注文成功率・送信率・レイテンシ等の集計と PASS/FAIL 判定を表示します。

4. Streamlit ダッシュボード
   - 起動方法:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 機能:
     - ダッシュボード、現在のポジション、最近の注文、最新のシステムステータス、最近のリスクイベントなどを表示します。
   - 注意: Streamlit 実行時は monitoring DB を読み取り専用で開きます（URI `?mode=ro`）。

5. AI 関連（ニュースセンチメント / レジーム判定）
   - 環境変数または引数で `OPENAI_API_KEY` を設定してください。
   - ニューススコアリング:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（日付）を渡すと ai_scores テーブルに書き込みます。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB 接続と target_date を渡すと market_regime テーブルに冪等書き込みします。
   - 実装上の特徴:
     - バッチ（最大 20 銘柄）で OpenAI に問い合わせ、429 やネットワークエラー・5xx に対して指数バックオフでリトライ。
     - レスポンスの厳密なバリデーションとスコアのクリッピング（±1.0）。
     - API 失敗時はフェイルセーフ（部分スキップや 0.0 で継続）をとっています。

6. 環境変数/設定の特記事項
   - .env の自動ロード:
     - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` を読み込み、`.env.local` があればそれで上書きします。
     - OS 環境変数は保護され `.env` による上書きを防ぎます。
     - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - MONITOR_POLL_INTERVAL:
     - 監視ループの sleep 間隔を秒で指定（整数 >=1）。無効値はデフォルト 60 秒にフォールバック。
   - PAPER_FILL_MODE:
     - paper_trading モードの MockBroker の挙動指定（instant, partial, never, reject）。不正値は例外。
   - KILL / PID:
     - ExecutionEngine は起動時に PID を `PID_FILE_PATH` に書き、KillSwitch は `KILL_FLAG_PATH` を作成して停止を促します。
     - `KILL_FLAG_CLEAR_ON_START` を 1 にすると起動時に kill.flag を自動削除します。

---

## 主要なテーブル（監視 DB: init_monitoring_db が作成）

- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の1行、portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value 等)

init_monitoring_db() は冪等でテーブルと必要なカラムを作成/マイグレーションします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス（環境変数読み込み・検証）
- run_monitoring.py
  - SystemMonitor をポーリング起動するスクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading ブランチあり）
- ai/
  - news_nlp.py （ニュース NLP スコアリング）
  - regime_detector.py（市場レジーム判定）
- monitoring/
  - monitoring_db.py（SQLite 永続層）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照あり)
  - execution_engine.py (参照あり)
  - broker_factory.py (参照あり)
  - broker_api.py (参照あり)
  - order_record.py (参照あり)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py（関数群エクスポート）
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py（zscore_normalize を data.stats から取り込む）
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py（プロセス優先度・CPU affinity 設定）
- data/ （既定のデータパス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）

（上記はコードベースの主要ファイルの抜粋です。Execution 系の詳細実装（Engine、OrderRepository、Broker 実装等）は省略されていますが、本 README の使い方に対応しています。）

---

## 開発・デプロイに関する注意点

- OpenAI API を用いる機能は API キーの管理に注意してください（コスト・レート制限）。
- paper_trading モードは本番 DB と完全分離されるよう設計されています。Paper trading 用 DB パスを確実に指定してください。
- Monitoring / Execution 両方で SQLite / DuckDB ファイルにアクセスします。ファイルロックや同時接続に注意してください（運用環境では別プロセスで接続するため read-only オプション等を利用）。
- プロセス優先度の設定はプラットフォーム依存で失敗する場合があります（権限不足など）。`psutil` に依存します。
- Streamlit ダッシュボードは監視 DB を read-only で開きます（起動エラーメッセージ参照）。

---

必要に応じて README の補足（例: .env.example、依存関係ファイル、実行フロー図、ユニットテストの実行手順）を追加できます。どの情報を詳細化したいか教えてください。