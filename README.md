README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模な統合コードベースです。  
主なコンポーネントは取引実行エンジン（ExecutionEngine）、監視サブシステム（Monitoring）、ファクター/リサーチ、ポートフォリオ構築、AI を使ったニュース解析/レジーム判定、および各種ツール群です。  
設計方針として「本番 DB と paper trading の明確分離」「ルックアヘッドを避ける時刻処理」「外部 API 呼び出しは明示的制御」「フェイルセーフ（API失敗時のフォールバック）」が保たれています。

主な機能
--------
- Execution
  - ブローカー抽象化・OrderManager による注文ライフサイクル管理
  - 起動時のリコンシリエーション（Reconciler）で再起動後の状態同期
  - Paper Trading モード（完全に本番 DB と分離した SQLite に記録）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - KillSwitch による flag ファイル経由の停止シグナル
  - LINE を使ったアラート通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用）
  - ユーティリティ: 監視 DB スキーマ初期化（init_monitoring_db）
- Research / Data
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC 計算・統計サマリ
- Portfolio construction
  - 候補選定、等重・スコア加重、リスク調整（セクター上限、レジーム乗数）、株数決定（単元丸め・aggregate cap など）
- AI
  - ニュースのセンチメントを OpenAI（gpt-4o-mini）でスコア化して ai_scores に保存
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（market_regime への書き込み）
  - API 呼び出しに対するリトライ / バックオフ / バリデーション実装
- Tools
  - Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - その他ユーティリティ群

必須・推奨依存パッケージ（例）
----------------------------
このリポジトリには requirements ファイルが含まれていません。実行に必要な代表的なパッケージは以下です。

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- （必要に応じて）その他ライブラリ

pip 例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil requests openai streamlit

セットアップ手順
---------------
1. リポジトリをクローンして Python 仮想環境を作成します。
2. 必要なパッケージをインストールします（上記参照）。
3. 環境変数を設定します。
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
4. DB パスのディレクトリ（data/ 等）を作成してください。監視・実行時に自動作成されるファイルもありますが、権限などで問題がある場合は事前に用意してください。

主な環境変数（重要なもの）
--------------------------
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Execution は paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離します。
- SQLITE_PATH: 監視 DB（SQLite）のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の約定モード（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 実運用で必要な各種 API トークン
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定
- MONITOR_POLL_INTERVAL: run_monitoring による監視ポーリング間隔（秒）。1 以上の整数。デフォルト 60。

注意点
- run_monitoring は説明ファイル内にある通り、監視用途は KABUSYS_ENV にかかわらず production（settings.sqlite_path）を参照します（監視は常に実稼働 DB を監視する前提）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行います。

使い方（例）
------------

1) 実行エンジン（ExecutionEngine）を起動する
- 本番/開発: KABUSYS_ENV に応じてブローカーが選択されます（paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録されます）。
- 起動コマンド:
    python -m kabusys.run_execution
- 実行前に環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定してください。
- 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

2) 監視ループを起動する
- run_monitoring は永続的に SystemMonitor.check_once() をポーリングします。
- 起動コマンド:
    python -m kabusys.run_monitoring
- ポーリング間隔を変更する:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3) Paper Trading 検証レポートを生成する
- コマンド:
    python -m kabusys.tools.paper_verification_report
    # 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB パス指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4) Streamlit ダッシュボード（監視可視化）
- 起動例（ローカルの monitoring DB を読み取り専用で開く）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードではダッシュボード集計、ポジション、注文履歴、最新のシステムステータス・リスクログを参照できます。

5) AI 機能（ニューススコアリング / レジーム判定）
- OpenAI API キーが必要です（OPENAI_API_KEY）。
- プログラムから利用する場合（例）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10), api_key="sk-...")

内部の実装注意点（運用者向け）
--------------------------------
- MonitoringDB（init_monitoring_db）で system_status, trade_logs, positions, risk_logs, dashboard のテーブルと必要なインデックスを作成します。既存 DB のマイグレーション処理（カラム追加）も一部行います。
- KillSwitch はファイルベース（KILL_FLAG_PATH）で ExecutionEngine に停止指示を出す設計です。冪等性のため既存ファイルがあれば書き換えません。
- Execution 起動時と Monitoring 起動時はいずれもプロセス優先度を high に設定しようと試みますが、権限不足等で失敗することがあります（ログに警告）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_execution.py               — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト（エントリポイント）
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 用永続化層（init + MonitoringDB クラス）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (※実装あり前提)
    - execution_engine.py (※実装あり前提)
    - broker_factory.py (※実装あり前提)
    - broker_api.py (※インターフェース)
    - order_record.py
    - risk_manager.py
    - ...（他の実行関連ファイル）
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/
    - pipeline.py (prices/last-date utilities, used by system_monitor 等)
    - stats.py (zscore_normalize 等、research で利用)

補足（開発者向け）
-----------------
- 単体テストを行う場合は Settings の自動 env ロードを無効化するか、必要な .env をテスト用に用意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- AI モジュールは外部 API 呼び出し部分をテストで差し替えられるように設計されています（_call_openai_api を patch する等）。
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。実データを使う前にスキーマ整備を確認してください。

ライセンス・著作権
-----------------
（この README には記載がありません。プロジェクトのライセンスファイルに従ってください。）

以上。必要に応じて README にサンプル .env.example、requirements.txt、起動 systemd ユニット例、デプロイ手順などを追加できます。追加を希望する項目を教えてください。