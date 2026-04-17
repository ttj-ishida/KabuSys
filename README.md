# KabuSys

KabuSys は日本株向けの自動売買・検証プラットフォームの一部実装です。本リポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのモジュール群を含みます。

> バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- 自動発注の実行管理（ExecutionEngine / OrderManager / Reconciler）
- 実行・約定の監視とアラート（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 等）
- ニュースの LLM ベースセンチメント解析と市場レジーム判定（OpenAI）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit による監視ダッシュボード

設計上のポイント:
- 環境変数や .env ファイルで設定を管理（自動ロード機能あり）。
- Paper Trading は本番 DB と完全分離（`data/paper_trading.db` を使用）。
- OpenAI 呼び出しはフェイルセーフ（失敗時はスコア 0.0 等で継続）。
- モジュールは可能な限り純粋関数または DB/外部依存を明確に分離。

---

## 機能一覧

- Execution
  - OrderManager：発注作成・状態管理
  - Reconciler：再起動時の注文・ポジション突合せ
  - BrokerFactory：環境に応じたブローカークライアント生成（paper_trading では Mock）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウンやポジション上限の監視
  - KillSwitch：条件に応じて停止フラグ（data/kill.flag）を書き込み
  - AlertManager：LINE Push による通知（クールダウン制御）
  - Streamlit ダッシュボード（読み取り専用で監視情報表示）
- Portfolio
  - 候補選定、等重 / スコア重み、リスク調整（セクターキャップ / レジーム乗数）、株数決定・集約上限処理
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp: raw_news を LLM でセンチメント計算し ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースセンチメントの合成で市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを出力

---

## 要件（例）

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）
- SQLite（標準ライブラリ）

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

例:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` からロードされます。
自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須 / 重要な変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合、score_news/score_regime）
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）
- PAPER_FILL_MODE — paper_trading のマッチング動作: `instant` | `partial` | `never` | `reject`（デフォルト: `instant`）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH — KillSwitch のフラグファイル（デフォルト: `data/kill.flag`）
- LOG_LEVEL — ログレベル（`DEBUG`, `INFO`, ...）

Monitoring 固有（閾値等）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

モニタのポーリング間隔:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）。無効な値はデフォルトにフォールバック。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定する（.env を作成）
   - 例（.env）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
5. 必要なら `data/` ディレクトリを作成
   - mkdir -p data

注意:
- Monitoring DB や Paper Trading DB のスキーマは初回接続時にコード内で自動作成/マイグレーションされます（`init_monitoring_db` を実行）。

---

## 使い方（起動・ツール）

### 1) 実行エンジン（ExecutionEngine）を起動する
- 通常:
  - KABUSYS_ENV を指定して実行（paper_trading では MockBroker を使用）
  - 例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
- 注意:
  - 起動時に `data/stop_requested.flag` があると起動を行わず終了します（run_execution の停止フラグ）。
  - Execution は `data/execution.pid` を利用してプロセス存在チェックを行います。

### 2) 監視ループを起動する
- run_monitoring は SystemMonitor のポーリングループを実行します。
  - ポーリング間隔を変えるには `MONITOR_POLL_INTERVAL` を設定（秒。デフォルト 60）。
  - 例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - `data/stop_requested.flag` を作成するとループは検知して終了します。

### 3) Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示する GUI。
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB が存在しない・読み込めない場合はエラーメッセージが表示されます。

### 4) Paper Trading 検証レポート
- コマンドラインツール:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）

### 5) AI 関連
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同じく OPENAI_API_KEY 必須

---

## 停止・フラグ管理

- run_execution/run_monitoring はプロジェクトルートの `data/stop_requested.flag`（run_* 内）を参照して終了判定を行います。
- KillSwitch は `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）を書き込んで ExecutionEngine 停止の要求を行います。
  - KillSwitch の生成＆評価は Monitoring 側で行われ、ファイルが既に存在すれば上書きせず冪等性を保持します。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START` が `1` に設定されていれば起動時にフラグをクリアする挙動等を組み合わせ可能。

---

## 注意事項 / 運用上のヒント

- Paper Trading では本番 DB と完全に分離して `PAPER_TRADING_SQLITE_PATH` を使うため本番データを汚さないようになっています。
- OpenAI の呼び出しはレートリミット・一時エラーを考慮したリトライ実装（指数バックオフ）がありますが、API キーの管理とコストに注意してください。
- プロセス優先度や CPU affinity は `kabusys.utils.process_priority` から設定されます。権限不足で失敗した場合は警告が出ますが処理自体は続行します。
- DuckDB はリサーチ・AI 周りで価格・財務テーブルを高速に参照する用途で使用します。prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- ログレベルは `LOG_LEVEL` で制御できます（`INFO` がデフォルト）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — 環境変数 / 設定管理（.env 自動ロード・検証）
- run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて動作）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義と簡易永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止フラグの読み書きユーティリティ
  - alert_manager.py — LINE Push 通知クラス
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - reconciler.py — 再起動時の注文・ポジションリコンシリエーション
  - order_manager.py — 発注の外向 API（OrderManager）
  - （その他: order_repository, execution_engine 等）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数決定・集約上限ロジック
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー算出
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/（実行時に使用するファイルを配置）
  - monitoring.db（SQLite）
  - paper_trading.db（Paper Trading 用 SQLite）
  - kabusys.duckdb（DuckDB）
  - execution.pid, kill.flag, stop_requested.flag など

---

## 実装上の注記（開発者向け）

- config.py はプロジェクトルートを `.git` や `pyproject.toml` を基準に自動検出して .env をロードします（CWD に依存しない挙動）。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB に対してのマイグレーション（カラム追加）も行います。
- news_nlp / regime_detector は OpenAI 呼び出し部分をラップしており、テスト時は `_call_openai_api` をモックする想定です。
- 多くのモジュールは「DB 接続 / クライアントを引数で受け取る」設計になっているためユニットテストで差し替えが容易です。

---

## よく使うコマンド例

- Execution 起動（paper_trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含める `.env.example` のテンプレートや運用フロー（起動シーケンス、監視→KillSwitch → Execution 停止のフロー図）も作成します。どうしますか？