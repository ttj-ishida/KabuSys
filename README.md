KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買・検証・監視を行うためのモジュール群です。  
本リポジトリには以下の主要機能が含まれます。

- 発注エンジン（ExecutionEngine）の起動・制御（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）とキルスイッチによる安全停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 支援モジュール（ニュース NLP によるセンチメント、レジーム検出）
- 運用支援ツール（環境設定ウィザード、設定検証、Paper Trading 検証レポート）
- ログ／DB 経由の永続化（SQLite / DuckDB）

主な特徴
---------
- 環境（development / paper_trading / live）に応じた挙動切替
  - paper_trading では MockBrokerClient を用い、実 DB と分離して data/paper_trading.db を利用
- 監視（MonitoringEngine）によりシステム状態・注文・リスクを定期チェック
- Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止
- OpenAI を用いたニュースセンチメント（ai.news_nlp）・レジーム判定（ai.regime_detector）
- DuckDB を分析用データベースとして利用（prices_daily / raw_financials 等を想定）
- ロギングは統一的に setup_logging を利用（コンソール + 日次ローテートファイル）

動作前提 / 依存
---------------
- Python 3.10 以上（| 型注釈や match を用いないが、Path | None 等を使用しているため）
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定 YAML の検証を行いたい場合）
- 標準ライブラリ：sqlite3, logging, threading, argparse など

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... ; cd <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに配置）。主な env キー:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI 利用時に必要
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START 等

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

使い方（起動・運用）
--------------------

起動スクリプト（モジュール実行形式）
- ExecutionEngine（注文エンジン）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合: MockBrokerClient を利用し data/paper_trading.db を使用（本番 DB から分離）
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 停止は kill.flag（デフォルト: data/kill.flag）や stop_requested.flag による監視で行われる
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings.sqlite_path（デフォルト data/monitoring.db）を常に使う（環境に依らず本番用 path を使用）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 停止フラグ: src/ 配下から project root の data/stop_requested.flag を監視し、存在時にループを終了

その他ユーティリティ
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB 指定可

AI 機能（OpenAI）
- ニュース NLP（センチメント）: kabusys.ai.score_news（内部的には news_nlp.score_news）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）
  - 大量 API 呼び出しはリトライ・バッチ処理を行う実装
- レジーム判定: kabusys.ai.regime_detector.score_regime
  - 同様に OPENAI_API_KEY が必要
- 注意: API 利用時はコストやレート制限、API キーの取り扱いに注意してください

監視・停止フラグ等（運用に重要）
- data/kill.flag
  - KillSwitch が条件を満たすとここに理由を書き込み、ExecutionEngine 停止を促す
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定に応じて kill.flag をクリアする挙動が設定可能
- data/stop_requested.flag
  - run_monitoring / run_execution の起動スクリプトが存在確認しループ停止やエンジン停止を行うための外部停止フラグ
- data/execution.pid
  - ExecutionEngine が PID を記録するファイル（Settings.pid_file_path）

ロギング
- 共通関数 setup_logging により:
  - コンソール（stdout）出力
  - 日次ローテートしたログファイル: logs/<app_name>.log（デフォルト logs/、30世代保持）
- 環境変数 LOG_DIR / LOG_LEVEL で挙動を上書き可能

プログラム的な利用例（ライブラリとして）
- 研究系 API（例）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
  - duckdb_conn = duckdb.connect("data/kabusys.duckdb"); calc_momentum(duckdb_conn, date(2026,4,1))
- ポートフォリオ関数
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

ディレクトリ構成（抜粋）
----------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数と .env 自動読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite のテーブル初期化・ラッパー
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（ファイル参照など）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知ロジック: LINE 等）※コード参照
  - execution/
    - execution_engine.py    — 実際の発注エンジン（EngineConfig 等）
    - broker_factory.py      — BrokerClient の生成（本番 / mock 切替）
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
    - __init__.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - data/                    — 実行時に生成される SQLite / pid / flag / duckdb 等の格納先（デフォルト）

補足 / 運用上の注意
------------------
- 本番（KABUSYS_ENV=live）での起動前に必ず validate_config を実行して設定を確認してください。
- .env は秘密情報（API トークン等）を含むため Git 等にコミットしないでください。
- OpenAI 等の外部 API を使う処理は失敗に強い作りになっていますが、API 呼び出しコスト・制限に注意してください。
- monitoring はデフォルトで本番用 sqlite_path を参照する（run_monitoring では KABUSYS_ENV に関わらず設定された sqlite_path を使用する点に注意）。
- run_execution は paper_trading 環境のとき DB を分離（paper_sqlite_path）するため、本番データを直接汚さない構成です。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

最後に
------
この README はコードベースから読み取れる設計・使い方の要点をまとめたものです。実運用時は設定ファイル（config/*.yaml が存在する場合）や各モジュールのログ・ドキュメントを参照し、十分なテストを行ってください。追加の詳細（API の挙動、BrokerClient 実装等）は該当モジュールのドキュメントやコード内コメントを参照してください。