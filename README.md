README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。本コードベースは以下の主要機能を含みます。

- マーケットデータ（DuckDB）を使ったファクタ計算・研究ツール
- 発注エンジン（ExecutionEngine）と注文管理（リスク管理・再整合）
- 監視サブシステム（System / Trade / Risk のポーリングとアラート / Kill Switch）
- Paper Trading（モックブローカー）用の分離された履歴 DB と検証レポート生成
- ニュースの NLP によるセンチメントスコアリング / レジーム判定（OpenAI 使用）
- 環境設定ウィザード・設定検証ツール

特徴
----
- .env ベースの環境設定（config_setup による対話式生成）
- KABUSYS_ENV による実行モード切替（development / paper_trading / live）
- paper_trading は本番 DB と分離された SQLite（data/paper_trading.db）を使用
- 監視は専用の SQLite（data/monitoring.db）に永続化され、stop/kill フラグで制御可能
- DuckDB を分析用ストアとして採用（prices_daily, raw_financials 等を想定）
- OpenAI（gpt-4o-mini）を用いたニュース解析・レジーム判定（API キー必須）
- psutil によるプロセス優先度 / CPU affinity 設定ユーティリティを内蔵

必要な依存パッケージ（代表例）
-----------------------------
実行に必要な主要パッケージ（環境によって追加が必要になることがあります）:

- python >= 3.10（型ヒントに union | を使用）
- duckdb
- psutil
- openai
- （任意）PyYAML - config/*.yaml の内容検証を行う場合

インストール例（仮）
pip install duckdb psutil openai
# 任意: pip install pyyaml

セットアップ手順
--------------
1. リポジトリをクローン／展開する。
2. Python 仮想環境を作成して依存パッケージをインストールする（上記参照）。
3. 初期 .env を生成する（対話式ウィザード）:
   python -m kabusys.config_setup
   - ウィザードは .env を作成します（デフォルトはプロジェクトルートの .env）。
4. 設定を検証する:
   python -m kabusys.validate_config
   - 必須環境変数や DB パス、YAML の有無等を検証します。
   - --strict を付けると警告も失敗扱いになります。
5. データディレクトリを準備（必要に応じて）:
   - デフォルトの DB 等は data/ 配下に置かれます（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。
   - ログは logs/ に出力されます（logging_setup が自動作成します）。

環境変数（主要）
----------------
主な環境変数とデフォルト値・意味:

- KABUSYS_ENV (development | paper_trading | live) — 実行モード（デフォルト: development）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定動作（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API を使う機能で参照されるキー
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0 推奨）

主要スクリプト・使い方
--------------------

- 環境設定ウィザード（.env を作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  # --strict を付けると警告も失敗扱い（exit 1）になる

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は環境に関わらず本番 sqlite_path を使用して監視ログを永続化します
  - 停止はプロジェクトルート/data/stop_requested.flag にファイルを置くことで行えます

- ExecutionEngine 起動（発注エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は data/execution.pid に PID を書きます。停止は stop_requested.flag を作成するか Engine.stop() による制御を行います
  - KILL スイッチ（data/kill.flag）により外部から停止要求を出すことも可能

- Paper Trading 検証レポート（標準出力へ）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - 稼働率・注文成功率・レイテンシなどを集計して PASS/FAIL を判定します

- AI / ニューススコアリング（プログラム的に呼び出す）
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI キーは api_key 引数か環境変数 OPENAI_API_KEY で指定
  - DuckDB 接続（duckdb.connect(...)）を渡して実行します
  - 例（簡易）:
    python -c "import duckdb, datetime; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key='YOUR_KEY'))"

- レジーム判定（ai.regime_detector.score_regime）
  - 同様に DuckDB 接続と API キーを渡して呼び出します

補助ユーティリティ
-----------------
- kabusys.utils.logging_setup.setup_logging(...) — 統一的なログ設定（コンソール + 日次ローテートファイル）
- kabusys.utils.process_priority.set_process_priority(level) — プロセス優先度設定（high/normal/low）
- config.Settings — 環境変数からアプリ設定を取得するヘルパークラス（コード内で広く利用）

ディレクトリ構成（主要ファイル）
-----------------------------
以下はソースツリー内の主要ファイル・モジュールの抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                    — Settings / .env 自動ロード
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py         — 市場レジーム判定（MA + マクロ NLP 合成）
  - monitoring/
    - monitoring_db.py           — SQLite モデル（テーブル作成／読み書き）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py           — （コード中に参照あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py           — （コード中に参照あり）
  - execution/
    - execution_engine.py        — ExecutionEngine 本体（参照あり）
    - broker_factory.py
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
  - data/
    - pipeline.py                — データパイプラインのヘルパー（get_last_price_date などを参照）
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/                   — 監視関連 DB/ロジック（上記）

永続データ / フラグファイル
---------------------------
- data/kabusys.duckdb           — DuckDB（分析データ）
- data/monitoring.db            — 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db         — paper_trading 用 SQLite（発注履歴など）
- data/kill.flag                — Kill Switch（Execution 停止を要求するフラグ）
- data/stop_requested.flag      — 実行管理用停止フラグ（run_* スクリプトが監視する）
- data/execution.pid            — 実行中の ExecutionEngine の PID（run_execution が書き込み）

注意事項 / 運用上のガイド
-----------------------
- 本番運用時（KABUSYS_ENV=live）は特に注意が必要です。validate_config は live の場合に追加警告を出します。
- Paper Trading は本番 DB と分離されていますが、設定ミスにより本番 DB を上書きしないよう .env を慎重に管理してください。
- OpenAI を利用する処理はコストが発生します。API キーの権限・利用状況に注意してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨されません（安全上のリスク）。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。ログ権限に注意してください。
- process priority / cpu affinity の設定は環境に依存し、権限不足で設定失敗する可能性があります。失敗時は警告のみ出ます。

開発者向け
---------
- ユニットテストは各純粋関数（portfolio/*, research/*）を中心に実装しやすい設計です（DB 参照なしの関数が多い）。
- DB を必要とする処理は DuckDB / SQLite 接続を引数で受け取るため、テスト時はインメモリ DB を渡すと良いです。
- OpenAI 呼び出しは内部関数を patch してモック化可能なように設計されています（_call_openai_api をモック）。

以上が本リポジトリの主要な概要・セットアップ・運用ガイドです。必要な箇所のサンプルや追加の CLI を希望される場合は、利用シナリオに合わせた README の拡張（例: systemd ユニットファイル例、Docker 化手順、CI 用テストスクリプト）を作成しますのでご相談ください。