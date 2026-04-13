README — KabuSys (日本株自動売買システム)
=================================================

概要
----
KabuSys は日本株向けの自動売買および研究用ライブラリ／ランタイム群です。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- 注文実行エンジン（ExecutionEngine 起動スクリプト）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- 監視用 SQLite 永続化層（monitoring DB）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・株数決定）
- 研究モジュール（ファクター計算・将来リターン・IC 解析など）
- AI 補助（ニュースのセンチメント評価 / 市場レジーム判定、OpenAI を利用）
- 運用支援ツール（Paper Trading 検証レポート生成・Streamlit ダッシュボード）

主な特徴
--------
- 環境変数ベースの設定管理（.env / .env.local 自動読み込み、無効化可能）
- paper_trading モードで本番 DB と明確に分離（専用 SQLite に記録）
- DuckDB を使った時系列・ファクター計算（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）経由の NLP によるニューススコアリング（フェイルセーフ、バッチ処理、リトライ）
- 監視ループはプロセス優先度設定・PID フラグ管理・LINE 通知（AlertManager）を備える
- 純粋関数で記述されたポートフォリオ構築ロジック（ユニットテストしやすい設計）

セットアップ
-----------
前提
- Python 3.10 以上（typing の | や from __future__ import annotations を利用）
- SQLite（組み込み）、DuckDB（pip パッケージ）
- ネットワーク環境（OpenAI API, LINE API を使用する場合）

手順（例）
1. リポジトリをクローン:
   git clone <リポジトリ_URL>
2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール:
   pip install -U pip
   pip install duckdb psutil openai requests streamlit
   （実運用では requirements.txt を用意して pip install -r requirements.txt を推奨）
4. データ用ディレクトリを用意:
   mkdir -p data
   （デフォルトの DB ファイル: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）
5. 環境変数（.env）を用意:
   プロジェクトルートに .env / .env.local を置くと自動読み込みされます。
   自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋、.env 例）
- KABUSYS_ENV=development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant | partial | never | reject
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- MONITOR_POLL_INTERVAL=60  （run_monitoring 用、秒）

使い方（実行例）
----------------

1) 実行エンジン（本番 / paper_trading）
- 実行:
  python -m kabusys.run_execution
- 説明:
  KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）が使われ、
  data/paper_trading.db に取引ログを記録します。本番とは DB を分離します。

2) 監視ループ（SystemMonitor のポーリング）
- 実行:
  python -m kabusys.run_monitoring
- 説明:
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。監視は常に本番用 sqlite_path を参照します（KABUSYS_ENV に無関係）。

3) Streamlit ダッシュボード（監視の可視化）
- 実行:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  監視 DB を read-only モードで開き、Overview / Positions / Orders / System タブを表示します。

4) Paper Trading 検証レポート
- 実行例:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite ファイルを指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- 出力:
  稼働率、注文成功率、送信率、レイテンシなどのサマリと PASS/FAIL 判定を標準出力へ印字します。

5) AI モジュール（プログラムから呼ぶ）
- ニューススコアリングを呼ぶ（例）:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="...")

- レジーム判定を呼ぶ（例）:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")

注意: OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で渡します。API 呼び出し失敗はフェイルセーフ（スコア 0.0 等）で処理する設計ですが、鍵が未設定の場合は ValueError が発生します。

ライブラリ利用例（研究 / ポートフォリオ）
- ファクター計算:
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  results = calc_momentum(duckdb_conn, target_date)
- ポートフォリオ構築:
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

設計メモ / 動作上の注意
---------------------
- 設定の自動ロード: プロジェクトルート（.git または pyproject.toml を起点）から .env/.env.local を自動で読み込みます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は「監視用 DB（monitoring DB）」に対してのみ書き込みます。Monitoring は KABUSYS_ENV に関係なく settings.sqlite_path（本番パス）を使用します。
- paper_trading モードでは発注・約定の挙動が本番と異なります（MockBrokerClient、PAPER_FILL_MODE 等を参照）。
- OpenAI 呼び出しはリトライ・バックオフ・JSON バリデーション等の処理を行い、部分失敗時でも既存データを不必要に消さないよう DB 操作は慎重に行います。
- process priority / CPU affinity 関連に psutil を使用しています。権限不足時は警告を出しスキップします。
- DuckDB を用いた研究処理は prices_daily / raw_financials / raw_news 等のテーブルを参照します。これらのテーブルが事前に用意されていること（データ投入）が前提です。
- ログレベルやその他閾値は Settings クラスが環境変数から取得します。KABUSYS_ENV は development / paper_trading / live のいずれかです。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                            — 環境変数 / Settings 管理（.env 自動ロード含む）
- run_execution.py                      — ExecutionEngine 起動スクリプト
- run_monitoring.py                     — SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py        — Paper Trading 検証レポート CLI
- monitoring/
  - __init__.py
  - monitoring_db.py                    — SQLite テーブル作成 / MonitoringDB 書込 API
  - system_monitor.py                   — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py                    — 注文滞留・約定異常の監視
  - risk_monitor.py                     — ドローダウン・ポジション上限監視
  - kill_switch.py                       — kill.flag 管理
  - alert_manager.py                    — LINE push 通知
  - monitoring_engine.py                — 各 monitor を束ねてループ
  - streamlit_dashboard.py              — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker API / engine / order_repository 等)
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
  - news_nlp.py                          — ニュースを OpenAI でスコアリング
  - regime_detector.py                   — マクロ + ETF MA200 で市場レジーム判定
  - __init__.py
- utils/
  - process_priority.py                  — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

主要テーブル（monitoring DB）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の集計行: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

運用上のヒント
--------------
- 起動直後に ExecutionEngine が古い kill.flag を残している可能性があるため、Settings.kill_flag_clear_on_start を利用してクリアする機能があります（環境変数で制御）。
- Paper Trading 検証は tools/paper_verification_report.py を使うと簡単に稼働率や成功率を確認できます。
- AI を使う処理は API コストがかかります。ローカル検証時は API 呼び出し部分をモックしてテストしてください（score_news や regime_detector 内で _call_openai_api をモックしやすい設計になっています）。

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献ガイドラインを記載）

お問い合わせ
----------
不明点や改善提案があれば Issue を作成してください。