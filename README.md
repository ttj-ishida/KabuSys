# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、リサーチ用ファクター計算、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。本リポジトリは純粋関数的なポートフォリオ構築ロジックから、SQLite / DuckDB を用いたデータ永続化、OpenAI を用いたニュース解析まで幅広く実装しています。

以下はこのコードベースを使い始めるための README です。

## 主な機能（Feature）

- Execution
  - 発注エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - Broker 抽象化（本番/モック切替: KABUSYS_ENV）
  - リコンシリエーション（再起動後の注文同期）
  - OrderManager / OrderRepository による状態管理
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期ポーリング監視
  - 監視ログの永続化（SQLite）
  - Kill Switch（条件で停止フラグを作成）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio（戦略側）
  - 候補選定、等配分・スコア配分、リスク調整、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- AI
  - ニュース NLP による銘柄別センチメントスコア（OpenAI）
  - マクロニュース + ETF MA に基づく市場レジーム判定（OpenAI）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## セットアップ手順

前提: Python 3.9+（typing の一部機能を使っています）。仮想環境の使用を推奨します。

1. リポジトリをクローンして仮想環境を作成・有効化:
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows では .venv\Scripts\activate)

2. 依存関係をインストール（例）:
   - pip install duckdb psutil requests openai streamlit

   ※ 必要に応じて dev/test 用ライブラリを追加してください。

3. data ディレクトリの準備（必要な場合）:
   - mkdir -p data

4. 環境変数の設定:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...         （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

   参考: `kabusys.config.Settings` に各設定とデフォルト値・バリデーションがまとめられています。

5. DB 初期化:
   - 多くの起動スクリプトは起動時に必要なテーブルを冪等に作成します（monitoring 用テーブル等）。
   - DuckDB 用の prices_daily / raw_financials 等は別途データ投入が必要です（リサーチ機能を使う場合）。

## 使い方（主要スクリプト）

- ExecutionEngine を起動する（発注エンジン）:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存。`paper_trading` の場合は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - 起動時に `data/execution.pid` に PID を書き込みます。停止は kill.flag（Settings.kill_flag_path）で通知できます。

- Monitoring を起動する（ポーリング監視）:
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を参照（KABUSYS_ENV にかかわらず本番 DB を使用する設計）。

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザに簡易ダッシュボードを表示します（読み取り専用で SQLite を URI + mode=ro で開きます）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムから呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続、ターゲット日（date）、OpenAI API キーを渡します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - マクロセンチメント + ETF MA を組み合わせて market_regime テーブルに書き込みます。

- Kill Switch の手動操作:
  - `data/kill.flag` を作成すると ExecutionEngine が検出して停止します。KillSwitch クラスは flag の作成・確認・クリアを提供します。
  - clear するには `rm data/kill.flag`（または KillSwitch.clear() を呼ぶ実装を用意する）。

## 主要な設定・注意点

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動ロードされます。ただし OS 環境変数が優先され、`.env.local` は上書き（override=True）で読み込まれます。
  - テストなどで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- KABUSYS_ENV（環境）
  - 有効値: development, paper_trading, live
  - `paper_trading` では発注がモックされ、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。これにより本番 DB と分離されます。

- PAPER_FILL_MODE（paper_trading の約定モード）
  - instant / partial / never / reject のいずれか（不正な値は例外）。

- DB パス（デフォルト）
  - monitoring SQLite: data/monitoring.db
  - paper trading SQLite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb

- 依存ライブラリ
  - duckdb, psutil, requests, openai, streamlit などが使われます。用途に応じてインストールしてください。

- 権限やプラットフォーム差異
  - process priority 設定はプラットフォーム依存（psutil を通じて Windows / POSIX に対応）。権限不足や未対応 OS の場合は警告を出してスキップします。

## ディレクトリ構成

（概要。実ファイルは src/kabusys 以下にあります）

- src/kabusys/
  - __init__.py               — パッケージ定義
  - config.py                 — 環境変数 / Settings
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - execution/
    - broker_api.py (抽象) (注: 実装ファイルは省略されている可能性あり)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - order_repository.py
    - order_record.py
  - monitoring/
    - monitoring_db.py        — monitoring 用 SQLite 永続化層
    - monitoring_engine.py    — 複数モニターの束ね
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
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
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — レジーム判定（OpenAI）
    - __init__.py
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag

（上のファイル一覧は主要なものを抜粋しています。詳細はソースツリーを参照してください。）

## 開発者向けメモ / ベストプラクティス

- DuckDB のテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）はリサーチ・AI 機能の前提データです。必要データをロードしてから関数を実行してください。
- AI（OpenAI）呼び出しは API 制限やエラーに備えたリトライ・フォールバック設計になっています。API キーは `OPENAI_API_KEY` 環境変数で設定してください。
- 監視と発注は DB を介して疎結合になるように設計されています。monitoring は本番 DB を参照する点に注意してください（環境にかかわらず monitor は sqlite_path を使います）。
- ロギングは各モジュールで logger を使っています。テスト・デバッグ時は logging.basicConfig(level=logging.DEBUG) 等で詳細ログを有効にしてください。
- unit test を追加する際は Settings の自動 .env 読み込みを無効にするか、必要な環境変数をテストランタイムで注入してください。

---

以上が KabuSys の概要と主要な操作手順です。追加の情報（API の詳細仕様、DB スキーマ、戦略仕様書等）はプロジェクト内のドキュメント（PortfolioConstruction.md, StrategyModel.md など、該当ファイルがあれば）を参照してください。質問や特定の使い方（例: DuckDB にデータを投入する方法、テスト用モックブローカーの使用方法など）があればお知らせください。