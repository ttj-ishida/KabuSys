KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群をまとめた Python コードベースです。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- ExecutionEngine（発注実行・リスク管理・リコンシリエーション）
- Monitoring（システム稼働監視・注文監視・リスク監視・アラート）
- Portfolio construction（候補選定・重み計算・ポジションサイズ決定）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュースの LLM センチメント評価・市場レジーム判定）
- ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード等）

主な特徴
---------
- 実行と監視が分離された設計（Production と Paper Trading の DB 分離）
- DuckDB を用いた時系列/ファクタ計算（prices_daily / raw_financials を参照）
- OpenAI（gpt-4o-mini）を使ったニュース NLP とレジーム判定（フェイルセーフ・リトライ実装）
- SQLite による監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- LINE によるアラートプッシュ（AlertManager）
- Streamlit ダッシュボードで監視情報の可視化
- Paper Trading の検証レポート生成ツール

前提・依存
-----------
必須（主なライブラリ・ツール）：
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）

（SQLite は標準ライブラリで利用可能）

簡易インストール例：
- 仮想環境作成・有効化
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
- 必要パッケージのインストール（requirements.txt がない場合は個別インストール）
  pip install duckdb psutil requests openai streamlit

環境変数（主なもの）
-------------------
設定は .env / .env.local / OS 環境変数で与えられます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須（実行内容に応じて）：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・設定系（デフォルト値は括弧内）：
- KABUSYS_ENV (development | paper_trading | live)（development）
  - paper_trading の場合は MockBroker を使用しデータは data/paper_trading.db に保存され、本番 DB と分離されます
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")（instant）
- PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）
- DUCKDB_PATH（data/kabusys.duckdb）
- SQLITE_PATH（data/monitoring.db）
- PID_FILE_PATH（data/execution.pid）
- KILL_FLAG_PATH（data/kill.flag）
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- LOG_LEVEL (DEBUG|INFO|...)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート用
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

セットアップ手順（概要）
---------------------
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存ライブラリをインストール
   pip install duckdb psutil requests openai streamlit

4. data ディレクトリを作成（必要に応じて）
   mkdir -p data

5. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を作成して必要な変数を記載します。
   - 例（最低限）:
     KABUSYS_ENV=development
     KABU_API_PASSWORD=your_password
     JQUANTS_REFRESH_TOKEN=your_token
     OPENAI_API_KEY=sk-...

6. 初期 DB 作成（必須ではないが監視を即利用するなら）
   - monitoring DB のテーブルはスクリプト起動時に自動生成・マイグレーションされます（init_monitoring_db を使用）。

使い方（主要エントリポイント）
----------------------------

- 実行エンジン（ExecutionEngine）
  - 本番/検証用の発注・リスク管理を行います。
  - 起動:
    KABUSYS_ENV=development python -m kabusys.run_execution
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 動作:
    - paper_trading では MockBrokerClient を使用し data/paper_trading.db に書き込みます。
    - 実行中は data/execution.pid に PID を書き込みます。
    - 停止は data/stop_requested.flag を作成するか kill.flag（KillSwitch）を利用します。

- 監視プロセス（Monitoring）
  - system / trade / risk の各監視を定期実行し SQLite にログを残します。
  - 起動:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

- Streamlit ダッシュボード
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボード表示します。

- Paper Trading 検証レポート
  - 起動:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  - 指標: 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などを出力します。

- AI モジュール（ニュース NLP / レジーム判定）
  - プログラム内から関数を呼び出して使用します（OpenAI API キーが必要）。
  - 例（概念）:
    from kabusys.ai import score_news
    written = score_news(duckdb_conn, target_date, api_key="sk-...")
  - レジーム判定（score_regime）は kabusys.ai.regime_detector.score_regime を参照。

停止シグナル／フラグファイル
---------------------------
- data/stop_requested.flag — run_monitoring/run_execution のポーリングループを優雅に停止するために監視されます。
- data/kill.flag — KillSwitch によって書き込まれると ExecutionEngine に停止信号を送るために使用されます（冪等・理由付与）。
- PID ファイル: data/execution.pid（ExecutionEngine が稼働中に作成）

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py — 環境変数と Settings クラス（自動 .env ロードロジック含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

subpackages:
- execution/
  - execution_engine.py (Engine の起動・セッション管理) — 参照あり
  - order_manager.py — 発注ロジックと状態管理
  - order_repository.py, order_record.py, reconciler.py — リポジトリ・リコンシリエーション
  - broker_factory.py / broker_api.py — ブローカー抽象
- monitoring/
  - monitoring_db.py — SQLite テーブル定義・CRUD ラッパー
  - system_monitor.py — CPU/メモリ/Disk/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE プッシュ通知
  - monitoring_engine.py — 各 Monitor 集約・ループ化
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・スケールダウンロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC/統計サマリー
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores 書き込み）
  - regime_detector.py — マクロ記事 + ETF MA200 によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading レポート生成スクリプト
- utils/
  - process_priority.py — psutil を使った優先度・CPU affinity ユーティリティ
- monitoring/monitoring_db.py etc. — 上述

運用上の注意
-------------
- Paper Trading は production DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しは失敗時にフェイルセーフ（0.0 フォールバック）やリトライを実装していますが、API キー管理・コストに注意してください。
- process priority や CPU affinity の設定には権限が必要になる場合があります。失敗時は警告に留めてスキップします。
- DuckDB / SQLite のファイルパスは Settings で指定可能。バックアップ・ローテーションを検討してください。
- monitoring のログ・DB マイグレーションは起動時に自動で行われます（冪等）。

拡張・開発メモ
--------------
- DuckDB を利用したファクター計算は prices_daily / raw_financials のテーブル設計に依存しています。データパイプライン（kabusys.data.pipeline）との連携を前提にしています。
- AI 部分（news_nlp / regime_detector）はテスト時に _call_openai_api を差し替え可能（unittest.mock など）。ロギングとバリデーションを厳密に行っています。
- monitoring_engine.run_once はユニットテストから個別監視ロジックを呼び出すのに便利です。

問い合わせ・貢献
----------------
- バグ報告や改善提案は Issue を立ててください。
- 開発者向け: コードの責務分離・テスト可能性を維持することを念頭に PR をお願いします。

以上。本 README はリポジトリ内のソースコード（主に src/kabusys 以下）に基づいて作成しています。実運用前に .env の内容や DB パス、API キーの設定を必ず確認してください。