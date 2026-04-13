KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買システム「KabuSys」のコアライブラリ群です。
戦略・ポートフォリオ構築、Execution エンジン、監視/アラート周り、研究用ユーティリティ、ニュースの NLP スコアリングなどを含みます。

以下は本コードベースの概要・機能・セットアップ・使い方・ディレクトリ構成の説明です。

プロジェクト概要
----------------
- 目的: 日本株の自動売買を安全に運用するためのコンポーネント群（Execution / Monitoring / Portfolio / Research / AI）。
- 設計方針:
  - 本番環境と Paper Trading を分離（Paper Trading は専用 SQLite を使用）。
  - DuckDB を用いたファクター計算・研究ワークフロー。
  - 監視機能は監視 DB（SQLite）へログを書き、LINE による通知や kill.flag による Execution 停止を提供。
  - LLM（OpenAI）を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）を備えるが、API失敗時はフェイルセーフで継続する設計。

主な機能一覧
-------------
- Execution（起動スクリプト: run_execution.py）
  - Broker クライアント生成（本番 or mock：KABUSYS_ENV=paper_trading 時は MockBrokerClient）。
  - OrderManager / OrderRepository / RiskManager / Reconciler を組み合わせた ExecutionEngine の起動。
  - Paper Trading モードはデータベースを分離（data/paper_trading.db 等）。

- Monitoring（run_monitoring.py, monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック。
  - TradeMonitor: 注文滞留・約定価格の異常検出。
  - RiskMonitor: ドローダウンやポジション上限監視、ダッシュボード更新。
  - KillSwitch: 条件に応じて data/kill.flag を書き Execution を停止させる。
  - AlertManager: LINE による通知（クールダウン管理）。
  - MonitoringEngine: 上記 Monitor を束ねたポーリングループ。
  - streamlit_dashboard.py: 監視 DB を可視化する簡易ダッシュボード（Streamlit）。

- Portfolio（portfolio パッケージ）
  - 候補選定、重み計算（等金額・スコア加重）、セクターキャップの適用、ポジションサイズ計算（単元株丸め・リスクベース等）。

- Research（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等） — DuckDB を用いて prices_daily / raw_financials を参照。
  - 将来リターン、IC（Information Coefficient）、統計サマリ等のユーティリティ。

- AI（ai パッケージ）
  - news_nlp: raw_news から銘柄ごとのニュースを集約し OpenAI でセンチメントスコアを算出し ai_scores に書き込む。
  - regime_detector: ETF（1321）の MA200 とマクロニュースセンチメントを合成して市場レジーム（bull / neutral / bear）を判定して記録。

- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity の設定（Windows / POSIX の差分吸収）。
  - config: 環境変数 / .env の読み込み・設定クラス（Settings）。

セットアップ手順
-----------------
1. 必要な Python バージョンを用意
   - Python 3.9+（コードは型アノテーション等を使用しているため新しめの 3.x を推奨）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必須パッケージのインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt が無い場合は上記を手動でインストール）

4. 環境変数設定
   - 環境変数は OS 環境変数、またはプロジェクトルートの .env / .env.local で設定可能。
   - 自動読み込みはデフォルトで有効。無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (news_nlp / regime_detector 用)
     - LINE_CHANNEL_ACCESS_TOKEN (通知用)
     - LINE_USER_ID (通知先)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper trading 用 SQLite, default: data/paper_trading.db)
     - PAPER_FILL_MODE (instant|partial|never|reject)
     - PID_FILE_PATH (実行中プロセスの PID 保存先, default: data/execution.pid)
     - KILL_FLAG_PATH (kill flag path, default: data/kill.flag)
     - MONITOR_POLL_INTERVAL（監視ループのポーリング秒数; run_monitoring では環境変数で上書き可）

5. データディレクトリ
   - デフォルトの DB/ファイルは data/ 以下を想定します。必要に応じてディレクトリを作成してください:
     - mkdir -p data

使い方（主要なスクリプト）
-------------------------

- ExecutionEngine を起動（本番または paper_trading）
  - 環境例（Paper Trading）:
    - export KABUSYS_ENV=paper_trading
    - export OPENAI_API_KEY=...
    - python -m kabusys.run_execution
  - 本番:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 実行は set_process_priority("high") を行い、SQLite / DuckDB に接続します。
  - Paper Trading の場合、専用の PAPER_TRADING_SQLITE_PATH が使用され、本番 DB と完全に分離されます。

- Monitoring を起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視データは sqlite (Settings.sqlite_path) に書き込まれます（monitoring は常に本番 sqlite_path を使用する設計）。

- Streamlit ダッシュボード（ローカルで監視 DB を閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI タスク（news scoring / regime scoring）
  - news_nlp.score_news(conn, target_date, api_key) を呼ぶ（内部で OpenAI API を使用）。
  - ai.regime_detector.score_regime(conn, target_date, api_key) で市場レジームの更新。
  - 注意: OPENAI_API_KEY が必要。API エラー時はフェイルセーフの挙動（0.0 で継続など）。

監視 DB（monitoring_db）について
---------------------------------
- init_monitoring_db(conn) により監視用テーブル群を作成します（冪等）。
- 主なテーブル:
  - system_status: CPU / memory / disk / process_ok / recorded_at
  - trade_logs: 注文イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms 等）
  - positions: 現在のポジション（code, qty, avg_price, current_price, updated_at）
  - risk_logs: リスクイベント（DRAWDOWN_ALERT, STALE_ORDER, PRICE_ANOMALY 等）
  - dashboard: 集計情報（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）
- これらは MonitoringDB クラス経由で読み書きする設計です。

主要な設計注意点（運用上のポイント）
-----------------------------------
- Paper Trading は専用 SQLite を使うため、本番 DB を破壊するリスクは低い。
- Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視は常に本番 DB を監視する想定）。
- kill.flag により Execution を安全に停止させる仕組みがある（KillSwitch）。Execution 側はこの flag を監視して停止する実装が想定される。
- process_priority（高優先度）や CPU affinity は psutil 経由で設定し、権限がない環境では警告を出してスキップする。
- OpenAI API 呼び出しはリトライ・バリデーションを実装しており、部分失敗時でも既存スコアを保護する工夫がある。

ディレクトリ構成（src/kabusys 以下の抜粋）
-------------------------------------------
- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 管理（Settings）
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor 単体起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（OpenAI + ETF）
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite テーブル定義・アクセスラッパー
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定異常監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 管理
    - alert_manager.py               — LINE 通知
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 発注株数計算・リスク制限
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py             — 各種ファクター計算（DuckDB）
    - feature_exploration.py         — 将来リターン・IC・統計サマリ
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成ツール
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度・affinity

補足（開発者向け）
-----------------
- .env のパースは配慮済み（クォート・エスケープ・コメント対応）。プロジェクトルートは .git または pyproject.toml を基準に探します。
- DuckDB 接続は prices_daily / raw_financials 等のテーブルを前提とするため、研究・バックテスト用のデータ準備が別途必要です。
- unit tests / CI 用フックはこのスナペットに含まれていませんが、各モジュールは純粋関数化（副作用少なめ）されている箇所が多く、単体テストしやすい設計です。

ライセンス / 貢献
-----------------
- ライセンスや貢献ルールはこの README に含まれていません。組織内の既定に従ってください。

問い合わせ
-----------
- 実行時の設定や運用に関する質問があれば、設定ファイル（.env）や run_* スクリプトのログ出力を参照してください。ログレベルは LOG_LEVEL 環境変数で調整できます。

以上がコードベースの README 相当のまとめです。必要ならば、README に含める具体的な .env.example のテンプレートや、起動スクリプトの具体的な systemd ユニット例、Dockerfile / docker-compose のサンプルなども作成できます。どれが必要か教えてください。