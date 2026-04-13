README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。本リポジトリは以下の主要機能を提供します。

- 実行コンポーネント（ExecutionEngine）: 注文の生成・送信・状態管理と再同期（リコンシリエーション）
- 監視コンポーネント（MonitoringEngine）: システム状態・注文滞留・リスク（ドローダウン・ポジション上限）を定期検査しログ・アラートを出す
- ポートフォリオ構築ユーティリティ: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ機能: ファクター計算（Momentum / Volatility / Value）、特徴量探索（IC 等）
- AI支援機能: ニュースを LLM（OpenAI）でセンチメント評価してスコア保存、マクロセンチメントと ETF MA を組み合わせた市場レジーム判定
- ツール類: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード等

主な設計方針:
- DuckDB を用いた時系列ファクタ計算（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ（data/monitoring.db）や paper trading 用 DB（data/paper_trading.db）
- 自動環境読み込み (.env / .env.local)、KABUSYS_ENV による動作モード切替（development / paper_trading / live）
- LLM 呼び出しは失敗に寛容（フェイルセーフ）、部分書込みで既存データを保護する設計

機能一覧
--------
- Execution
  - 注文生成 / 送信 / 同期（OrderManager, OrderRepository, Reconciler）
  - RiskManager による約定時のリスクチェック（スロット制限・利用割合等）
  - BrokerFactory による本番 / PaperTrading（MockBroker）の切り替え

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 注文滞留（stale）・約定異常（価格乖離）検出
  - RiskMonitor: ドローダウン・ポジション上限の監視と risk_logs への永続化
  - KillSwitch: 条件に応じて data/kill.flag を書き込んで ExecutionEngine を停止させる
  - AlertManager: LINE PUSH API を使ったアラート送信（cooldown 管理）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）

- Research / Portfolio
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算 / IC（calc_forward_returns, calc_ic）
  - ポートフォリオ構築ユーティリティ（select_candidates, weight 計算, calc_position_sizes）
  - セクターキャップ／レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- AI
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュース LLM スコアを合成し market_regime に書き込む

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（typing | None 型表記等を利用）
- system 要件: duckdb, psutil, requests, openai, streamlit（必要に応じてインストール）

仮想環境（推奨）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

依存パッケージのインストール（例）
- pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API 用（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必須）
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - PAPER_TRADING_SQLITE_PATH — paper_trading モードの SQLite パス（デフォルト data/paper_trading.db）
  - SQLITE_PATH — 監視 DB path（デフォルト data/monitoring.db）
  - DUCKDB_PATH — DuckDB path（デフォルト data/kabusys.duckdb）
  - PAPER_FILL_MODE — paper_trading の Fill モード（instant|partial|never|reject）
  - PID_FILE_PATH / KILL_FLAG_PATH — pid / kill.flag のパス
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

初回 DB 作成
- 監視テーブルは起動スクリプト内で init_monitoring_db が呼ばれて自動作成されます。
- DuckDB と prices_daily / raw_financials 等のテーブルはデータ準備が必要です（外部 ETL）。

使い方
------

起動スクリプト（モジュール実行）
- ExecutionEngine を起動（デフォルトは Settings に従う）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading を設定すると MockBroker が使われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時、プロセス優先度を high に設定し、監視用テーブルの存在を保証します。

- SystemMonitor のポーリング単体スクリプト
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は常に本番の sqlite_path を使用します（KABUSYS_ENV に依らず）。

Streamlit ダッシュボード
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
- 監視 DB（paper_trading.db）から稼働率 / 注文成功率 / レイテンシ等を集計し PASS/FAIL を表示します。

AI 機能（プログラム呼び出し）
- ニューススコアリング（例）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

- レジームスコアリング
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")

注意:
- OPENAI_API_KEY が未設定だとこれらは例外を投げます（関数内でチェック）。
- API 呼び出しはリトライ / フェイルセーフのロジックを内包していますが、レート制限や接続失敗がある点に注意してください。

監視関連の挙動
- KillSwitch は RiskMonitor の結果に基づいて data/kill.flag を書き込みます。ExecutionEngine はこのファイルの存在を検知してシャットダウンする設計が想定されています（Execution 側の実装参照）。
- AlertManager は LINE PUSH API を使って通知します。LINE の channel_access_token と user_id を設定しない場合は送信をスキップします。
- MonitoringDB の init 関数はマイグレーション（カラム追加）を行います。既存 DB に対して冪等に実行されます。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 読み込みと Settings クラス
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 単体起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 監視テーブル層（init_monitoring_db, MonitoringDB）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — LINE 通知
    - monitoring_engine.py   — 各 Monitor を束ねる（ポーリング・一括実行）
    - streamlit_dashboard.py — Streamlit ダッシュボード（read-only）
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py    — （実装ファイルはここにあることを想定）
    - broker_factory.py
    - execution_engine.py
    - ...                    — 注文関連の実装
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定 / 重み算出
    - risk_adjustment.py     — セクター制限 / レジーム乗数
    - position_sizing.py     — 発注株数計算 / スケーリング
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント取得（OpenAI）
    - regime_detector.py     — マクロ+MA によるレジーム判定
  - data/
    - pipeline.py            — get_last_price_date 等（DuckDB 関連ユーティリティ）
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - その他: duckdb / sqlite を操作するコードが各モジュールに分かれています

運用上の注意
------------
- 実際の売買を伴う環境（KABUSYS_ENV=live）で使用する前に、paper_trading モードで十分に検証してください。
- .env ファイルは secrets（API キー等）を含みます。取り扱いには十分ご注意ください（.gitignore で除外推奨）。
- OpenAI 呼び出しはコストが発生します。batch size / トークン量に注意してください。
- psutil による優先度 / affinity 設定は権限に依存します。設定に失敗した場合は警告ログでスキップされます。

貢献・拡張案（一例）
--------------------
- stocks マスタを導入して銘柄ごとの lot_size をサポート
- リアルタイム監視のため WebSocket / Push 方式のアラート（LINE 以外）
- DuckDB テーブルの ETL / 定期更新パイプライン統合
- ExecutionEngine の graceful shutdown / kill.flag ハンドリングの堅牢化

以上。必要であれば README にサンプル .env のテンプレートやより詳細な起動手順（systemd / Docker / コンテナ運用）を追加できます。どのドキュメントを優先して追加しますか？