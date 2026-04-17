KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした軽量なPythonライブラリ群です。本リポジトリは以下の主要機能を提供します。

- 注文発行・状態管理・リコンシリエーション（ExecutionEngine 周り）
- 監視（System / Trade / Risk）のポーリングとログ保存（SQLite）
- Paper Trading 環境の切替・モックブローカー対応
- ポートフォリオ構築（銘柄選定、重み付け、サイズ計算、セクター制限）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- ニュースを用いた LLM ベースのセンチメントスコアリング（OpenAI）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

主な機能一覧
-------------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 DB に記録
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止
- 監視エンジン起動スクリプト: run_monitoring.py
  - SystemMonitor を定期実行して system_status / trade_logs / risk_logs / dashboard 等へ記録
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を変更可（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウンやポジション上限の検出と dashboard 更新
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書込とLINE通知
- Portfolio モジュール
  - 銘柄選定、等金額／スコア重み付け、リスクベースのサイズ計算、セクターキャップ、レジーム乗数
- Research モジュール
  - DuckDB を参照してファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリー等
- AI モジュール
  - news_nlp: raw_news を集約し OpenAI で銘柄ごとのセンチメントを計算・ai_scores に保存
  - regime_detector: ETF (1321) の MA200 とマクロニュース LLM を合成し市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視データの可視化）

前提 / 必要パッケージ
--------------------
主な依存ライブラリの例（requirements.txt を作ることを推奨）:
- python >= 3.9
- duckdb
- psutil
- requests
- openai（OpenAI の Python SDK）
- streamlit (ダッシュボードを使う場合)
- その他: sqlite3 は標準ライブラリに含まれます

セットアップ手順
---------------
1. リポジトリをクローン / ソースを取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて requirements.txt を用意して pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれる（既定: OS > .env.local > .env）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な（代表的な）環境変数:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用）
     - OPENAI_API_KEY — OpenAI を使う機能で必要
     - KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトを確認）
     - PAPER_FILL_MODE — paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
   - 例 .env 内容:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb

使い方（コマンド例）
------------------

- 監視ループ起動
  - 簡易:
    - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成するとループ終了（scripts 内でフラグ操作）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / 開発:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（Mock Broker、DB を分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 注意:
    - paper_trading の場合はデフォルトで data/paper_trading.db を使用（本番 DB から分離）
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - （--db を与えない場合は data/monitoring.db を使います）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も優先順で使用）

- AI / レジーム検出
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を直接呼ぶ（OpenAI API キーが必要）
  - 例（スクリプトから）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

主要ファイルとディレクトリ構成
------------------------------
（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 振る舞いあり）
  - ai/
    - news_nlp.py — raw_news を OpenAI で評価し ai_scores に書き込む
    - regime_detector.py — マクロ + MA200 を合成し market_regime に書込む
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite スキーマ初期化と永続化操作（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理（Execution 停止用）
    - alert_manager.py — LINE Push 通知ラッパ
    - monitoring_engine.py — 各モニタを束ねる実行ループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ... — 発注・同期・復旧ロジック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め・投下上限のスケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB を想定）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

監視 DB（SQLite）概要
--------------------
init_monitoring_db(conn) により次のテーブルが作成（冪等）されます:
- system_status: CPU / メモリ / ディスク / process_ok 等の履歴
- trade_logs: 発注イベントのログ（latency_ms 列含む）
- positions: 現在の保有（code 主キー）
- risk_logs: リスク関連イベント（DRAWDOWN_ALERT / STALE_ORDER 等）
- dashboard: 最新の集計（単一行、id = 1）

既存 DB のマイグレーション:
- dashboard に peak_value カラムがなければ追加
- trade_logs に latency_ms カラムがなければ追加

運用上の注意
------------
- .env 自動ロード:
  - OS 環境変数 > .env.local > .env の優先順位で読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードをオフにできます（テスト時に有用）
- モニタリングは run_monitoring が本番の sqlite_path を直接使うため、監視用 DB を共有する場合は注意
- 実行プロセスの優先度変更:
  - set_process_priority() は psutil を使い Windows / POSIX の差分を吸収するが、権限により失敗する場合があります（ログ警告）
- OpenAI API:
  - API レスポンス失敗時はフェイルセーフで処理を続行する設計（部分失敗で既存データを消さない工夫あり）
  - OPENAI_API_KEY を確実に設定してください
- 停止フラグ:
  - data/stop_requested.flag や data/kill.flag を用いてプロセスに停止シグナルを送ります。実行中の Engine はそれらを検知して安全に終了します。

開発・拡張のヒント
------------------
- DuckDB を使って prices_daily / raw_financials / raw_news 等の表を用意すると research / ai 機能をローカルで評価できます
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くように設計されています（URI + ?mode=ro を使用）
- テスト時は OpenAI 呼び出し関数（_call_openai_api 等）をモックして外部依存を切り離せます

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

以上。必要があれば README にインストール用 requirements.txt、サンプル .env.example、運用スクリプト（systemd など）例、より詳細な API 使用方法を追記します。どの部分を優先して追記しますか？