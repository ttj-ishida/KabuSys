KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python パッケージ群です。  
主な責務は以下の通りです。

- シグナルに基づく発注（ExecutionEngine）
- 発注の再同期・リコンシリエーション（Reconciler）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ファクター計算・特徴量探索（Research）
- ニュースベースの NLP スコアリング（OpenAI を利用）
- システム・取引・リスク監視（Monitoring）
- 監視ダッシュボード（Streamlit）

主要機能
--------
- Execution（発注エンジン）
  - Signal Queue Pull 型の発注ループ
  - Gate（シグナル／エグゼキューション／ドレイン）による多段安全チェック
  - Broker 抽象化により paper_trading（モック）と live（実ブローカー）を切替可能
  - 再起動後の自動リコンシリエーション

- Portfolio（銘柄選定・配分・ポジションサイズ決定）
  - スコア順ソート / 等配分 / スコア加重
  - レジーム乗数、セクター集中抑制、単元株丸め、aggregate cap 処理

- Research（ファクター・探索）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）や統計サマリー

- AI（ニュースセンチメント / レジーム判定）
  - OpenAI（gpt-4o-mini を想定）を使ったニュースの銘柄別センチメントスコアリング
  - マクロニュース＋ETF MA200 を合成した市場レジーム判定
  - API のリトライ・検証・クリッピングなど堅牢性を考慮

- Monitoring（監視）
  - system_status / trade_logs / positions / risk_logs / dashboard を SQLite に永続化
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine 停止シグナル、LINE でのアラート送信（push）
  - Streamlit ダッシュボードで状況確認

セットアップ手順
----------------

1. Python 環境の作成（例）
   - 推奨: Python 3.9+
   - 仮想環境作成:
     ```
     python -m venv .venv
     source .venv/bin/activate    # macOS / Linux
     .venv\Scripts\activate       # Windows
     ```

2. 依存パッケージのインストール（想定パッケージ）
   - 例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - 実プロジェクトでは requirements.txt を用意している想定でそれを利用してください。

3. リポジトリの配置方法
   - ソースはパッケージ形式（src/kabusys）で配置されています。開発中は PYTHONPATH を指定して実行します:
     ```
     export PYTHONPATH=src   # macOS / Linux
     set PYTHONPATH=src      # Windows (cmd)
     ```

4. 環境変数
   - 必須（実ブローカーや外部 API を使う場合）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 主要な設定:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
       - paper_trading の場合、Execution は data/paper_trading.db を使用し MockBroker を利用
       - 監視（Monitoring）は KABUSYS_ENV にかかわらず常に本番 sqlite_path を使用します
     - SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
     - PID_FILE_PATH: pid ファイル（デフォルト data/execution.pid）
     - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   - 簡易 .env 例（プロジェクトルートに .env を置く）:
     ```
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     KABU_API_PASSWORD=your_kabu_password
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```

使い方（起動例）
----------------

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）。
  - 例:
    ```
    export PYTHONPATH=src
    MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    ```
  - 注意: run_monitoring は Monitoring 用 DB（settings.sqlite_path）を常に使用します。

- ExecutionEngine（発注エンジン）を起動
  - paper_trading モードでは MockBroker を使用し data/paper_trading.db に記録します。
  - 例（ペーパートレード）:
    ```
    export PYTHONPATH=src
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 例（本番）:
    ```
    export PYTHONPATH=src
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

- Streamlit ダッシュボード
  - 監視 DB（SQLite）を読み取り専用で表示するダッシュボードです。
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- AI（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - Python インタプリタやスクリプトから呼び出す例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 3, 20), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 3, 20), api_key="sk-...")
    ```

- kill.flag の操作
  - KillSwitch により kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine は安全に停止する設計です。
  - ExecutionEngine 起動時に kill.flag を手動でクリアしたい場合:
    ```
    rm data/kill.flag
    ```
    または Settings.kill_flag_clear_on_start を利用するフローが組み込まれている場合があります（環境変数で設定）。

実装上の主要ポイント / 注意事項
-------------------------------
- process priority
  - run_monitoring / run_execution 起動時に set_process_priority("high") を試みます（psutil を使用）。
  - 権限やプラットフォームによっては警告が出てスキップされます。

- DB 初期化
  - init_monitoring_db() が呼ばれ、必要なテーブルとインデックスを冪等的に作成します。
  - monitoring 側は起動時に必ず監視 DB を初期化します（存在しなくても作成されます）。

- paper_trading
  - KABUSYS_ENV=paper_trading の場合、発注はモックブローカーに送られ、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録されます。本番 DB とは分離されます。

- DuckDB
  - ファクター計算・ニュース集計・リサーチ処理は DuckDB（settings.duckdb_path）を参照します。DuckDB に必要なテーブル（prices_daily / raw_financials / raw_news など）があることが前提です。

- OpenAI 使用時の堅牢性
  - レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライします。
  - レスポンスの JSON 検証とクリッピングを行い、異常系ではフェイルセーフ（スコア 0 等）にフォールバックする設計です。

ディレクトリ構成（主要ファイル）
-------------------------------
（ソースは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - broker_api.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py (DuckDB 等データ操作ユーティリティを含む想定)
  - utils/
    - process_priority.py

（上記は主要モジュールの抜粋です。実装はさらに細かなモジュールで構成されています。）

開発・拡張のヒント
-------------------
- 単体関数群（portfolio/*.py、research/*.py）は副作用が少なく、ユニットテストが容易です。
- OpenAI 呼び出し部分は個別関数（_call_openai_api）に分離されているため unittest.mock.patch で容易に差し替えできます。
- MonitoringDB は SQLite を直接操作する薄い永続化層です。マイグレーション処理が簡易に含まれています。

サポート / 貢献
----------------
- バグレポートや改善提案は issue を作成してください。設計・実装の一貫性を保つため既存のパターン（冪等性・フェイルセーフ）に従ってください。

以上がこのコードベースの概要と使い方です。必要であれば各モジュールの API 使用例や .env.example のテンプレート、docker-compose 例などを追記します。どの情報を優先してさらに詳しく記載しましょうか？