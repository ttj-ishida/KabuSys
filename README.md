KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けの自動売買および研究ツールキットです。本リポジトリは次の主要機能を含みます:

- 実行エンジン（ExecutionEngine）と監視（Monitoring）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- ファクター計算・特徴量探索（Research）
- ニュース NLP / 市場レジーム判定（OpenAI を利用した AI モジュール）
- Paper Trading 用の分離された DB と検証ツール
- 環境設定ウィザード、設定検証 CLI、ログ設定ユーティリティ

特徴一覧
--------
- 環境変数 & .env を用いた柔軟な設定管理（.env 自動読み込み、.env.local サポート）
- Execution と Monitoring を分離。paper_trading モードは専用 SQLite DB を使用して本番 DB と分離
- DuckDB を用いた分析（prices_daily / raw_financials 等を想定）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）や市場レジーム判定
- ログはコンソール(stdout) と日次ローテーションファイルに出力（logs/<app>.log）
- Kill Switch（data/kill.flag）による安全停止、停止フラグ（data/stop_requested.flag）によるプロセス停止制御
- Paper Trading の検証レポート生成ツール

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨（型記法や pathlib の挙動に依存）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルの検証に利用。必須ではない）
インストール例:
  pip install duckdb psutil openai PyYAML

1. リポジトリのルートに移動（src パッケージ配置を前提）。
2. .env を作成:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照してください）。
3. 設定検証（必須環境変数や YAML の簡易検証）:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗として exit(1) になります。
4. データディレクトリとログディレクトリの権限を確認:
   - デフォルトの DB/ログパスは data/ および logs/ を想定。
   - 必要に応じて DUCKDB_PATH / SQLITE_PATH / LOG_DIR を .env で上書き。

主要な環境変数（抜粋）
---------------------
（デフォルト値は括弧内）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) (development)
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) (instant)
- LOG_LEVEL (INFO)
- LOG_DIR (logs/)
- OPENAI_API_KEY (AI 機能利用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知任意)
- KILL_FLAG_CLEAR_ON_START (0|1) (0 推奨)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒, デフォルト 60)

使い方（コマンド）
-----------------

主な起動・ユーティリティ

- 環境セットアップ（対話式 .env 生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  python -m kabusys.run_execution
  挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録する。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了する。
    - 実行中は data/execution.pid に PID を書く（設定で上書き可能）。
    - 停止要求は data/stop_requested.flag により受け付ける。

- Monitoring 起動
  python -m kabusys.run_monitoring
  挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを永続化する。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行える。

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD
    --to   YYYY-MM-DD
    --db PATH （デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI モジュール（プログラムから利用）
  - ニューススコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key=None)
    ※ api_key が None の場合は環境変数 OPENAI_API_KEY を参照

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)

ログとファイル
--------------
- ログ: デフォルト logs/<app_name>.log（日次ローテーション・30日保持）
  app_name 例: execution, monitoring
- 停止フラグ:
  - data/stop_requested.flag — 起動済みスクリプトを優雅に停止させるためのフラグ（run_monitoring/run_execution が監視）
  - data/kill.flag — Kill Switch により ExecutionEngine を停止させるためのフラグ（監視→書き込み）
- 実行 PID ファイル:
  - data/execution.pid（ExecutionEngine）

動作上の注意
------------
- paper_trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必要です。API 呼び出し失敗時はフェイルセーフ（多くのケースで 0.0 やスキップ）で継続する設計です。
- .env ファイルは機密情報を含みうるため Git にコミットしないでください（config_setup もその旨を注意喚起しています）。
- MONITOR_POLL_INTERVAL に 0 以下の値を与えるとデフォルト（60 秒）にフォールバックします。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は本リポジトリの主要モジュール（src/kabusys 配下）を抜粋した構成例です:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/.env 読み込みと Settings
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        — SQLite ベースの永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/                — Execution 関連（Engine, OrderManager, BrokerFactory 等）
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
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
    - data/                      — （ランタイムに作成される想定）DB / フラグ / PID 等

（注）上記はコードベースの主要部分のみを示しています。細かいファイルや追加モジュールはディレクトリを参照してください。

運用・デプロイのヒント
---------------------
- systemd や supervisor, Docker, Kubernetes 等を利用する場合は、ログディレクトリと data ディレクトリの永続化を確保してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動クリアは危険）。
- ExecutionEngine と Monitoring は別プロセスで実行し、Monitoring を通じて Kill Switch（data/kill.flag）で安全停止する運用を推奨します。
- 定期的に python -m kabusys.tools.paper_verification_report などで Paper Trading のモニタリング結果を出力して品質を確かめてください。

サポートライブラリ（要インストール）
-----------------------------------
- duckdb
- psutil
- openai
- PyYAML（任意：validate_config の YAML チェックを有効にするため）

最後に
-----
この README はソースコードの現状に基づいた利用説明です。各モジュールの詳細な API や内部挙動は該当モジュールの docstring / コメントを参照してください。追加の質問やドキュメント化したい箇所があれば教えてください。