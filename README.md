KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。  
取引の実行エンジン（ExecutionEngine）、監視・アラート基盤（Monitoring）、ポートフォリオ構築・ポジションサイジング、ファクター計算・リサーチ、AI（ニュースセンチメント・レジーム判定）などのコンポーネントを含みます。設計上、実行ロジックとデータ処理はできるだけ分離されており、Paper Trading（検証）モードも用意されています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading 切り替え（KABUSYS_ENV）
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler 組み立て
  - paper_trading 時は専用 SQLite（data/paper_trading.db）へ記録し本番 DB と分離
- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン / 保有上限の監視とリスクログ化
  - KillSwitch: フラグファイル（data/kill.flag）を介した停止シグナル発行
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視ビュー）
- ポートフォリオ構築
  - 候補選定、等ウェイト・スコア加重、セクター上限適用、ポジションサイズ計算（単元株丸め、集約上限等）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント（銘柄別）スコアリング（ai_scores へ書き込み）
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - 環境変数管理（.env 自動読込）、プロセス優先度 / CPU affinity 設定、Monitoring DB 初期化・マイグレーション

動作要件（推奨）
----------------
- Python 3.9+
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit（ダッシュボード利用時）
  - openai（AI 機能利用時）
  - sqlite3（標準ライブラリ）
- OS: Linux / macOS / Windows（ただし一部優先度設定は OS により挙動が異なります）

セットアップ手順
----------------
1. リポジトリをクローン（省略）
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 必要ライブラリをインストール（例）
   - pip install duckdb psutil requests streamlit openai
   実際のプロジェクトでは requirements.txt を用意していることを想定してください。
4. 環境変数の設定
   - プロジェクトルートに .env を配置すると自動でロードされます（OS 環境変数が優先、.env.local は上書き）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. 必須環境変数（用途別）
   - J-Quants API: JQUANTS_REFRESH_TOKEN
   - kabuステーション API: KABU_API_PASSWORD, 必要に応じて KABU_API_BASE_URL
   - OpenAI（AI 機能）: OPENAI_API_KEY
   - LINE 通知（任意）: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - 環境選択: KABUSYS_ENV (development | paper_trading | live)
   - Paper Trading 切替のため: PAPER_TRADING_SQLITE_PATH（任意）
   - Paper Trading 動作設定: PAPER_FILL_MODE (instant | partial | never | reject)
6. データベース初期化
   - monitoring 用 SQLite（デフォルト: data/monitoring.db）は run_monitoring/run_execution の起動時に init_monitoring_db によって自動作成・マイグレーションされます。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- SQLITE_PATH: monitoring 用 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を削除する場合は "1"
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で上書き可能、デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知

実行方法（例）
--------------
- 監視ループ起動（Monitoring）
  - 環境変数で間隔を上書き可能: MONITOR_POLL_INTERVAL=30
  - 起動コマンド: python -m kabusys.run_monitoring
  - 補足: run_monitoring は Settings に従い sqlite/duckdb に接続し SystemMonitor を定期実行します。

- 実行エンジン起動（Execution）
  - Paper Trading にする場合:
    - export KABUSYS_ENV=paper_trading
    - (任意) export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - 起動コマンド: python -m kabusys.run_execution
  - 補足: 起動時に Process 優先度を high に設定し、OrderManager / RiskManager / Reconciler を構成して ExecutionEngine を実行します。

- Streamlit ダッシュボード
  - 起動コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データは監視用 SQLite を read-only で参照します（MonitoringEngine がデータを作成している必要あり）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で指定可能。

- AI (ニューススコア / レジーム判定)
  - モジュール関数を直接呼ぶことができます（DuckDB 接続が必要）。
  - 例（Python REPL）:
    - from openai import OpenAI などを設定後、
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

ログ・監視関連の挙動メモ
-----------------------
- MONITOR_POLL_INTERVAL: run_monitoring が参照する環境変数（秒）。1 未満や不正値を与えるとデフォルト 60 秒にフォールバックします。
- KillSwitch: RiskMonitor が条件を満たした場合（例: ドローダウン超過、ポジション数超過）に data/kill.flag を作成します。ExecutionEngine 側は起動時に kill.flag の有無をチェックし、KILL_FLAG_CLEAR_ON_START により起動時クリアを制御できます（安全上の運用ルールにご注意ください）。
- AlertManager: LINE token / user_id 未設定時は送信をスキップしてログのみ出力します。送信は (level, category) 毎に cooldown をメモリ内で管理します。

DB スキーマ / マイグレーション
---------------------------
- init_monitoring_db(conn) により次のテーブルが作成・マイグレーションされます:
  - system_status, trade_logs, positions, risk_logs, dashboard
- 既存 DB に対するカラム追加（例: latency_ms, peak_value）は起動時にチェックして ALTER TABLE を実行します（冪等）。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py               — パッケージ定義、バージョン
  - config.py                 — Settings クラス (.env 自動ロード、環境変数ラッパ)
  - run_monitoring.py         — SystemMonitor のポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（初期化 / CRUD ユーティリティ）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — LINE 通知ラッパ
    - monitoring_engine.py    — 各 Monitor を束ねるループ
    - streamlit_dashboard.py  — streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py        — 注文状態管理（OrderManager）
    - reconciler.py           — 起動時リコンシリエーション
    - ...                     — （ブローカー / order_repository 等の実装）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 株数計算・単元丸め・集約キャップ
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュースの LLM センチメントスコアリング
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力

開発者向けノート
-----------------
- .env の自動読み込みは Settings モジュール内で行われます。CWD に依存せず、パッケージの位置からプロジェクトルート（.git / pyproject.toml）を探索して .env / .env.local を読み込みます。
- process_priority.set_process_priority は psutil を利用して OS 毎に差分を吸収します。権限不足時は警告を出してスキップします。
- AI 関連の OpenAI 呼び出しはリトライ・JSON バリデーションなどを含む頑健化がなされていますが、APIキーやレートに注意してください。
- DuckDB 接続は read-only URI を使って streamlit から安全に参照できます（例: sqlite の場合と同様にファイル URI を使用）。

ライセンス・責任
----------------
- 本ドキュメントはコードベースから抽出した情報に基づく概略説明です。実運用では十分なテスト・監査を行ってください。金融取引に関わるコードを使用する場合は自己責任で扱ってください。

補足（よくある操作）
-------------------
- MONITOR_POLL_INTERVAL を 30 秒に設定して監視ループを短くする:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper Trading DB を指定して検証レポートを出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

以上。README に記載がない細かい挙動は各モジュールの docstring を参照してください。