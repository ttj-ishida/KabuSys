KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ユーティリティをまとめた Python パッケージです。  
主要機能は取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・リサーチ、ニュース NLP を用いた AI スコアリングなどを含みます。  
設計方針としては「本番／ペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」を重視しています。

主な機能一覧
-------------
- 実行（ExecutionEngine）
  - 本番 / ペーパートレードを切替可能（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
  - リスク管理（RiskManager）・注文管理（OrderManager）・再突合（Reconciler）などを統合

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック
  - TradeMonitor / RiskMonitor: 滞留注文やドローダウン等の監視とログ記録
  - KillSwitch: しきい値超過で data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
  - MonitoringEngine: 上記モニタを定期ポーリングしてアラート管理

- ポートフォリオ構築（Portfolio）
  - 銘柄選定（スコア降順）、等金額／スコア加重配分
  - セクターキャップ適用、レジーム乗数、株数決定（単元丸め、リスクベース配分、aggregate cap）

- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン / IC（Information Coefficient）計算、統計サマリ

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリング（ai_scores への書込）
  - マクロニュース + ETF ma200 を用いた市場レジーム判定（market_regime への書込）
  - リトライやパース検証、スコアのクリップ等の堅牢な実装

- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
  - ロギング / プロセス優先度設定ユーティリティ

セットアップ手順
----------------
1. リポジトリをチェックアウトし、Python 仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする（pip 等）:
   - 必要なパッケージ例: duckdb, psutil, openai, PyYAML（YAML 検証用）
   - 例: pip install duckdb psutil openai PyYAML

3. .env を作成する:
   - 対話型ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記は最低必須環境変数）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - そのほか: DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 機能利用時）

4. 設定を検証する:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリとログディレクトリが自動作成されますが、パーミッション等に注意してください。
   - デフォルト DB パス: data/kabusys.duckdb（DuckDB）、data/monitoring.db（SQLite）
   - ログ: logs/<app_name>.log（日次ローテーション、30日保持）

主要環境変数（抜粋）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live)

- データベース:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
  - PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定動作

- ログ / 実行:
  - LOG_LEVEL (DEBUG / INFO / ...)
  - LOG_DIR
  - PID_FILE_PATH / KILL_FLAG_PATH（デフォルトは data/execution.pid / data/kill.flag）

- 監視:
  - MONITOR_POLL_INTERVAL（秒。run_monitoring のポーリング間隔。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector が必要）

使い方（起動・主要コマンド）
---------------------------
- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path を使用（環境に依らず monitoring DB は共通）

- ExecutionEngine（取引エンジン）を起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - data/execution.pid に PID を書きます（停止時は削除）

- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 短い要約（稼働率・注文成功率・レイテンシ等）を標準出力に出します。

- AI 機能（プログラムからの呼び出し）:
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（引数で渡すことも可）

停止・Kill Switch
-----------------
- KillSwitch は監視側がしきい値を検出した場合 data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動停止（エンジンの強制停止）をしたい場合は data/kill.flag を作成してください（内容は理由文字列）。
- run_execution/run_monitoring はプロジェクトルート下の data/stop_requested.flag も監視しており、このファイルが存在すると起動を抑止または実行中の終了に使われます。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

データベース（マイグレーション・スキーマ）
--------------------------------
- monitoring_db.init_monitoring_db() は監視用 SQLite に必要テーブルを作成します（冪等）。テーブル:
  - system_status, trade_logs, positions, risk_logs, dashboard
- 既存 DB に対する軽微なマイグレーション（例: dashboard.peak_value, trade_logs.latency_ms の追加）を自動的に行います。

ログ
---
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
  - stdout（StreamHandler）と日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定
  - LOG_LEVEL / LOG_DIR で動作を制御可能
  - ログはデフォルトで logs/ に出力され、30 日分保持されます

ディレクトリ構成（主要ファイル・モジュール）
-------------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数の読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ入口スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （滞留注文などの監視）※詳細はコード参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — （通知管理）※詳細はコード参照
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション実行）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py     — マーケットレジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

注意事項 / ベストプラクティス
------------------------------
- 本番(KABUSYS_ENV=live) では .env の取り扱いに注意し、.env を Git に含めないこと。
- KILL_FLAG_CLEAR_ON_START は本番では 0 にしておくこと（自動クリアは危険）。
- OPENAI_API_KEY を環境変数経由で安全に管理してください（Vault/Secrets Manager の利用推奨）。
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を使用）。実際の発注は paper_trading では行われません。

問い合わせ・拡張
----------------
- 新しい戦略やブローカ（kabuステーション以外）を追加する際は BrokerClientFactory を拡張してください。
- 解析・レポート機能は DuckDB 上の prices_daily / raw_financials / raw_news テーブルを参照する設計です。データ投入パイプラインは kabusys.data パッケージに実装できます（本リポジトリにデータパイプライン実装があればそれに従ってください）。

以上が本リポジトリの概要・セットアップ・使用方法です。詳細なモジュール実装やパラメータは各ソース（src/kabusys 以下）を参照してください。必要であれば、README に追記するコマンド例や運用手順（systemd ユニット、cron、コンテナ化等）のテンプレートも作成します。必要に応じて教えてください。