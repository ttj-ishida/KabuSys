CHANGELOG
=========

すべての変更は Keep a Changelog の仕様に従って記載しています。  
日付は本リリースを推定した日付です（ソースコードから推測）。

フォーマット:
- Unreleased: 現在開発中/未リリースの変更
- バージョンごとに「Added / Changed / Fixed / Deprecated / Removed / Security」を列挙

Unreleased
----------
- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコア機能を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 実行用スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用の MockBrokerClient を使用し、paper_trading 環境では専用 SQLite (data/paper_trading.db) に記録することで本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) と実行 PID 管理 (data/execution.pid) に対応。
    - スレッドでエンジンを起動し、停止フラグ検出時に安全に停止させる処理を実装。
    - RiskManager と Reconciler、OrderManager、OrderRepository 等の組み立てロジックを追加。RiskConfig の既定パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, など）を定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - ポーリング中の例外はログ出力して次サイクルへ継続。
- 設定管理:
  - config.py: 環境変数/.env を扱う Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種環境変数アクセス用プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, しきい値等）を実装。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH のデフォルトを提供。
- 設定ユーティリティ:
  - config_setup.py: .env の対話式ウィザードを追加。主要設定項目の質問と .env への書き込みをサポート（秘密項目はマスク表示、既存 .env からの読み込み）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番向けガードなどを実装。--strict モードで警告を FAIL 扱いにできる。
- ロギング / 運用ユーティリティ:
  - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。LOG_DIR / LOG_LEVEL / app_name 引数で挙動を制御。既存ハンドラのクリアやファイルハンドラ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux, macOS, FreeBSD）を吸収する実装。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足等は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群、DB 未参照）:
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソート（同点時は signal_rank の昇順でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションのセクター比率が閾値を超える場合、当該セクターの新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数決定ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。lot_size（単元）や cost_buffer（スリッページ・手数料見積り）を考慮した aggregate cap のスケーリング、端数処理の再配分ロジックを実装。
- 監視・検証ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を読み、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。閾値はソース内定義（例: uptime >= 99%、fill_rate >= 90%、P95 レイテンシ <= 200ms）。
- 研究モジュール雛形:
  - research/factor_research.py: DuckDB を参照してファクター（Momentum / Value / Volatility / Liquidity）を計算するためのモジュール骨格を追加（モーメンタム等の定義・定数を含む）。設計方針として DuckDB の prices_daily/raw_financials を利用し、外部 API に依存しない形を想定。
- DB 初期化:
  - monitoring_db 初期化呼び出し（init_monitoring_db）を run_monitoring と run_execution の起動時に行い、監視テーブルが存在することを保証（冪等）。

Changed
- 設計上の決定:
  - 監視 (SystemMonitor) は KABUSYS_ENV に依存せず本番 sqlite_path（監視 DB）を使用する設計とした。（意図的に監視データは本番 DB に統合）
  - ログは stdout を基準に出力しつつ、ファイル出力は logs/<app>.log に日次ローテーション（30世代）で保存。ファイル作成に失敗してもコンソール出力は維持。
  - .env の自動ロード順序は OS 環境 > .env.local > .env。プロジェクトルートが特定できない場合は自動ロードをスキップする安全設計。
- validate_config:
  - PyYAML がインストールされていない環境でもスクリプトが稼働するよう、YAML 検証は利用可能な場合のみ行い、未インストール時は警告でスキップする。
- process_priority:
  - プラットフォーム差分を吸収する実装により、呼び出し側は OS を意識せず set_process_priority を呼べるようにした。権限不足時は警告ログで安全にスキップ。

Fixed
- なし（初回リリースのため明示的な修正履歴はなし）

Deprecated
- なし

Removed
- なし

Security
- なし（セキュリティ向上のため、.env は絶対に Git にコミットしない旨を config_setup のヘッダに明示）

注記（開発者向け）
- 多くのモジュールは副作用を持たない純粋関数（portfolio 等）として実装されており、ユニットテストの作成が容易です。
- run_execution/run_monitoring は外部リソース（SQLite, DuckDB, ブローカー API）にアクセスするため、ローカル開発時は環境変数で PAPER_TRADING_SQLITE_PATH や PAPER_FILL_MODE 等を設定して paper_trading モードを利用することを推奨します。
- research/factor_research.py は途中まで実装の痕跡があり、モーメンタム計算等の実装継続が必要（ファイル末尾が途中で切れているため、実装の完了を検討してください）。

以上。