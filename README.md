KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・運用監視を想定した Python パッケージです。  
このリポジトリは以下の主要機能を持ち、運用用エンジン（ExecutionEngine）と監視（Monitoring）を切り離して実行できます。

主な特徴
--------
- ExecutionEngine：発注・注文管理・リコンシリエーション・リスク管理を含む実行コンポーネント
  - 本番（live）とペーパートレード（paper_trading）を分離
- Monitoring：システム健全性（CPU/メモリ/ディスク）、データ鮮度、注文ログ、ダッシュボード監視
  - Kill Switch による停止フラグ（data/kill.flag）発動
- ポートフォリオ構築モジュール（候補選定・重み付け・ポジションサイズ計算・セクターキャップ等）
- 研究用モジュール（ファクター計算 / 特徴量探索 / IC 計算）
- AI 統合（ニュースセンチメント評価 / レジーム判定） — OpenAI API 利用
- 運用支援スクリプト（.env ウィザード、設定検証、Paper Trading レポート等）
- SQLite（監視ログ） + DuckDB（分析用）をデフォルトで使用

必要条件
--------
- Python 3.10+
- 推奨パッケージ（最低限の例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML をチェックする場合に必要）
- OS: Linux / macOS / Windows（process priority 周りは OS により動作差あり）

インストール（例）
-----------------
1. リポジトリをクローン:
   git clone <repo-url>
2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. パッケージをインストール（最低限）:
   pip install duckdb psutil
   # AI 機能を使う場合
   pip install openai
   # 設定 YAML 検証を行う場合
   pip install pyyaml

.env の準備（推奨ワークフロー）
-----------------------------
- 対話式ウィザードで .env を作成 / 更新:
  python -m kabusys.config_setup
- 作成後、設定を検証:
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いになります。

重要な環境変数（代表）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）

重要（デフォルトあり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（SQLite）（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR — ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject、デフォルト instant）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60 秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

データ / フラグ / PID
--------------------
- data/kill.flag — Kill Switch（監視が発動時に作成されると Engine を停止させるためのフラグ）
- data/stop_requested.flag — 起動スクリプトや監視ループ停止の内部制御に使用
- data/execution.pid / data/*.pid — PID ファイル（ExecutionEngine など）
- デフォルトの DB ファイルやログは .env で変更可能

使い方（主要コマンド）
--------------------

1) 環境作成（.env）
- python -m kabusys.config_setup
  → 対話式に .env を作成します

2) 設定検証
- python -m kabusys.validate_config [--strict]
  → .env や config/*.yaml の基本的な妥当性チェックを実行

3) ExecutionEngine（取引エンジン）起動
- python -m kabusys.run_execution
  動作:
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）
  - 起動時に PID と停止フラグを確認し、別スレッドで engine.run_session を実行
  - 停止は data/stop_requested.flag を作成するか kill.flag による評価で行われます

4) Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
  オプション / 環境:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を使い周期的にチェックしてログ（SQLite）へ書き込み、必要に応じて Kill Switch を作動させます
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使う設計

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - PAPER_TRADING_SQLITE_PATH または --db で対象 DB を指定可能
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を出力し PASS/FAIL を判定

6) AI 関連（プログラム API）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - raw_news テーブルを参照して OpenAI へバッチ送信し ai_scores テーブルへ書き込み
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 1321 の MA200 乖離とマクロニュースを元にレジーム判定を行い market_regime テーブルへ書き込み
  - いずれも実行する際は OPENAI_API_KEY の設定が必要

ログ & ロギング
----------------
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...") を使用
- デフォルトではコンソール（stdout）と日次ローテーションされる logs/<app_name>.log に出力（30 日保持）
- ログディレクトリは LOG_DIR 環境変数または引数で変更可能

データベース初期化
-----------------
- 監視 DB 用のテーブル作成は init_monitoring_db(sqlite_conn) で行われ、起動スクリプトから呼び出されます（冪等）
- DuckDB は分析用に使用（パイプライン / research モジュールが接続を受け取る）

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       — （注文監視、コード参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知管理）
  - execution/               — Execution 関連コンポーネント（broker_factory, execution_engine, order_manager, risk_manager, reconciler 等）
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
  - monitoring/               — 監視用 DB 定義やロジック
  - tools/
    - paper_verification_report.py

運用上の注意 / ヒント
-------------------
- KABUSYS_ENV を "live" に設定する前に必ず validate_config で設定を確認してください。live では特に kill flag や通知設定に注意が必要です。
- ペーパートレードでは本番 DB と完全分離する設計になっています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能は API レートやコストの影響があるため、運用時に呼び出し回数やバッチサイズを制御してください（news_nlp.py の定数参照）。
- kill.flag（Settings.kill_flag_path）を手動で削除してシステムを再始動することができます（本番環境では慎重に扱ってください）。
- ログやデータファイル（data/*.db, .env）は絶対にバージョン管理にコミットしないでください（config_setup でも注意書きあり）。

貢献
----
バグ報告や改善提案は issue を立ててください。ユニットテスト・ドキュメントの追加歓迎です。

ライセンス
--------
リポジトリに従う（LICENSE ファイルがある場合はそちらを参照してください）。

---

この README はコードベースから抽出した主要な運用・開発情報をまとめたものです。追加で「起動フロー図」や「設定例 .env サンプル」、「ディテールな API ドキュメント」が必要であれば作成します。どの情報を優先して追加しますか？