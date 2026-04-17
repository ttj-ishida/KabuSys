KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買 / 研究 / モニタリングを目的とした小規模なシステム群です。  
主要機能は次の通りです。

- 実行エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- モニタリング（System / Trade / Risk）とアラート（LINE Push）
- Paper Trading 用の分離された SQLite DB と MockBroker サポート
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限等）
- 研究用モジュール（ファクター計算・将来リターン・IC など）
- AI モジュール（ニュースセンチメント評価 / 市場レジーム判定：OpenAI を利用）
- 運用補助ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

主要な設計方針:
- DB（DuckDB/SQLite）を使ったデータ処理・永続化
- 実運用と Paper Trading は DB を分離して安全に検証可能
- 外部 API（OpenAI / broker / 証券API）は必要な箇所のみ抽象化して呼び出す
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）

機能一覧
--------
- Execution
  - 起動スクリプト: run_execution.py
  - Broker クライアントのファクトリにより paper_trading 時は MockBroker を使用
  - Reconciler による再起動時の自動リコンシリエーション
- Monitoring
  - run_monitoring.py による継続ポーリング（SystemMonitor, TradeMonitor, RiskMonitor）
  - kill_flag による ExecutionEngine 停止シグナル
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio
  - 候補選定 / 等金額・スコア加重 / セクター制限 / ポジションサイズ算出
- Research
  - calc_momentum / calc_volatility / calc_value（DuckDB 接続を受ける純粋関数）
  - 将来リターン、IC、統計サマリ等
- AI
  - news_nlp.score_news: raw_news を OpenAI でセンチメント評価して ai_scores に書込
  - regime_detector.score_regime: ma200 乖離 + マクロニュースの LLM 評価で日次レジーム判定
- Tools
  - paper_verification_report.py: Paper Trading DB を集計して PASS/FAIL レポートを表示

セットアップ手順
----------------
1. Python 環境
   - Python 3.9+ を推奨（使用する機能に依存します）
   - 仮想環境を作成してアクティブ化することを推奨

     python -m venv .venv
     source .venv/bin/activate  # POSIX
     .venv\Scripts\activate     # Windows

2. 依存パッケージのインストール
   - プロジェクトに requirements.txt がある場合はそれを利用してください（現状サンプル）。
   - 必要な主要パッケージ（抜粋）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:

     pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env
   - ルートに .env/.env.local を置くと自動で読み込まれます（OS 環境変数を上書きしない挙動）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（一部）:

     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション接続パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring で参照）
     - LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   - 簡易 .env の例:

     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=

4. 初期データディレクトリ
   - data/ ディレクトリを作成しておく (実行時に自動作成する箇所もありますが、権限等に注意)。

使い方（主要スクリプト）
-----------------------

- 監視ループを起動

  - run_monitoring.py は SystemMonitor のポーリングループを起動します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能（デフォルト 60）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。

  実行例:

    python -m kabusys.run_monitoring

  停止:
    - プロジェクトルート/data/stop_requested.flag ファイルが作成されるとループを終了します。
    - Execution 停止を要求する場合は data/kill.flag を使用（KillSwitch 経由で Execution を停止）。

- 実行エンジンを起動（ExecutionEngine）

  - run_execution.py により ExecutionEngine を起動します。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/execution.pid を参照・作成してプロセス状態を管理します。
    - 既に data/stop_requested.flag が存在する場合は起動を中止します。

  実行例:

    python -m kabusys.run_execution

  停止:
    - data/stop_requested.flag を作成することでエンジンに停止を通知します。
    - または監視側でデッドライン到達時に kill.flag を書き込み、Execution 側がそれを検出して停止します。

- Paper Trading 検証レポート

  - tools/paper_verification_report.py は Paper Trading DB を集計して PASS/FAIL 判定を行います。

  実行例:

    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

  - 判定基準（デフォルト）
    - 稼働率 >= 99.0%
    - 注文成功率 (Filled / Created) >= 90.0%
    - 送信率 (Sent / Created) >= 95.0%
    - P95 latency <= 200 ms

- Streamlit ダッシュボード

  - 監視用ダッシュボードを起動:

    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  - 監視 DB を読み取り専用で開き、ポートフォリオ値・保有ポジション・直近注文・リスクログ等を表示します。

- AI モジュール（プログラムから利用）

  - ニュースセンチメント:

    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")

  - レジーム判定:

    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

  - 注意: OpenAI API キーが必要。API 呼び出しはバックオフ・エラーハンドリングを行いますが、キー未設定時は ValueError が投げられます。

設定と環境変数（代表）
-----------------------
- 自動 .env 読み込み
  - ルートにある .env / .env.local をプロセス起動時に自動で読み込みます（OS環境変数を上書きしない / 上書きするルールあり）。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 重要な Settings プロパティ（Settings クラスに定義）
  - jquants_refresh_token, kabu_api_password
  - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - line_channel_access_token, line_user_id
  - duckdb_path (デフォルト data/kabusys.duckdb)
  - sqlite_path (デフォルト data/monitoring.db)
  - paper_sqlite_path (PAPER_TRADING_SQLITE_PATH / default data/paper_trading.db)
  - paper_fill_mode (instant|partial|never|reject)
  - pid_file_path, kill_flag_path
  - cpu/memory/disk thresholds
  - KABUSYS_ENV (development|paper_trading|live)

運用上の注意
------------
- Monitoring は Settings.sqlite_path の DB を使用します（run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照する点に注意）。
- Paper Trading は paper_sqlite_path を使って本番 DB と完全分離する設計です（run_execution は env に応じて DB を切り替えます）。
- stop_requested.flag / kill.flag によりプロセス間で停止シグナルをやり取りします（フラグファイル方式）。
- Process priority（優先度）や CPU affinity の設定は psutil を利用しており、権限不足時は警告でスキップされます。
- OpenAI 呼び出しはレート制限や一時エラーに対して指数バックオフを行いますが、API コストやレートに注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py               — パッケージ定義、バージョン等
- config.py                 — Settings クラス（.env 自動読み込み、環境変数管理）
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py          — SQLite schema / 永続化ラッパー（MonitoringDB）
- system_monitor.py         — システム・データ鮮度チェック
- trade_monitor.py          — 注文滞留・約定異常チェック
- risk_monitor.py           — ドローダウン・ポジション上限監視
- kill_switch.py            — kill.flag の作成/評価
- alert_manager.py          — LINE による通知実装
- monitoring_engine.py      — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py    — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py
- order_repository.py
- reconciler.py
- execution_engine.py (Engine 実装)
- broker_factory / broker_api / broker clients (ブローカー抽象)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py               — ニュースセンチメント（OpenAI）
- regime_detector.py        — 市場レジーム判定（MA200 + マクロニュース + LLM）

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

src/kabusys/utils/
- process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

ライセンス / 責任範囲
--------------------
- このプロジェクトはサンプル実装の集合であり、取引戦略・実運用の安全性や法令順守を保証するものではありません。実運用や資金を投入する前に十分な検証を行ってください。
- OpenAI / ブローカー API / 証券会社との接続は別途契約・設定が必要です。API キーやパスワードは安全に管理してください。

追加情報 / 開発メモ
-------------------
- テスト用に .env.example を用意し、必要な環境変数を記載しておくと便利です。
- DuckDB のスキーマや prices_daily / raw_financials 等のデータ投入は別途 ETL パイプライン（kabusys.data.pipeline 等）を使用します。
- モジュール設計は純粋関数（research/portfolio）と I/O を伴うクラス（monitoring_db/OrderRepository）を分離しています。ユニットテストを作成しやすい構成です。

以上。必要であれば README に記載するコマンド例や環境変数のより詳細な説明、運用手順（デプロイ / systemd / コンテナ化）も追記します。どの範囲を掘り下げたいか教えてください。