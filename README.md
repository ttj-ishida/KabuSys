README — KabuSys（日本株自動売買システム）
================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のサンプル実装です。
主な目的は以下を含みます:
- 発注エンジン（ExecutionEngine）と監視（Monitoring）を分離して稼働
- ペーパートレード（Mock）による検証と本番運用の分離
- DuckDB を用いたリサーチ / ファクター計算
- OpenAI を利用したニュース NLP によるセンチメント評価
- 監視ログ（SQLite）による稼働性・注文ログ・リスクログの永続化

重要な設計ポイント:
- .env / 環境変数で構成を管理。Settings クラスで統一的に参照。
- ペーパートレード時は DB を完全分離（data/paper_trading.db）。
- 監視は環境にかかわらず本番用 sqlite_path（監視 DB）を使用する設計。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード DB に記録
- Monitoring 起動スクリプト（run_monitoring.py）
  - システム状態・データ鮮度・注文状態・リスク監視を定期ポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）
- 環境設定ウィザード（config_setup.py）で .env 初期生成・更新を対話式で支援
- 設定検証 CLI（validate_config.py）で .env と config/*.yaml の前提チェック
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- ポートフォリオ構築（選定・重みづけ・単元丸め・セクター制限 等）
- リサーチ: ファクター計算（momentum/value/volatility）、特徴量解析（IC 等）
- AI モジュール: ニュース NLP（news_nlp）、市場レジーム判定（regime_detector）
- ロギング・プロセス優先度設定・プロセス制御ユーティリティ群

前提条件
--------
- Python 3.9+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML (validate_config の YAML 検査で使用)
- (任意) 仮想環境を推奨

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトで requirements.txt がある場合は pip install -r requirements.txt）

4. 初期ディレクトリ作成（data, logs 等）
   - mkdir -p data logs

5. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考に）

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD       — kabuステーション API パスワード

運用 / ログ / DB 周り
- KABUSYS_ENV             — 実行環境（development / paper_trading / live）
- DUCKDB_PATH             — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             — 監視 SQLite（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL               — ログレベル
- LOG_DIR                 — ログ保存ディレクトリ（デフォルト: logs）

AI / 外部 API
- OPENAI_API_KEY          — OpenAI API キー（news_nlp / regime_detector で使用）
- PAPER_FILL_MODE         — ペーパートレードの約定挙動（instant/partial/never/reject）

監視 / フラグ
- PID_FILE_PATH           — ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH          — Kill Switch フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

実行方法
--------
※ すべてパッケージモードで実行できます（カレントディレクトリはプロジェクトルート）。

- ExecutionEngine 起動（実行/ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定するとペーパートレード用の MockBroker を使い data/paper_trading.db に記録

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定可能（例: export MONITOR_POLL_INTERVAL=30）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ログ・データファイル
--------------------
- ログ: logs/<app_name>.log（日次ローテーション、30日保持）
  - 例: logs/execution.log, logs/monitoring.log
- 監視 DB (SQLite): デフォルト data/monitoring.db
- DuckDB: デフォルト data/kabusys.duckdb
- ペーパートレード DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- Kill / Stop フラグ:
  - data/kill.flag — Kill Switch のトリガーファイル（監視が条件を満たすと書き込む）
  - data/stop_requested.flag — run_monitoring/run_execution の外部停止用フラグ（存在するとループを終了）

注意点
-------
- 監視（Monitoring）は「監視 DB」として SQLITE_PATH に指定した DB を使用します。run_monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を参照する実装になっています。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して DB を完全に分離します。
- OpenAI 等外部 API を利用する機能を有効にする場合は適切に API キーを設定してください。API 呼び出しはリトライ・エラーハンドリングを備えていますが、コスト管理には注意してください。
- .env は決して Git 等にコミットしないでください（config_setup でも注意喚起あり）。

ディレクトリ構成（抜粋）
-----------------------
以下は主要なファイル/ディレクトリの構成（src/kabusys 配下を想定）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
  - data/                    — runtime: data ファイル（DB, PID, flag 等）
  - logs/                    — runtime: ログ出力先（デフォルト）

開発・拡張メモ
--------------
- DuckDB を用いたリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データ取り込みパイプラインは kabusys.data.pipeline 等に実装される想定です（本 README の抜粋コードでは一部参照のみ）。
- AI モジュール（news_nlp / regime_detector）は OpenAI API を呼び出します。ユニットテストでは API 呼び出しをモックすることを推奨します（モジュール内での注釈あり）。
- ロギングは全アプリケーションで統一して setup_logging を呼ぶ設計です。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

お問い合わせ / 参考
-------------------
- 各モジュールのドキュメントはソース内 docstring に詳細な設計・注意点が記載されています。まずは該当モジュールの docstring を参照してください。
- .env の雛形や config/*.yaml の生成スクリプトがプロジェクトに含まれている場合、それらを利用して初期設定を行ってください。

以上。ご不明点があれば、どの機能（例: Execution 起動、monitoring の挙動、AI モジュール、DB スキーマ）についてさらに詳しくドキュメント化するか教えてください。