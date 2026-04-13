README — KabuSys
===============

概要
----
KabuSys は日本株自動売買のためのコンポーネント群（実行エンジン、モニタリング、ポートフォリオ構築、リサーチ、AI 補助）を含む Python パッケージです。本リポジトリは発注ロジックと監視/検証ツールを分離し、安全性（フェイルセーフ、リコンシリエーション、kill-switch 等）を重視した設計になっています。

主な機能
--------
- ExecutionEngine 起動（run_execution.py）
  - 本番 / ペーパートレードの切替
  - ブローカー抽象化（実ブローカー or MockBroker）
  - リスク管理・発注管理・リコンシリエーション
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文状況、ドローダウン監視
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE によるアラート通知（AlertManager）
  - Streamlit 監視ダッシュボード
- Portfolio 建設ロジック（candidate 選定、重み計算、ポジションサイジング、セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI 補助
  - ニュース NLP による銘柄センチメント（OpenAI を使用）
  - 市場レジーム判定（ETF MA + マクロセンチメント）
- 検証ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提 / 必要ライブラリ
--------------------
- Python 3.9+（typing の一部機能を利用）
- 主要依存（例）
  - duckdb
  - psutil
  - requests
  - openai (OpenAI SDK)
  - streamlit（ダッシュボード）
- 環境により追加の依存が必要になる場合があります。requirements.txt がある場合はそれを利用してください。

設定（環境変数）
----------------
このパッケージは環境変数（または .env / .env.local）から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を検出して行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（抜粋）:
- KABUSYS_ENV: 起動環境 (development | paper_trading | live)。デフォルト: development
- SQLITE_PATH: 監視用 SQLite ファイルパス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用）。デフォルト: data/paper_trading.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PID_FILE_PATH: ExecutionEngine PID ファイルパス。デフォルト: data/execution.pid
- KILL_FLAG_PATH: kill flag ファイルパス。デフォルト: data/kill.flag
- PAPER_FILL_MODE: MockBroker の約定挙動 ("instant" | "partial" | "never" | "reject")。デフォルト: "instant"
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の必須トークン/パスワード
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO

デフォルトのデータパス（重要）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- kill.flag: data/kill.flag

セットアップ手順（例）
--------------------
1. リポジトリをクローンし、仮想環境を作る:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install -r requirements.txt
   （requirements.txt がない場合は上の主要依存を個別インストールしてください）

3. 必要なディレクトリを作成:
   - mkdir -p data

4. 環境変数を設定:
   - プロジェクトルートに .env を置くか、環境変数をエクスポートしてください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development

5. DB 初期化:
   - run_execution.py / run_monitoring.py 実行時に init_monitoring_db() が呼ばれ、監視テーブルは自動で作成されます。
   - DuckDB のテーブルは別途用意してください（prices_daily / raw_news / raw_financials 等をロードする処理が想定されます）。

使い方（主なスクリプト）
-----------------------

- 監視ループを起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を使います（環境にかかわらず monitoring DB は本番パスを参照する実装）。

- 実行エンジンを起動
  - 本番/ペーパーは KABUSYS_ENV によって切替
    - KABUSYS_ENV=paper_trading にすると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - python -m kabusys.run_execution

- Streamlit 監視ダッシュボード
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - 実行例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、raw_news → ai_scores に書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算し market_regime テーブルへ書き込みます。
  - いずれも OPENAI_API_KEY (または api_key 引数) が必要です。

注意点 / 運用メモ
-----------------
- Paper Trading は本番 DB と完全分離され、PAPER_TRADING_SQLITE_PATH に記録されます（KABUSYS_ENV=paper_trading）。
- MONITOR_POLL_INTERVAL が 0 または負の数のときはデフォルト (60 秒) にフォールバックします。
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（プラットフォームに依存）。
- kill.flag の存在を監視して ExecutionEngine 停止を指示できます。KillSwitch は一度書き込まれたフラグを再作成しません（冪等）。
- .env の読み込み順: OS 環境 > .env.local > .env。プロジェクトルートが特定できない場合は自動ロードがスキップされます。
- 自動ロードをテストで無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

監視用 SQLite スキーマ（概要）
----------------------------
init_monitoring_db() により以下テーブルが作成されます（冪等）:
- system_status: cpu/memory/disk/process_ok と記録日時
- trade_logs: 発注イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: code 単位の保有情報
- risk_logs: リスクイベントログ（dedup 機能あり）
- dashboard: 集計（id=1 の1行で保持、peak_value 列あり）

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定読み込み
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ...（ブローカー関連等）
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
- tools/
  - paper_verification_report.py

開発・テスト向け
----------------
- 自動環境変数読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部 API をモックしてテスト可能（コード内で _call_openai_api を patch する設計）
- MonitoringEngine.run_once() を使って単発実行テストが可能

最後に
-----
本 README はコードベースから読み取れる実装意図・設定・起動方法をまとめたものです。実際の運用では外部 API キーや機密情報の管理（Vault や CI/CD の Secret 管理）を推奨します。README で不足している運用フローや詳細が必要であれば、追加で記載します。