# KabuSys

KabuSys は日本株自動売買システムの簡易実装です。戦略のポートフォリオ構築、注文管理、監視、Paper Trading 機能、ニュース NLP によるセンチメント評価、研究用ファクター計算などのコンポーネントを含みます。

以下はこのリポジトリの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要なコマンド／モジュール）
- 環境変数（主な設定）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意

---

プロジェクト概要
- 日本株（kabuステーション想定）向けの自動売買基盤のプロトタイプ。
- 戦略側のポートフォリオ構築（候補選定・重み付け・株数算出）、発注フロー（OrderManager、ExecutionEngine の想定）、監視（System / Trade / Risk）、LLM を使ったニュースセンチメント（OpenAI）やレジーム判定、研究用ファクタ計算を備えています。
- DB は DuckDB（市場データ・リサーチ）と SQLite（監視・発注ログ等）を併用します。
- Paper Trading モードは本番 DB と分離して動作可能。

主な機能
- ExecutionEngine 起動用スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録。
  - ブローカー接続、リスク管理、オーダー管理、再突合（Reconciler）を組み合わせて注文処理を行う。
- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして system_status, trade_logs, risk_logs, dashboard などへ記録。
  - KillSwitch による停止フラグ生成と ExecutionEngine の強制停止トリガ。
  - LINE 通知（AlertManager）対応（トークン/ユーザID 設定時）。
- Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
  - 監視 DB（data/monitoring.db）を読み、ダッシュボード表示。
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - paper_trading DB を解析し稼働率・注文成功率・レイテンシ等をレポート出力。
- 研究・解析モジュール（research）
  - ファクター計算（momentum / value / volatility）、将来リターン、IC 計算、統計サマリー等（DuckDB 接続で prices_daily 等を参照）。
- ニュース NLP（ai/news_nlp.py）
  - raw_news をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores テーブルへ保存（API リトライ・検証ロジックあり）。
- レジーム判定（ai/regime_detector.py）
  - ETF(1321) の MA200 差分とマクロニュースセンチメントを合成して daily market_regime を算出・保存。
- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア重み、セクターキャップ、レジーム乗数、株数決定（lot 丸め・aggregate cap）など。

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.10+ を推奨（型注釈に union types 等を使用）。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要なライブラリ（例）
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - requirements.txt がある場合はそれを利用してください。ない場合は手動で：
     - pip install duckdb psutil requests openai streamlit

4. データディレクトリとファイル
   - プロジェクトルートに data/ ディレクトリを作成
     - data/monitoring.db （監視 SQLite、デフォルト）
     - data/kabusys.duckdb （DuckDB、デフォルト）
     - data/paper_trading.db （Paper Trading 用 SQLite、paper_trading モード時）
     - data/execution.pid, data/kill.flag, data/stop_requested.flag などはランタイムで作成されます
   - 監視 DB は起動時に init_monitoring_db() によってスキーマを作成します（冪等動作）。

5. 環境変数（.env）
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     PAPER_FILL_MODE=instant

使い方（主要コマンド・エントリポイント）

- Execution（実運用・Paper Trading）
  - 本番モード（env=live）または development:
    - KABUSYS_ENV を設定（例: export KABUSYS_ENV=development）
    - python -m kabusys.run_execution
  - Paper Trading:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - paper_trading モードでは settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ書き込み、MockBroker を使用します。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 監視は常に本番 sqlite_path（data/monitoring.db 等）を用いてログを残します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで監視 DB を読み、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / リサーチ機能（プログラム呼び出し）
  - ニュース NLP（OpenAI 必須）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # または環境変数 OPENAI_API_KEY
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")
  - 研究用ファクター:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - calc_momentum(duckdb_conn, date(2026, 4, 1))

環境変数（主な設定）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨
  - KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / 各種閾値（CPU/MEM/DISK） など（Settings を参照）

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/設定の読み込みおよび Settings クラス（.env 自動読み込み）
  - run_execution.py — ExecutionEngine 起動スクリプト（main エントリ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングして ai_scores へ書込
    - regime_detector.py — 市場レジーム判定（ma200 + LLM マクロ評点）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite スキーマと MonitoringDB（永続化層）
    - system_monitor.py — CPU/MEM/DISK・プロセスPID・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各モニタをまとめるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, execution_engine.py（※一部は抜粋）
    - broker_factory.py, broker_api.py — ブローカー抽象・実装（Mock を含む）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 発注株数計算、aggregate cap / lot 丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - data/  （プロジェクトルート直下、ランタイムで使用）
    - monitoring.db（SQLite）、kabusys.duckdb（DuckDB）、paper_trading.db（Paper-trading）
    - execution.pid, kill.flag, stop_requested.flag などのフラグ/PIDファイル

運用上の注意
- .env 自動ロード
  - config.py がプロジェクトルートを検出できれば .env / .env.local が自動で読み込まれます。
  - テストや特殊な起動では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- Paper Trading と本番 DB の分離
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用するため、本番ログと干渉しません。
- フラグファイル
  - data/stop_requested.flag: run_*.py では存在を検出してループやエンジンを停止します（手動作成で安全停止）。
  - data/kill.flag: KillSwitch により生成され ExecutionEngine の停止をトリガできます。
- OpenAI の呼び出し
  - OPENAI_API_KEY を設定してください。API の失敗はフェイルセーフとされ多くのケースで 0.0 にフォールバックしますが、ログを必ず確認してください。
- 権限・優先度設定
  - run_* 起動時にプロセス優先度を設定しようとします（psutil 経由）。権限不足の場合は警告を出してスキップします。

簡単な起動例（ローカルテスト）
1. .env を作成（最低限の必須値を埋める）
2. 仮想環境を有効化して依存をインストール
3. DuckDB/SQLite に基本テーブルを用意（monitoring は起動時に自動作成）
4. 監視を起動（別端末で）
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
5. Execution を起動（別端末で）
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
6. ダッシュボード表示
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

さらに詳細なモジュール設計や API の使い方、テーブルスキーマ、戦略仕様書（PortfolioConstruction.md / StrategyModel.md 参照）は別ドキュメントに記載を想定しています。本 README はコードベースの俯瞰と実行手順をまとめたものです。必要があれば追加で「起動フロー図」「環境変数完全リスト」「DB スキーマ詳細」などを作成します。