README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした Python コードベースです。
主な機能は以下のカテゴリに分かれます:

- 注文実行 / リコンシリエーション（ExecutionEngine、OrderManager、Reconciler）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、AlertManager）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI ユーティリティ（ニュースセンチメント評価、レジーム検出）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

特徴
----
- 実運用／Paper Trading を環境変数で切り替え（KABUSYS_ENV）
- SQLite（監視ログ等）および DuckDB（時系列・ファイナンスデータ）を使用
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価・レジーム判定機能
- LINE によるアラート送信（AlertManager）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil を利用）
- フェイルセーフ設計（DB マイグレーション・トランザクション・バックオフ等）
- Streamlit ベースの監視ダッシュボード（読み取り専用）

動作要件（推奨）
----------------
- Python 3.10+
- 必要な Python パッケージ（一例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - そのほか標準ライブラリ（sqlite3 など）

インストール（例）
-----------------
1. 仮想環境を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合はそれを使用してください: pip install -r requirements.txt）

設定（環境変数）
---------------
環境変数は OS 環境またはプロジェクトルートの .env / .env.local ファイルで設定可能です。
自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

主な環境変数:
- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live") — デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の fill モード ("instant" | "partial" | "never" | "reject")
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

簡単な .env 例:
- KABUSYS_ENV=paper_trading
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

セットアップ手順
--------------
1. 必要な DB ディレクトリを作成:
   - mkdir -p data

2. 環境変数を設定（上記参照）

3. 必要な Python パッケージをインストール（上記参照）

使い方
------

1) 注文実行（ExecutionEngine）を起動
- 実行方法（パッケージが PYTHONPATH にあることを前提）:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH の DB に記録して本番 DB と分離します。
  - 起動時にプロセス優先度を "high" に設定します。
  - 設定やブローカーは kabusys.config.Settings を参照します。

2) 監視ループを起動
- 実行方法:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（1 秒以上を指定）
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor などを組み合わせて定期チェックを行い、SQLite（Monitoring DB）へログを書きます。
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（監視 DB）を使用します。

3) Streamlit ダッシュボード（監視 UI）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用で監視 DB を参照し、Overview / Positions / Orders / System 情報を表示します。

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を評価し PASS/FAIL 判定を出力します。

5) AI ユーティリティ（プログラム内 API）
- ニュースセンチメント取得:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)  — DuckDB 接続と日付を渡して ai_scores テーブルへ書き込み
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

ログ / アラート
---------------
- LINE への通知: kabusys.monitoring.alert_manager.AlertManager を使用
  - トークン/ユーザが未設定の場合は送信はスキップされ、ログに警告が残ります。
- リスクイベント、トレードログ、システム状態は SQLite の monitoring DB に保存されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要なファイル構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings 管理（.env 自動ロード）
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite スキーマ & MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Execution 関連モジュール: broker_api, order_repository, execution_engine 等)
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
    - __init__.py
    - paper_verification_report.py

補足・運用上の注意
-----------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の位置）を探索して行います。CI / テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は明確に分離されています（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を使う機能は API 呼び出しで課金されるためテスト時は注意してください。テストでは _call_openai_api をモックする設計になっています。
- Monitoring のログスキーマは冪等的に初期化され、既存 DB に対するカラム追加マイグレーション処理も含まれています。
- モジュール設計はフェイルセーフ（API 失敗時にスキップ／デフォルト値で継続）を重視していますが、運用時はログと通知を確認して手動介入してください。

ライセンス / 貢献
-----------------
本 README はコードベースに基づくサマリです。実際のライセンス、貢献フローはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

以上。変更点の追加説明や .env.example 作成、セットアップスクリプト化（Makefile / docker-compose 等）の補助が必要であればお知らせください。