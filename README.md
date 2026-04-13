# KabuSys — README

このリポジトリは日本株の自動売買システム「KabuSys」の一部実装です。  
本READMEはコードベース（src/kabusys 以下）を対象に、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤で、以下の主要機能を持ちます。

- 注文生成・発注・状態管理（Execution）
- リコンシリエーション（起動時の注文・ポジション同期）
- 監視（System / Trade / Risk）とアラート（LINE）
- ポートフォリオ構築・配分計算（等配分・スコア加重・リスクベース）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー）
- ニュースのNLPによるセンチメント評価（OpenAI を利用）
- Paper Trading 用の検証・レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計方針として、可能な限り純粋関数・副作用の分離、DB（SQLite / DuckDB）を用いた永続化、API 呼び出しのリトライやフェイルセーフを備えています。

---

## 機能一覧（主要コンポーネント）

- kabusys.config
  - 環境変数/.env の読み込みと Settings クラス
  - KABUSYS_ENV による実行モード（development / paper_trading / live）

- Execution（発注系）
  - run_execution.py：ExecutionEngine の起動スクリプト
  - Broker クライアントファクトリ（本番 / モック切替）
  - OrderManager / OrderRepository / Reconciler / RiskManager

- Monitoring（監視系）
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB（SQLite を使った永続化）
  - AlertManager（LINE プッシュ通知）
  - KillSwitch（flag ファイルによる Execution 停止）
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）

- Portfolio（ポートフォリオ構築）
  - 銘柄選定・重み計算・ポジションサイズ計算・リスク調整

- Research（研究用途）
  - factor_research.py：モメンタム・ボラティリティ・バリュー算出（DuckDB）
  - feature_exploration.py：将来リターン計算、IC、統計サマリ

- AI（OpenAI 利用）
  - news_nlp.py：ニュース記事の銘柄別センチメントスコア付与（ai_scores テーブルへ書き込み）
  - regime_detector.py：ETF 等の指標とマクロニュースを統合した市場レジーム判定

- Tools
  - paper_verification_report.py：Paper Trading データから検証レポート生成

- ユーティリティ
  - utils/process_priority.py：OS 横断のプロセス優先度／CPU affinity 設定

---

## 必要条件（概略）

- Python 3.10+
- 推奨ライブラリ（コードで利用されているもの）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード起動時)
  - openai (AI 機能利用時)
  - sqlite3（標準ライブラリ）
- ネットワークアクセス（LINE / OpenAI / ブローカー API を使う場合）

※ 実際の requirements.txt はこのリポジトリに含まれていないため、上記ライブラリを適宜 pip でインストールしてください。

例:
pip install duckdb psutil requests streamlit openai

---

## セットアップ手順

1. リポジトリをチェックアウト／クローンし、仮想環境を作成してアクティベートします。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（上記参照）。

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

推奨の .env に含める主要項目例:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...   (AI 機能を使う場合)
- KABUSYS_ENV=development | paper_trading | live
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db   (paper_trading モード用)
- SQLITE_PATH=data/monitoring.db                    (監視ログ DB パス、デフォルト)
- DUCKDB_PATH=data/kabusys.duckdb                   (DuckDB パス、デフォルト)
- LINE_CHANNEL_ACCESS_TOKEN=... (通知用)
- LINE_USER_ID=...              (通知用)
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- MONITOR_POLL_INTERVAL=60      (run_monitoring のポーリング間隔（秒）上書き)

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. DB の初期化：監視用 DB テーブルはスクリプト内で起動時に自動作成（init_monitoring_db）されます。DuckDB 側は外部スクリプトや ETL プロセスでテーブル（prices_daily / raw_financials / raw_news 等）を準備してください。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")。特に paper_trading はブローカーをモックに切替えて data/paper_trading.db に記録します。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。
- PAPER_FILL_MODE: Paper Trading の fill モード（"instant" | "partial" | "never" | "reject"）。
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 各種外部 API 認証
- SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは Settings クラス参照）

.env 自動ロード
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動的に読み込みます。
- OS 環境変数はデフォルトで保護され、.env の値は上書きされません（.env.local は override=True で読み込まれます）。
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（コマンド例）

以下は主要な起動・ユーティリティの実行例です。各スクリプトは src/kabusys 以下をパッケージとして扱い、python -m で実行できます。

1) Execution（発注エンジン）を起動する
- 本番/開発/紙（paper_trading）は KABUSYS_ENV に依存します。
- 例（paper_trading モードを想定）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

  実行の流れ:
  - プロセス優先度を high に設定（set_process_priority）
  - Settings を読み込み DB（paper_trading の場合は data/paper_trading.db）へ接続
  - BrokerClientFactory によるブローカークライアント生成（モック or 実ブローカー）
  - ExecutionEngine を起動してセッションを実行

2) Monitoring（監視）を起動する
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60s）。
- 監視は Settings.env にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB に記録する設計）。

3) Paper Trading 検証レポートを生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- 指標: 稼働率、注文成功率、送信率、P95 レイテンシ などを算出して PASS/FAIL 判定を行います。

4) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブで可視化します。

5) AI 系ユーティリティ（ニューススコアリング / レジーム判定）
- news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date、OPENAI_API_KEY を与えて呼び出します（スクリプトとしての起動は用意されていませんが、ライブラリ関数として利用可能です）。
- 例（Python REPL）:
  - from kabusys.ai.news_nlp import score_news
  - import duckdb, datetime
  - conn = duckdb.connect('data/kabusys.duckdb')
  - score_news(conn, datetime.date(2026,4,10), api_key='sk-...')

注意: AI 機能は OpenAI の利用料が発生します。API キーの管理に注意してください。

---

## 実装上の注意点 / 動作仕様（抜粋）

- Settings は .env を自動読み込みし、重要な環境変数が未設定の場合は例外を投げます（_require）。
- run_monitoring では MONITOR_POLL_INTERVAL を環境変数で変更可能。0 以下や不正値はデフォルトにフォールバック。
- MonitoringDB:init_monitoring_db は冪等でスキーマを作成し、既存 DB に対する簡易マイグレーション（カラム追加）も実施します。
- Paper Trading モードでは本番 DB と完全分離して data/paper_trading.db を使用（設定により上書き可能）。
- process_priority 設定は psutil を使い OS に依存した実装を吸収。権限不足等で設定できない場合は警告でスキップします。
- AI 呼び出しはリトライや JSON レスポンスのバリデーションを行い、失敗時は安全にフォールバックする実装です（例: macro_sentiment=0.0）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要ファイルと簡単な説明です（抜粋）:

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — Settings / .env 自動ロード
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py         — 発注状態マネージャ
    - reconciler.py           — 再起動時のリコンシリエーション
    - ... (Broker, Engine, OrderRepository 等)
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite テーブル定義と CRUD ラッパ
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - alert_manager.py         — LINE 通知
    - kill_switch.py           — kill.flag 制御
    - monitoring_engine.py     — 各モニタの統合
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算、上限・丸め処理
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value ファクター
    - feature_exploration.py   — IC / forward returns / summary
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — 市場レジーム判定（マクロ＋MA200）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - data/ (実行時に使用する DB / PID / flag 等の配置を想定)
    - kabusys.duckdb (default DUCKDB_PATH)
    - monitoring.db   (default SQLITE_PATH)
    - paper_trading.db (paper trading 用 DB)
    - execution.pid
    - kill.flag

---

## 開発・テスト時の補足

- DB や外部 API 呼び出しが必要な箇所は抽象化されており、ユニットテストではモック（patch）で差し替え可能です（例: news_nlp._call_openai_api, regime_detector._call_openai_api）。
- .env のパースはシェル形式の export をある程度サポートし、クォート内のエスケープやインラインコメントの取り扱いにも対応しています。
- DuckDB の SQL は大規模集計を想定して設計されています。prices_daily / raw_financials / raw_news 等のテーブル準備が必要です。
- streamlit_dashboard は監視 DB を読み取り専用で開くため、MonitoringEngine が稼働中でも安全に表示できます。

---

もし README に追加してほしい具体的な情報（例: requirements.txt の自動生成、Docker 化、具体的な環境変数テンプレート、CI 設定例など）があればお知らせください。必要に応じて追記・整備します。