CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
-----
- 基本アプリケーションパッケージを初期実装として追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はリポジトリ直下 data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）と MockBroker を利用し、本番 DB と分離。
    - 実行中は data/execution.pid を PID ファイルとして利用。停止は data/stop_requested.flag を検知して安全に停止。
- 設定管理・環境変数
  - config.py: Settings クラスを実装。環境変数から各種設定を取得するユーティリティを提供。
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等をサポート。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - 環境自動ロード機能: プロジェクトルート (.git または pyproject.toml) を探索して .env/.env.local を自動読み込みする仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - 環境判定プロパティ: is_live, is_paper, is_dev を提供。
- 設定関連 CLI/ツール
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - デフォルト項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に設定して .env に保存可能。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML 必須）等を実施。
    - --strict オプションで警告を失敗扱い（exit 1）にできる。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数または引数で設定を上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS に対応し、psutil の AccessDenied 等の例外を安全にハンドル。
    - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(N) を提供。
- モニタリング/監査 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db（参照実装の呼び出し箇所が起動スクリプトに統合）。
- Execution / 発注関連（実装の主要コンポーネント）
  - execution モジュールの主要コンポーネントを組み立てるコードを run_execution に追加（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager を組み合わせて起動する）。
  - RiskConfig によるリスク制御初期値設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() から初期化される。
- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py: 候補選定および重み計算（等比・スコア比重）を実装。
  - portfolio/risk_adjustment.py: セクターキャップ適用、レジーム乗数計算（bull/neutral/bear のマッピング）を実装。unknown セクター扱いルール等を明記。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮したスケールダウンロジックを実装。
    - スケールダウン時の端数配分アルゴリズムを実装し再現性を確保。
- リサーチ（ファクター計算）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity に関する設計と一部実装を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。モメンタム計算関連定数と calc_momentum の冒頭処理を含む（実装途中）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH / --db オプションで指定した SQLite を読み、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ指定（--from/--to）をサポート。
- ドキュメント的な記載（各モジュールに詳細な docstring を追加）。

Changed
-------
- なし（初期リリース）

Fixed
-----
- なし（初期リリース）

Security
--------
- なし（初期リリース）

Notes / Breaking changes / Migration
-----------------------------------
- Monitoring は「環境にかかわらず」設定された production sqlite_path を使用する実装になっています。意図的な分離が必要な場合は注意してください。
- Paper trading（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データベースと完全に分離します。テスト/検証を行う場合はこの挙動を活用してください。
- 環境変数自動ロード機能により .env/.env.local がプロジェクトルートから読み込まれます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- logging_setup は標準出力（stdout）を採用しています。systemd/cron 等で標準出力を扱う運用に合わせた設計です。

Acknowledgements
----------------
- この変更履歴はソースコードの内容から推測して作成しています。実際のリリースノート作成時はリリース担当者による確認・追記を推奨します。