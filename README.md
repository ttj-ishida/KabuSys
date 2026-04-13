KabuSys — 日本株自動売買システム (README)
====================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装したプロジェクトです。  
主な目的は以下です。

- ファクター計算・研究（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 発注実行エンジン（本番 / paper_trading 切替）
- 監視（System / Trade / Risk モニタ）とアラート（LINE）
- OpenAI を使ったニュース NLP（センチメント）・レジーム判定
- Paper Trading の検証レポート生成・ダッシュボード表示

特徴（抜粋）
------------
- DuckDB / SQLite を利用した分析・監視データ永続化
- 本番 / paper_trading 環境切替（DB とブローカーは分離）
- CLI / スクリプトでの起動（モジュール化：python -m kabusys.*）
- LINE Push による通知（cooldown 管理）
- OpenAI（gpt-4o-mini 等）でニュースセンチメントを取得する機能
- Streamlit で監視ダッシュボード表示
- 冗長性を考慮したリコンシリエーション・リスク監視（dd・ポジション数等）
- フェイルセーフ設計（API失敗時はフォールバック、DB書き込みはトランザクション）

前提 / 必要環境
--------------
- Python 3.10 以上（逐次型ヒント（|）を使用）
- 以下の主要な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)

インストール例
--------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

設定（環境変数）
----------------
プロジェクトは .env / .env.local（プロジェクトルートに置く）および OS 環境変数を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。.env の読み込み優先は OS 環境変数 > .env.local > .env です。

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合は MockBrokerClient を使い、専用の PAPER_TRADING_SQLITE_PATH に記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定振る舞い（instant|partial|never|reject, デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

セットアップのヒント
------------------
- data/ ディレクトリを作成して DB ファイルを配置（例: mkdir -p data）
- .env.example があれば参考に .env を作成
- OpenAI を使う場合は OPENAI_API_KEY を設定
- paper_trading を試す場合は KABUSYS_ENV=paper_trading を設定すると本番 DB と分離されます

使い方（起動例）
----------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - paper_trading モードで起動する場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - Execution 起動時には PID ファイルが作成され、プロセス優先度を高に設定しようとします。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 注意: 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。

- Streamlit ダッシュボード（監視）を起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボード表示を行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（優先度は --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

主要挙動の説明
----------------
- paper_trading:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に書き込みます。本番 DB と完全に分離される設計です。
- プロセス優先度:
  - run_* スクリプト起動時に set_process_priority("high") を呼び出します（Windows/Linux の差分を吸収）。
- 監視（Monitoring）:
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブルを持つ SQLite DB を使用します。init_monitoring_db() は冪等にこれらテーブルを作成・マイグレーションします。
  - KillSwitch はリスクアラート（DRAWDOWN / POSITION_LIMIT 等）を検出すると kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - AlertManager は LINE push を行い、同一 (level, category) の短時間連続送信をクールダウンで抑制します（デフォルト 30 分）。
- OpenAI（ニュース NLP / レジーム判定）:
  - news_nlp.score_news と regime_detector.score_regime が OpenAI（gpt-4o-mini 等）を使ってニュースを解析します。API失敗時は安全なフォールバック（ゼロスコア等）で継続します。
  - OpenAI キーは api_key 引数または環境変数 OPENAI_API_KEY から解決します。

ディレクトリ構成（抜粋）
------------------------
src/
  kabusys/
    __init__.py                 — パッケージ定義（バージョン等）
    config.py                   — 環境変数 / 設定読み込みロジック（.env 自動読込）
    utils/
      process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
    execution/                  — 発注関連（Engine, OrderManager, Reconciler 等）
      order_manager.py
      reconciler.py
      ... (broker_factory, order_repository 等)
    monitoring/                 — 監視コンポーネント
      monitoring_db.py          — SQLite テーブル定義 + MonitoringDB 操作
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
      run_monitoring.py         — 監視ポーリングループ起動スクリプト
    portfolio/                  — ポートフォリオ構築ロジック（純粋関数）
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/                   — ファクター計算・研究用モジュール（DuckDB）
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py               — ニュースを OpenAI でスコアリングして ai_scores へ書込
      regime_detector.py        — マクロ + ma200 を合成した市場レジーム判定
    tools/
      paper_verification_report.py — paper_trading の検証レポート生成スクリプト
    run_execution.py            — ExecutionEngine 起動スクリプト
    ... その他モジュール

監視 DB（monitoring_db.py）の主なテーブル
----------------------------------------
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の 1 行で集計情報を保持。portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value など)

開発・テストの注意点
--------------------
- Settings は起動時に .env / .env.local を自動ロードします（プロジェクトルートは .git または pyproject.toml を基準に自動検出）。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードをオフにできます。
- DuckDB / SQLite のスキーマは init_monitoring_db() によって冪等に作成されます。既存 DB に対する軽微なマイグレーション（カラム追加）も実装済みです。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンスバリデーションを行い、失敗時は安全にフォールバックする設計です（テスト時は _call_openai_api をモック可能）。

よく使うコマンドまとめ
---------------------
- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- ライセンスや詳細な運用手順（デプロイ、監視ポリシー、バックアップ等）はこの README に含まれていません。運用に際しては追補ドキュメント（運用マニュアル）を整備してください。
- セキュリティ上の注意: 環境変数や .env に API キー / パスワードを平文で置く場合はアクセス権を厳格に制御してください。

--- 
この README はリポジトリ内のコード（src/kabusys 以下）を参照して作成しています。実際の運用・拡張時は各モジュールの docstring と実装を合わせて参照してください。