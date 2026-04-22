# CHANGELOG

すべての注記は Keep a Changelog のフォーマットに準拠しています。  

未解決の問題や将来的な変更点は "Unreleased" に記載します。

## [Unreleased]

- —（現在未リリースの変更はありません）—

---

## [0.1.0] - 2026-04-22

初回公開リリース。KabuSys 自動売買システムの基幹ユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツールなどを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository、OrderManager、RiskManager、Reconciler の組み立て。
    - 実行中の PID ファイル管理、data/stop_requested.flag による安全停止機構、デーモンスレッドでのエンジン実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用し、停止フラグファイルでループ終了。

- 設定管理
  - config.py
    - .env ファイルの自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env 解析の強化：export 修飾、クォート内エスケープ、インラインコメント処理などに対応。
    - Settings クラスを導入し、アプリ全体で環境設定を統一提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 等）。
    - `paper_fill_mode` の検証（有効値: instant, partial, never, reject）。
    - `paper_sqlite_path`、`pid_file_path`、`kill_flag_path`、kill フラグの自動クリア設定、リソース閾値（CPU/メモリ/ディスク）などのプロパティを提供。

- 設定作成・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - J-Quants / kabu ステーション / DB 等の主要設定項目を案内。
  - validate_config.py
    - 起動前に .env や config/*.yaml の問題を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル、DB パス、YAML ファイル存在・パース検査、ライブ環境向け注意点などを出力。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定するユーティリティ `setup_logging`。
    - LOG_DIR/LOG_LEVEL の解決順をサポートし、ログディレクトリ作成失敗時はファイル出力を自動で無効化してコンソール出力のみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定 `set_process_priority(level)`（Windows / POSIX 対応）。
    - CPU コア固定用 `set_cpu_affinity(cpu_count)`（存在しない環境では安全にスキップ）。
    - アクセス権限や未対応 OS に対するフォールバックと警告出力。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates`（スコア降順、signal_rank でタイブレーク）。
    - ウェイト計算 `calc_equal_weights`, `calc_score_weights`（スコア総和が 0 の場合は等金額配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap`（既存保有と当日売却予定銘柄を考慮して新規候補をフィルタ）。
    - 市場レジームに基づく乗数 `calc_regime_multiplier`（bull/neutral/bear をマッピング、未知は警告の上フォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出 `calc_position_sizes`。
    - allocation_method（risk_based / equal / score）サポート、lot_size（単元）処理、単銘柄上限・集計上限（available_cash）によるスケールダウン、cost_buffer を用いた保守的見積り。
    - スケーリング時の端数処理（lot 単位で残差を考慮して追加配分）。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計するレポート生成 CLI。
    - 合格/不合格の基準値を定義（稼働率 99% など）し、PASS/FAIL 判定を出力。
    - P95 計算ユーティリティ、日付フィルタ、欠損テーブルへの耐性を実装。

- 研究用ファクター計算（実装途中）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 系ファクター算出を目指すモジュールを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。一部実装が継続中。

- DB 初期化フック
  - monitoring/monitoring_db.py への参照（起動スクリプトが監視用テーブル存在を保証するために init_monitoring_db を呼び出す実装を統一）。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Removed
- なし（初回リリース）。

### Security
- 環境変数の取り扱いに注意する旨をドキュメント・ウィザード内に明記（.env を絶対にコミットしないなどの注意喚起を追加）。

---

注記:
- 本リリースは主にフレームワークとユーティリティの整備に焦点を当てており、Strategy/Execution の具体的戦略実装や完全な factor 計算は今後のリリースで順次追加・完成されます。
- 実行時は .env（.env.local）で必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を設定してください。validate_config.py を使った事前検証を推奨します。