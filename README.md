KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python パッケージ群です。本リポジトリには以下の主要機能が含まれます。

- 実行（Execution）: 注文管理、ブローカーとのやり取り、リスク管理、リコンシリエーション
- 監視（Monitoring）: システム状態・注文滞留・ドローダウン監視、LINE 通知、kill flag 発行
- 研究（Research）: ファクター計算・特徴量探索（DuckDB ベース）
- AI モジュール（AI）: ニュース NLP によるセンチメント計算、レジーム判定（OpenAI を使用）
- ポートフォリオ構築: 候補選定、重み計算、リスク制御、ポジションサイズ計算
- ツール: Paper Trading の検証レポート生成、Streamlit ダッシュボードなど

主な設計方針:
- DuckDB / SQLite をローカル DB として利用（データは data/ 配下に保存される）
- 本番環境と Paper Trading を明確に分離可能（KABUSYS_ENV）
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ設計（失敗時はフォールバック）

機能一覧
--------
主なコンポーネント（抜粋）:

- 実行関連
  - run_execution.py: ExecutionEngine（エンジン）起動スクリプト
  - OrderManager / OrderRepository: 注文状態管理・永続化
  - Reconciler: 起動時の自動復旧・突合せ
  - RiskManager: 発注時のリスク制御（設定に基づく）

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリング起動スクリプト
  - MonitoringEngine: System / Trade / Risk をまとめてポーリング
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス状態監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウンやポジション上限監視
  - AlertManager: LINE への通知（クールダウン機構あり）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる

- 研究・AI
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC 等
  - ai.news_nlp: raw_news を LLM（OpenAI）でスコア化して ai_scores に書き込み
  - ai.regime_detector: マクロ記事 + ETF MA200 を組み合わせて市場レジーム判定

- ポートフォリオ
  - portfolio.portfolio_builder: 候補選定、重み算出（等分 / スコア）
  - portfolio.position_sizing: 株数決定、単元株丸め、投資総額スケール調整
  - portfolio.risk_adjustment: セクターキャップ、レジーム乗数

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成
  - monitoring/streamlit_dashboard.py: Streamlit 監視ダッシュボード（read-only）

セットアップ手順
----------------

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化することを推奨します。
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージ（代表例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード使用時)
   - 注意: requirements.txt は含まれていないため、必要に応じて上記を pip install してください。
     例:
       pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env
   - KabuSys は .env / .env.local をプロジェクトルートから自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（research 等で利用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（ブローカークライアント）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト 60）
     - LOG_LEVEL（DEBUG|INFO|...）

   - .env の例（プロジェクトルートに .env を作成）:
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

4. データディレクトリ
   - デフォルトの DB ファイルは data/ 配下に置かれます。必要に応じてディレクトリを作成してください。
     mkdir -p data

使い方
------

- 監視ループ起動（SystemMonitor 単体）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 実行:
    python -m kabusys.run_monitoring
  - 停止:
    - Ctrl+C、またはプロジェクトルートの data/stop_requested.flag を作成すると安全に停止します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 SQLite に書き込みます（本番 DB と分離）。
  - 実行:
    python -m kabusys.run_execution
  - 実行中の停止は data/stop_requested.flag を作成するか、ExecutionEngine が kill.flag を検知すると停止します。

- Streamlit ダッシュボード（監視）
  - 実行 (read-only, DB を読み取る):
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - 実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI モジュール（プログラム的呼び出し例）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

- 設定参照（コード内で）
  - from kabusys.config import settings
  - settings.env / settings.is_paper / settings.sqlite_path / settings.duckdb_path などのプロパティを利用可能

注意事項 / 実行時の振る舞い
-------------------------
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を監視 DB として使用する設計になっています。
- OpenAI を使うモジュール（ai.news_nlp, ai.regime_detector）は API 失敗時にフォールバックやスキップを行い、システム全体を停止させないように設計されています。
- process priority / CPU affinity は psutil を用いて OS に依存せず設定を試みますが、権限不足時は警告を出してスキップします。
- kill switch: RiskMonitor が条件を満たすと KillSwitch が data/kill.flag を作成・書き込み、ExecutionEngine が検知して停止します。KillSwitch は冪等に動作します（既に存在する場合は書き込みをスキップ）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境設定の読み込み / Settings
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- execution/
  - (OrderManager, Reconciler, order_repository 等の実装ファイルが含まれます)
- utils/
  - __init__.py
  - process_priority.py
- data/ (実行時に使用されることが多いトップレベル data ディレクトリ)
  - monitoring.db
  - kabusys.duckdb
  - paper_trading.db
  - stop_requested.flag
  - kill.flag
  - execution.pid

よく使うファイル・概念
- data/stop_requested.flag:
  - このファイルの存在を run_execution/run_monitoring が検知すると安全に停止します。
- data/kill.flag:
  - KillSwitch により作成される停止指示フラグ。ExecutionEngine 側が検知すると即時停止を試みます。
- data/execution.pid:
  - ExecutionEngine 起動時に PID を書く想定のファイル（SystemMonitor が実在プロセスかをチェックするために使用）。
- monitoring DB（SQLite）:
  - system_status / trade_logs / positions / risk_logs / dashboard のテーブルを持ちます。init_monitoring_db() でスキーマを作成します。
- duckdb:
  - 価格データ・財務データ（prices_daily, raw_financials 等）や research/ai の分析に利用します。

開発上のヒント
----------------
- .env ファイルの自動ロードは、プロジェクトルート（pyproject.toml または .git がある場所）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Streamlit ダッシュボードは DB を読み取り専用で開きます。監視プロセスが起動していないと Database not found エラーになります。
- DuckDB を直接使った研究コード群は外部ネットワークに影響しない設計（ローカルデータのみ参照）です。テスト時は DuckDB 接続に対してテスト用データを準備してください。

ライセンス / 貢献
----------------
- 本リポジトリ固有のライセンス情報はプロジェクトルートの LICENSE を参照してください（ここには含まれていません）。
- バグ報告や PR を歓迎します。大きな変更は事前に Issue で相談してください。

以上がこのコードベースの概要と主要な使い方です。必要であれば、セットアップ用の requirements.txt や実際の起動手順 (systemd / docker-compose など) のテンプレートを作成することもできます。どの形式が必要か教えてください。