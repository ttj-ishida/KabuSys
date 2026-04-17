KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群と起動スクリプト群を収めています。戦略設計・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ユーティリティ、AI を用いたニュースセンチメント評価などの機能を備えています。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - ブローカー抽象化（実運用 / ペーパートレード切替）
  - リスク管理（最大ポジション比率・利用率、ドローダウン等）
  - 再起動時のリコンシリエーション（未確定注文の同期、ポジション差分検出）
- Monitoring（監視）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（価格データの最新日確認）
  - 注文滞留・約定異常検出
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（停止フラグ生成）と LINE 通知（AlertManager）
  - Streamlit ダッシュボード（監視 UI）
- Portfolio（ポートフォリオ構築）
  - シグナル選定（候補選び）
  - 等重・スコア重み付与
  - 単元・リスク基づく株数決定、集約上限でのスケーリング
  - セクター上限適用、レジーム乗数
- Research（研究用）
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI サブシステム
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に記録
  - マクロ + ETF MA200 を使った市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成スクリプト（期間指定可能）

前提条件 / 依存パッケージ
------------------------
主に以下のパッケージを使用します（環境や用途に応じて追加してください）。

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

（sqlite3 は標準ライブラリに含まれます）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate（Windows）

2. 依存関係をインストールします（例）。
   - pip install duckdb psutil requests openai streamlit

   （要件ファイル requirements.txt があればそちらを使ってください）

3. データディレクトリ（data）を作成します（DBファイルの初期配置など）。
   - mkdir -p data

4. 必須の環境変数を設定します（下記「環境変数」参照）。開発時はルートに .env / .env.local を置くと自動読み込みされます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

環境変数（主なもの）
-------------------
Settings クラス（src/kabusys/config.py）で読み込む主要な環境変数を列挙します。

必須（利用する機能によって変わります）
- JQUANTS_REFRESH_TOKEN — J-Quants API（Research で使用する場合）
- KABU_API_PASSWORD — kabuステーション API（実運用ブローカー接続）
- OPENAI_API_KEY — OpenAI API（ニュース NLP / レジーム判定）

任意 / デフォルト有り
- KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、ペーパートレード専用 DB を使用
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする場合は "1"
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（%）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE通知）用

起動 / 使い方（主なコマンド）
---------------------------

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて paper_sqlite_path に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid を作成し、停止は stop flag を書いて行います

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番の monitoring.db）を使用します
    - stop flag の検出でループを終了します（data/stop_requested.flag）

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザでダッシュボードを表示し、ダッシュボード・ポジション・注文・システムステータスを確認できます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
  - 指定期間の稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL を判定します

- AI（ニューススコアリング / レジーム判定）
  - プログラムから呼び出す関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None) — ai_scores テーブルに書き込む
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルに書き込む
  - 例（スクリプト内から）:
    - from kabusys.ai import score_news
      score_news(duckdb_conn, date(2026, 4, 1), api_key="sk-...")

プロセス制御 / フラグファイル
---------------------------
- data/stop_requested.flag — run_* スクリプトはこのファイルの存在をチェックして安全に終了します
- data/kill.flag — KillSwitch が書き込む停止フラグ。ExecutionEngine は起動時にこれがあれば起動しません
- data/execution.pid — ExecutionEngine が起動時に作成する PID ファイル。SystemMonitor はこの PID を見てプロセスが生きているか判定します

設定ロジック（.env 読み込み）
----------------------------
- ルートの .env / .env.local を自動的に読み込みます（OS 環境変数が優先）
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- .env のパースはシェルライクなフォーマット（コメント、export 形式、クォート、エスケープ）に対応

開発向けメモ
------------
- Monitoring のDB初期化:
  - monitoring 起動時（init_monitoring_db）に必要なテーブルが作成されます（冪等）。既存 DB にカラムがない場合はマイグレーション（ALTER）も行われます。
- Process priority:
  - 起動スクリプトは set_process_priority("high") を呼び、psutil を使ってプロセス優先度を設定します（OS に依存）。
- DuckDB:
  - 研究モジュールや AI モジュールは DuckDB 接続を受け取り SQL クエリで処理します。prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。
- テスト時:
  - OpenAI API 呼び出し部分は内部で分離されており、ユニットテストではモック化しやすい設計です（_call_openai_api を patch するなど）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py            — マクロ + ETF MA200 によるレジーム判定

- monitoring/
  - __init__.py
  - monitoring_db.py              — monitoring 用 SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py              — LINE 通知
  - kill_switch.py
  - streamlit_dashboard.py

- execution/
  - order_manager.py
  - reconciler.py
  - ...（ブローカー / order_repository / execution_engine 等、発注ロジック）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - __init__.py
  - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト

- utils/
  - process_priority.py
  - __init__.py

data/
- monitoring.db                    — 監視ログ（SQLite、起動時自動作成される）
- paper_trading.db                 — ペーパートレード用 DB
- kabusys.duckdb                   — DuckDB（市場データ等）

（実際のリポジトリでは src/ をパッケージ配下にしており、data/ は実行環境で作成されます）

よくある運用フロー（例）
-----------------------
1. DuckDB に価格データや raw_news を投入（研究用データ準備）
2. 本番/ペーパーの設定を .env に用意（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY 等）
3. 監視を先に起動:
   - python -m kabusys.run_monitoring
4. ExecutionEngine を起動:
   - python -m kabusys.run_execution
5. ダッシュボードで状況確認:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
6. Paper トレードの評価:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- KABUSYS_ENV による分離:
  - paper_trading 環境では paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番監視 DB とは完全に分離されます。
- Monitoring は意図的に monitoring.db（sqlite_path）を常に使用します（環境による切替なし）。
- OpenAI 呼び出しや外部 API 呼び出しはレート制御やリトライを実装しており、失敗時は安全にフォールバックする設計です（フェイルセーフ）。

必要に応じて README を補足します。例えば:
- requirements.txt の想定内容
- .env.example の具体例
- 実装されている BrokerClient の使い方（Mock / 実運用）
など、欲しい情報があれば教えてください。