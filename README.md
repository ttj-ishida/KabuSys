README.md

概要
---
KabuSys は日本株向けの自動売買／研究／監視を目的とした小規模な Python コードベースです。
本リポジトリは以下の主要機能を持ちます：
- 戦略用ファクター計算（DuckDB 上の時系列データ参照）
- ポートフォリオ構成・銘柄選定・株数決定ロジック（純粋関数群）
- 注文発行と実行エンジン（ブローカ抽象化・再同期機能）
- 運用監視（システム状態・注文滞留・リスク監視）およびダッシュボード
- Paper Trading 用検証レポート生成ツール
- ニュース NLP（OpenAI を用いたセンチメントスコア算出）と市場レジーム判定

主要な設計方針
- データ操作や計算は DuckDB / SQLite を用いてローカルで完結する設計
- 実行時の環境（本番 / paper_trading / development）に応じた挙動分離
- LLM 呼び出しは冪等性・リトライ・バリデーションを意識して実装
- 多くの処理はテストしやすい純粋関数／副作用を限定したクラス設計

機能一覧
---
- research:
  - ファクター計算: Momentum / Volatility / Value（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索: 将来リターン計算、IC（Information Coefficient）など
- portfolio:
  - 銘柄選定・重み計算（等金額、スコア加重）
  - セクター集中制限、レジーム乗数
  - ポジションサイズ算出（単元株丸め、投下資金スケーリング）
- execution:
  - 注文管理（OrderManager）・再同期（Reconciler）・ExecutionEngine（起動スクリプトあり）
  - ブローカファクトリ（paper_trading では MockBrokerClient を使用）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - SQLite ベースの監視 DB（init_monitoring_db）
  - LINE による一方向アラート通知（AlertManager）
  - streamlit ダッシュボード（read-only）
  - kill.flag を用いた ExecutionEngine 停止シグナル
- ai:
  - ニュースセンチメントスコアの取得（OpenAI を用いたバッチ評価）
  - 市場レジーム判定（ETF MA と LLM の混合スコア）
- tools:
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

必要条件（依存関係）
---
主なランタイム依存（例）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3（標準ライブラリ）

pip でインストールする例（仮想環境推奨）:
    pip install duckdb psutil requests openai streamlit

セットアップ手順
---
1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成して依存パッケージをインストール
3. プロジェクトルートに .env を置く（自動ロードされます。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   - 自動ロード順: OS 環境変数 > .env.local > .env
   - .env 解析は export KEY=val やクォート、コメント等に対応
4. データディレクトリの作成:
    mkdir -p data

主要な環境変数（代表）
---
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須となる処理あり）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE プッシュ）用
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID 保存先（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60）

注意: Settings は自動で .env をロードします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

実行方法
---
1) 監視ループ（SystemMonitor 単体の簡易起動）
    python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を上書き（例: MONITOR_POLL_INTERVAL=30）
   - 監視は常に「本番用」監視 DB（Settings.sqlite_path）を使用します（環境に依存せず）

2) ExecutionEngine（注文実行）起動
    # 本番環境
    KABUSYS_ENV=live python -m kabusys.run_execution

    # Paper Trading（MockBroker を使用し data/paper_trading.db に記録）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   - ExecutionEngine 起動時に PID ファイル（デフォルト data/execution.pid）を作成します
   - Paper Trading の DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に分離されます

3) streamlit ダッシュボード（監視 DB の可視化）
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

   - read-only モードで SQLite を URI 経由で開きます
   - DB が存在しない場合はエラー表示されます（MonitoringEngine を先に起動してください）

4) Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で SQLite ファイルを指定可能（優先順: --db > PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）
   - 稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を表示します

5) AI（ニュース NLP / レジーム判定）プログラム呼び出し（プログラム的に利用する例）
    from datetime import date
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,11), api_key="sk-...")

   - OpenAI API キーが引数にない場合は環境変数 OPENAI_API_KEY を参照
   - score_regime（市場レジーム判定）も同様に提供されています（kabusys.ai.regime_detector.score_regime）

設定と挙動のポイント
---
- .env の自動ロード:
  - プロジェクトルートは .git または pyproject.toml を起点に探索します
  - 見つからない場合、自動ロードをスキップ
  - OS 環境変数は保護され、.env.local の override を無効にできます（protected 機構）

- paper_trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、記録先 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります。本番 DB と完全に分離されます。

- モニタリング:
  - monitoring_db.init_monitoring_db() は冪等実行可能で、既存 DB に対する必要なカラム追加等の簡単なマイグレーションを行います
  - kill.flag を書き込むと ExecutionEngine 側で停止シグナルとして検出できます（KillSwitch）

- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（プラットフォーム依存の実装）
  - 権限不足等で設定に失敗しても警告を出してスキップします

開発・テストヒント
---
- モジュール単位でのテスト:
  - portfolio/*.py、research/*.py、monitoring/* は副作用を限定しており単体テストが書きやすく設計されています
- OpenAI API 呼び出し箇所は外部呼び出しを隠蔽するヘルパー関数を通して実行しているため、ユニットテストではそれらを patch / mock してください
- Settings の自動 .env ロードを無効にしたいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください

ディレクトリ構成
---
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py            — 市場レジーム判定（MA + LLM）

- data/ (別モジュール想定: prices_daily / raw_financials を DuckDB で保持)

- execution/
  - order_manager.py
  - reconciler.py
  - (その他 broker_* / order_repository など実装ファイル群)

- monitoring/
  - __init__.py
  - monitoring_db.py              — SQLite テーブル定義・永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
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

- tools/
  - __init__.py
  - paper_verification_report.py  — Paper Trading 検証レポート出力スクリプト

- utils/
  - __init__.py
  - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ

補足
---
- SQLite / DuckDB のデフォルトファイル:
  - Monitoring DB: data/monitoring.db
  - Paper Trading DB: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb
- ログレベルやしきい値等は Settings 経由で環境変数から調整可能です（LOG_LEVEL / CPU_THRESHOLD_PCT 等）。
- 本 README はコード内の docstring と実装に基づいた概要です。実際の運用では .env の整備および必要なデータ（prices_daily / raw_financials / raw_news 等）の準備が必要です。

ライセンス / 貢献
---
（必要に応じてここにライセンスやコントリビュート方法を追記してください）

以上。必要があれば、サンプル .env のテンプレートや起動スクリプトの systemd ユニット例、docker-compose 設定例なども追加で作成します。どの情報を優先して追加しますか？