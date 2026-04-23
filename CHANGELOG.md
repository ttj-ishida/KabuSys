# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証ツール群を追加。

### Added
- パッケージ基盤
  - バージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開用の __all__ を定義。

- 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数経由で設定を取得・検証するプロパティ群を提供。
    - DBパス（DUCKDB_PATH, SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、KABUSYS_ENV、LOG_LEVEL、各種閾値やフラグなどをプロパティ化。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の有効値検証）。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 読み込み順序: OS 環境 > .env.local > .env。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 高度な .env パーサーを実装:
    - export プレフィックス、クォート文字列（エスケープ対応）、インラインコメントの扱い、上書き制御（protected set）等に対応。

- 環境設定/検証 CLI
  - config_setup（kabusys.config_setup）: 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - 各項目の説明、シークレットのマスク表示、既存値の再利用、.env 書き込み。
  - validate_config（kabusys.validate_config）: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config YAML の存在/パース検証（PyYAML があれば内容検査）。
    - --strict オプションで警告も失敗として扱う。

- 起動スクリプト
  - run_execution（kabusys.run_execution）を追加:
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClient の生成、各コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立て、PID/停止フラグ処理、スレッドでのエンジン実行を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) 検知時に安全に停止。
  - run_monitoring（kabusys.run_monitoring）を追加:
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグによるループ終了ハンドリングと例外のログ出力。

- ロギング / プロセス制御ユーティリティ
  - logging_setup（kabusys.utils.logging_setup）を追加:
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority（kabusys.utils.process_priority）を追加:
    - Windows/Linux/Mac を抽象化してプロセス優先度（"high"|"normal"|"low"）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足などの例外は警告ログでスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補の除外を行うロジック。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じて発注株数を計算。単元株丸め、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、端数配分の再配分ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report を追加:
    - Paper Trading の検証レポート生成ツール。SQLite（PAPER_TRADING_SQLITE_PATH）からデータ取得して稼働率、注文成功率、送信率、P95レイテンシ等を算出し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db をサポート。デフォルト閾値やフォーマット済み出力あり。

- 研究モジュール
  - research.factor_research を追加（ファクター計算基盤）。
    - Momentum / Value / Volatility / Liquidity を想定した設計とモメンタム計算（calc_momentum）の実装方針・定数を配置。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### Changed
- なし（初回リリースのため既存変更はなし）。

### Fixed
- なし（初回リリースのため既存不具合修正はなし）。

### Breaking Changes
- なし（初回リリース）。

---

注記:
- 多くのモジュールは「外部資源（DB、ブローカーAPI、設定ファイル等）」に依存します。実行前に validate_config や config_setup を使用して環境を整備してください。
- ログやデータファイルのデフォルトパスはプロジェクト内の data/ や logs/ を参照します。デプロイ先での適切なパーミッション・パスの確認を推奨します。