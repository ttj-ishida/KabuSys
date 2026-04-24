KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。
主な機能は以下の通りです:

- 実行エンジン（ExecutionEngine）: ブローカーと連携して発注・注文管理を行う（paper_trading モードあり）
- 監視（Monitoring）: システム状態・注文状況・リスクを定期的にチェックしてログ／アラート／Kill Switch を制御
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイジング、セクターキャップ等の純粋関数実装
- リサーチ/ファクター計算: DuckDB 上の価格・財務データからファクターを計算
- AI モジュール: ニュースを LLM によるセンチメント評価（OpenAI）でスコアリングし、レジーム判定に利用
- 付帯ツール: .env ウィザード、設定検証、Paper Trading の検証レポート生成 等

主な特徴
--------
- 環境変数/.env ベースの設定管理（config.py）
- 実稼働（live）とペーパートレード（paper_trading）を明確に分離（paper_trading は専用 SQLite DB を使用）
- DuckDB を用いたリサーチ向け高速分析（prices_daily / raw_financials 等のテーブル想定）
- OpenAI を用いたニュース NLP（gpt-4o-mini 想定）と市場レジーム判定
- ログはコンソール（stdout）＋日次ローテートファイルへ出力（logs/<app_name>.log）
- Kill Switch（data/kill.flag）により外部からエンジン停止を要求可能

セットアップ
-----------

1. Python と依存ライブラリ
   - Python 3.9+ を想定しています（プロジェクトのポリシーに合わせて調整してください）。
   - 必要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合に必要）
   - 例: pip install duckdb psutil openai PyYAML

2. リポジトリ配置
   - この README はパッケージ配下 src/kabusys を前提にしています。パッケージルートが .git または pyproject.toml によって検出される仕組みです。

3. 環境変数設定（.env）
   - プロジェクトルートに .env を作成します。.env には以下のようなキーが含まれます（必要に応じて上書き可）。
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/…、デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合に必要）
   - 対話式ウィザードで作成する:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成・更新し、シークレット項目はマスク表示されます。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------

- 実行エンジン（ExecutionEngine）起動
  - 本番/開発両方で同一スクリプトを使用。KABUSYS_ENV によって挙動が異なります。
  - 起動:
    - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db にトレード履歴を記録します（本番 DB とは完全分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せずに終了します（停止フラグ）。
    - エンジンは実行中に data/stop_requested.flag を検知すると安全に停止します。
    - 実行時に pid ファイル（デフォルト data/execution.pid）を扱います。

- 監視プロセス（Monitoring）起動
  - 起動:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（ポーリング間隔・秒、デフォルト 60）
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を用いて定期チェックを行い、必要に応じて data/kill.flag を書き込みます（ExecutionEngine 側で検知して停止）。
    - 監視は monitoring DB（設定に従い sqlite_path）へログを書きます。監視は KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用します。

- .env 関連ツール
  - 設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - レポート生成:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト data/paper_trading.db）。
  - レポートでは稼働率・注文成功率・送信率・レイテンシ（P95）などを評価し、PASS/FAIL を出力します。

- AI 関連機能
  - ニュース NLP（センチメントスコア付与）:
    - kabusys.ai.news_nlp.score_news を呼ぶことで ai_scores テーブルへ書き込みます。
    - OpenAI API キーを OPENAI_API_KEY 環境変数に設定するか、関数引数で渡してください。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を使って market_regime テーブルへ冪等書き込みします。
  - 注意:
    - OpenAI 呼び出しはレート制限や 5xx などに対してリトライ処理を実装していますが、API キーや利用ポリシーには十分ご注意ください。

設定項目の主な環境変数
--------------------
（主要なものを抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略可）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading モード）
- LOG_LEVEL — ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒）

ディレクトリ構成（概要）
----------------------
src/kabusys 以下の主なファイル・モジュール:

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数/.env の読み込み・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- __init__.py — パッケージ定義

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM スコアリングロジック
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — 監視用 SQLite のスキーマと永続層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文関連の監視）※実装ファイルあり（省略）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - kill_switch.py — data/kill.flag の書き込みロジック
  - alert_manager.py — （アラート送信管理）※実装ファイルあり（省略）
- execution/
  - execution_engine.py — 実際の ExecutionEngine（起動・セッション管理）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・探索
- monitoring/ （上記）
- tools/
  - paper_verification_report.py — Paper Trading レポート
- utils/
  - logging_setup.py — ログの一元設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

ログとデータファイル（デフォルト）
--------------------------------
- logs/<app_name>.log — 日次ローテートされるログ（setup_logging により生成）
- data/monitoring.db — 監視用 SQLite（デフォルト）
- data/paper_trading.db — ペーパートレード用 SQLite（paper_trading モード）
- data/kabusys.duckdb — DuckDB（デフォルト）
- data/execution.pid — ExecutionEngine の PID（実行時）
- data/stop_requested.flag — 起動/実行プロセスが停止フラグとしてチェックするファイル
- data/kill.flag — Kill Switch が書き込む停止理由ファイル

注意事項 / 運用上のヒント
------------------------
- .env は機密情報を含むため絶対に Git 等へコミットしないでください。
- KABUSYS_ENV=live のときは特に注意（validate_config で警告を表示するチェックあり）。
- Monitoring は基本的に本番用 sqlite_path を使用するように設計されています（KABUSYS_ENV に依存せず監視 DB を参照）。
- OpenAI の利用はコスト・レート制限に注意して運用してください。
- プロセス優先度や CPU affinity の設定は OS 権限（root や管理者権限）に依存する場合があります。失敗しても警告でスキップされます。

さらに詳しく
------------
各モジュールの docstring や関数コメントに設計方針やアルゴリズムの説明があります。特定の機能を拡張・検証する際は該当ファイルを参照してください。

問題・バグ報告
--------------
README にない点や不整合があれば、該当モジュールの docstring を確認のうえ報告してください。

以上。