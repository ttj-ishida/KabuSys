README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の軽量実装です。
主な機能は市場データ集計（DuckDB）、発注実行（kabuステーション API またはモック）、監視・アラート、ポートフォリオ構築ユーティリティ、AI ベースのニュース/レジーム判定、および各種運用ユーティリティです。

設計方針の要点
- 環境変数 / .env による設定管理（config.py）
- 実行エンジン（ExecutionEngine）と監視プロセス（MonitoringEngine）を分離
- Paper Trading 用に本番 DB と分離された専用 SQLite を利用可能
- DuckDB を分析用 DB として利用（prices_daily, raw_financials などを想定）
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定をサポート（API キー必要）
- フラグファイル（data/kill.flag, data/stop_requested.flag）でプロセス制御

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db を使用
  - プロセス優先度設定、PID ファイル管理、停止フラグ検知などを備える
- 監視起動スクリプト: run_monitoring.py
  - SystemMonitor 等をポーリングし監視ログ（SQLite）へ保存
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
- 設定ウィザード: config_setup.py（対話式で .env を生成/更新）
- 設定検証 CLI: validate_config.py（.env と config/*.yaml の簡易検証、--strict オプション有）
- Paper Trading レポート生成: tools/paper_verification_report.py
  - Paper Trading SQLite から稼働率・注文成功率・レイテンシなどを集計し PASS/FAIL 判定
- ポートフォリオ構築ライブラリ: kabusys.portfolio（候補選定、重み算出、ポジションサイズ決定、セクター制限など）
- リサーチ機能: kabusys.research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 関連: kabusys.ai（news_nlp、regime_detector）— OpenAI を利用したニュースセンチメント・市場レジーム判定
- 監視関連: kabusys.monitoring（monitoring_db、system_monitor、trade_monitor、risk_monitor、kill_switch、alert_manager 等）
- ユーティリティ: ログ設定（utils.logging_setup）、プロセス優先度設定（utils.process_priority）など

セットアップ手順
----------------
1. リポジトリをクローン
   - プロジェクトルート配下に src/ を置くレイアウトを想定しています（このコードベースは src/kabusys 配下に配置されています）。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合は .venv\Scripts\activate）

3. 依存パッケージのインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証用。ただし未インストールでも動作するが警告が出ます）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt がないため、環境に応じて追加パッケージが必要になる場合があります。

4. .env の準備
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境（必須ではないが重要）
     - KABUSYS_ENV: development | paper_trading | live
   - その他:
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB: data/paper_trading.db）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 環境変数例（ペーパートレードで起動する場合）
    - export KABUSYS_ENV=paper_trading
    - export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - stop: data/stop_requested.flag（存在を検知すると安全に停止します）
  - PID ファイル: data/execution.pid

- 監視を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - 監視停止: data/stop_requested.flag を作成するとループが終了します

- .env の作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）になります

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

運用上の注意
-------------
- 監視 / 実行プロセスは data/stop_requested.flag により停止できます。また、Kill Switch（kill.flag）はリスク条件が発生したときに ExecutionEngine 側で読まれ、発注を止めるトリガーになります。
- 監視ロジックは環境にかかわらず Settings.sqlite_path（監視 DB）を使用します。ExecutionEngine は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使います（本番 DB と分離）。
- ログはデフォルト logs/ ディレクトリに出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- OpenAI を利用する機能（news_nlp, regime_detector）を有効にするには OPENAI_API_KEY を設定してください。API 呼び出しは冪等処理・リトライやフォールバックを備えていますが、API 利用量に注意してください。
- フェイルセーフ: 設定不足や一部の API エラー時にはフォールバック動作（例: macro_sentiment=0.0）を行い、致命的な例外の伝播を避ける設計になっています。

主な設定（環境変数）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能で必要）
- MONITOR_POLL_INTERVAL（監視のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1、production では 0 推奨）

ディレクトリ構成（主要ファイル）
----------------------------
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

- src/kabusys/execution/
  - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
  - broker_factory.py        — ブローカークライアントの生成（実ブローカ／モック）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- src/kabusys/monitoring/
  - monitoring_db.py         — SQLite 永続化層・スキーマ初期化
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py              — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py       — ETF MA + マクロニュースで市場レジームを判定

- src/kabusys/tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成

- src/kabusys/utils/
  - logging_setup.py         — ログ初期化ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

データ・ログ出力（デフォルト）
------------------------------
- データベース:
  - data/kabusys.duckdb         （DuckDB：分析用）
  - data/monitoring.db          （SQLite：監視ログ）
  - data/paper_trading.db       （Paper Trading 用 SQLite、paper_trading 環境で使用）
- ログ:
  - logs/<app_name>.log
- 制御フラグ / PID:
  - data/stop_requested.flag
  - data/kill.flag
  - data/execution.pid

開発・拡張メモ
----------------
- DuckDB を分析 DB として使用する前提で SQL と Python を組み合わせた処理が多く実装されています（research / ai）。
- AI 呼び出しは OpenAI SDK（新しい v1 SDK を想定）を利用しています。テスト時は内部の _call_openai_api をモックすると良いです。
- monitoring_db.init_monitoring_db はスキーマのマイグレーション処理（後方互換）を含みます。
- ポートフォリオ計算やポジションサイズ決定ロジックは純粋関数（副作用なし）で設計されているため、単体テストが容易です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- 本リポジトリのライセンス表記は該当ファイルをご確認ください（ここには含まれていません）。

お問い合わせ / 貢献
------------------
- バグ報告や機能提案は Issue を通してください。プルリクエスト歓迎です。
- 変更を加える場合は既存の設定検証スクリプト（validate_config）やテストで動作を確認してください。

以上。開発や運用で必要なコマンドや設定の補足があれば追記します。