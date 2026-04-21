# Changelog

すべての重要な変更履歴をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）に分類します。
- バージョンと日付を付記します。

なお、本履歴はリポジトリ内のソースコードから推測して作成したもので、実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-21
初回リリース相当。自動売買システム KabuSys の基礎機能を実装。

### Added
- パッケージ基本情報
  - kabusys パッケージ初版を追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。

- 起動スクリプト / エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用の SQLite パス（Settings.sqlite_path）を使用。
    - data/stop_requested.flag によりループを安全に終了可能。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBroker を利用する想定。
    - エンジン実行中の PID 管理（data/execution.pid）および停止フラグ監視を実装。
    - 各種コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てて実行。
  - config_setup.py: .env を対話式に作成/更新するウィザード CLI を追加。
    - J-Quants / kabu API / DB パス / LINE 設定などの主要設定項目を対話で入力。
    - .env 書き出しは安全注意を含むテンプレートで出力。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB/ファイルパスの親ディレクトリ存在確認、config/*.yaml の存在＆パース（PyYAML 利用可能時）などをチェック。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定する。
    - P95 レイテンシ計算、閾値による判定ルールを実装。
  - tools パッケージ（空の __init__ を含む）を追加。

- コンフィグ / 設定管理
  - config.py:
    - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。
    - .env 自動ロード機能を実装（.env を読み込み、.env.local で上書き、OS 環境変数を保護）。
    - .env のパースはコメント、export、シングル/ダブルクォート、バックスラッシュエスケープなどに対応。
    - Settings クラスを追加し、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値、env/log_level 判定など）を提供。入力値の妥当性検証を実施。
    - settings = Settings() の単一インスタンスを提供。

- ポートフォリオ構築・リスク計算
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアで上位 N を選出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補除外ロジックを実装。既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外（unknown セクターは適用外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数計算ロジックを実装。以下をサポート：
      - allocation_method: "risk_based", "equal", "score"
      - 単元株（lot_size）への丸め、max_position_pct による個別上限、max_utilization による利用上限
      - cost_buffer を考慮した保守的コスト見積り、投下資金が available_cash を超えた場合のスケーリングと残余割当ロジック
      - ログ出力によるデバッグ情報
  - portfolio パッケージ __init__ で主要 API をエクスポート。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name 引数による柔軟な設定、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加。Windows（psutil の priority constants を使用）と POSIX (nice 値) を吸収し、例外時は警告でスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を提供（権限不足時は警告でスキップ）。

- モニタリング DB 初期化
  - monitoring.monitoring_db に DB 初期化関数を呼び出す利用例を run_monitoring.py/run_execution.py に追加（監視用テーブルが存在することを保証し冪等性を確保）。

- 実行コンポーネントとの連携
  - execution 側の各コンポーネント（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager）を組み込む設計。RiskConfig のデフォルトパラメータ（position 上限、utilization、rate limit、circuit breaker 等）を明示。

- 研究用ファクターモジュール（部分実装）
  - research/factor_research.py を追加（モメンタム・ボラティリティ等の計算を想定）。モメンタム計算を開始するための定数等を定義（calc_momentum の関数シグネチャと説明を含む）。DuckDB を用いたデータ参照を想定。

### Changed
- なし（初回リリースのため）。

### Fixed
- run_monitoring のポーリング間隔取得で無効な値や 0/負の値を検出した場合にデフォルト値へフォールバックする保護処理を追加（MONITOR_POLL_INTERVAL バリデーション）。

### Notes / Behavior details
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する。
- run_execution は paper_trading 環境で本番 DB と切り離した専用 SQLite（デフォルト data/paper_trading.db）を使用するよう設計されており、誤って本番 DB に影響を与えない方針が取られています。
- ログは標準出力（stdout）に出しつつ、可能なら logs/<app_name>.log に日次ローテートで保存します。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。
- process_priority や CPU affinity の設定は権限やプラットフォームによって失敗する可能性があり、その場合は警告を出して処理を継続します。

### Security
- なし

---

この CHANGELOG はリポジトリ内に含まれるソースコードから推測して作成しています。追加の変更点やリリース日付の修正が必要な場合はお知らせください。