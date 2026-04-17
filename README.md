# KabuSys

日本株向け自動売買システムのコードベース。  
この README はリポジトリ内の主要機能、セットアップ方法、起動方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の責務を持つモジュール群で構成されたシステムです。

- Execution（発注エンジン）：ブローカーと連携して注文を作成・管理する ExecutionEngine、OrderManager、OrderRepository など。
- Monitoring（監視）：システム状態、注文滞留、ドローダウン等を定期的にチェックしログ化 / アラート送信する監視コンポーネント群。
- Research（調査）：DuckDB 上の時系列データからファクター計算・特徴量生成を行う研究用ツール。
- AI：ニュースを LLM（OpenAI）で評価して銘柄センチメントを生成したり、市場レジーム判定を行うモジュール。
- Portfolio：銘柄選定・ウェイト計算・ポジションサイジング等のポートフォリオ構築ロジック。
- Tools：Paper Trading の検証レポート生成などのユーティリティスクリプト。

設計上、監視ログは SQLite、時系列・リサーチ用の大容量データは DuckDB に保存します。Paper Trading（模擬取引）用に本番データベースと分離した SQLite を利用する構成になっています。

---

## 主な機能一覧

- Execution
  - 発注フローの管理（OrderManager、ExecutionEngine）
  - 再起動時のリコンシリエーション（Reconciler）
  - Risk Manager（発注数・資金利用率等の制限）
- Monitoring
  - システムリソースとプロセスの監視（SystemMonitor）
  - 注文の滞留 / 約定異常の監視（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - アラート送信（LINE via AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI
  - ニュースを LLM でスコアリングして ai_scores に保存（news_nlp）
  - マクロ + ETF 200 日移動平均を用いた市場レジーム判定（regime_detector）
- Tools
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）

---

## 前提（動作環境）

- Python 3.9+（型ヒントや一部機能により 3.9 以上を推奨）
- SQLite（Python に同梱）
- 以下の外部ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- ネットワークアクセス（OpenAI/API を使用する場合）
- （任意）LINE Messaging API のチャネルアクセストークン / ユーザー ID（アラート送信に利用）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてルートに移動
   - git clone ...
   - cd <repo>

2. Python 仮想環境を作成 / 有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（pip）
   - pip install duckdb psutil requests openai streamlit

   ※requirements.txt がない場合は上記を個別にインストールしてください。プロジェクトで別の依存があれば追加でインストールしてください。

4. データディレクトリの作成
   - mkdir -p data

5. 環境変数の設定
   - ルートに `.env` または `.env.local` を作成して必要な環境変数を設定できます。
   - 自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）

---

## 必要な環境変数（主なもの）

以下は主要な設定キーとデフォルト値の例です。実行前に環境変数または .env で適切に設定してください。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 起動モード: development | paper_trading | live（デフォルト: development）
  - paper_trading のときは paper 用 SQLite（data/paper_trading.db）を使用
- PAPER_FILL_MODE — paper_trading 時の約定挙動（instant|partial|never|reject） デフォルト: instant
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag（Execution 停止シグナル）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

例（.env）:
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
JQUANTS_REFRESH_TOKEN=...

---

## 使い方（起動・実行例）

- Execution Engine を起動
  - 本番相当:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（例: MONITOR_POLL_INTERVAL=30）

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 事前に MonitoringEngine を起動して監視データを書き込ませておくと表示が有効になります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

- AI 系バッチ
  - ニュースのスコアリング: kabusys.ai.score_news (Python API). 例:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime（同様に Python API 経由で呼び出し）

- 停止フラグ / Kill Switch
  - Execution や Monitoring を強制停止させたい場合は `data/stop_requested.flag`（Monitoring の run loop 停止用）や `data/kill.flag`（Execution 停止指示）を作成します。KillSwitch は条件に応じて `data/kill.flag` を自動生成します。
  - `data/kill.flag` を削除してクリアするには、KillSwitch.clear() を利用するか手動でファイルを削除してください。

---

## 注意事項 / 運用上のポイント

- Paper Trading モードでは本番用 DB と完全に分離されるよう設計されていますが、環境変数の設定ミスに注意してください。
- OpenAI API を利用する処理は API エラー・レート制限に対してバックオフ/フォールバックを実装していますが、API キーの漏洩やコストに注意してください。
- Process priority / CPU affinity の設定を行います（psutil を使用）。権限不足により設定に失敗する場合はワーニングが出ます。
- DuckDB / SQLite のファイルパスは Settings によりカスタマイズ可能です。大量データを扱う場合は十分なディスク容量を確保してください。

---

## 主要ファイル・ディレクトリ構成

（ルートは `src/kabusys` を想定）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/
    - order_manager.py, reconciler.py, ... — 発注周りの主要コンポーネント（OrderRepository 等はこの配下）
  - monitoring/
    - monitoring_db.py — 監視ログ（SQLite）永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — フラグファイル生成による停止シグナル
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — DuckDB を使ったファクター計算 & 解析
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング
    - regime_detector.py — 市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - data/ （実行時に使用するファイル・フラグ）
    - kabusys.duckdb （デフォルトの DuckDB）
    - monitoring.db （監視 SQLite）
    - paper_trading.db （paper_trading 用 SQLite）
    - execution.pid （Execution の PID ファイル）
    - kill.flag / stop_requested.flag — 停止フラグ

---

## 開発・デバッグヒント

- 設定は `kabusys.config.Settings` を参照してください。環境変数の取り扱い（.env の自動読み込み）に注意。
- DuckDB 接続はパフォーマンス上重要な箇所があるため、分析系のクエリは `research` 内でまとめて実行されるよう設計されています。
- AI 部分（news_nlp / regime_detector）は外部 API に依存するため、ユニットテストでは `_call_openai_api` をモックしてください（ファイル内にその旨の注記があります）。
- 監視ループや Execution の停止は `data/stop_requested.flag` や `data/kill.flag` を用いることで外部から制御できます。

---

もし README に追加してほしい情報（例：具体的な .env.example、CI/CD 設定、より詳細な起動手順やデータベースマイグレーション手順など）があれば教えてください。必要に応じて追記します。