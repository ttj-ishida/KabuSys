# Changelog

すべての注目すべき変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

- 既存: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-23

初回公開リリース。自動売買システム「KabuSys」のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、および運用支援ツールを含む。

### Added
- 基本バージョン情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - Settings クラスを実装し、環境変数経由で各種設定（J-Quants / kabu API / DB パス / 環境フラグ / 監視閾値 など）を取得可能に。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出に .git / pyproject.toml を使用）。`.env` と `.env.local` の優先順で環境変数をロード。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パース機能の強化: `export KEY=val` 形式対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ処理、行内コメントの扱い（クォートあり/なしでの振る舞い）等。

- 設定作成ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成・更新を支援（質問プロンプト、既存値の再利用、シークレット値マスク表示、確認後にファイル書き込み）。
  - `.env` 書き込みフォーマットにヘッダコメントを含め、誤って Git にコミットしないよう注意文を記載。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在と（PyYAML があれば）パースチェック、`live` 環境向けの追加ガードを実装。
  - `--strict` オプションにより警告を失敗として扱うモードを追加。

- 実行系 / 監視系スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / default: `data/paper_trading.db`）を使用し、本番 DB と分離。BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動／停止制御（stop フラグファイル監視）。
    - `_EXECUTION_PID`（`data/execution.pid`）への PID ファイル管理をサポート（Engine に渡す）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視（monitoring）用 DB は環境にかかわらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグ（`data/stop_requested.flag`）による安全停止、例外発生時のログ保護を実装。

- ロギングユーティリティ
  - 統一的なログ設定関数 `setup_logging` を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - `set_process_priority(level)` を追加。Windows と POSIX（Linux, macOS, FreeBSD）を吸収し、psutil を用いてプロセスの優先度（nice / Windows priority）を設定。失敗時は警告を出してスキップ。
  - `set_cpu_affinity(cpu_count)` を追加。最初の N コアにプロセスを割り当てる。権限不足や未実装環境の際は警告してスキップ。

- ポートフォリオ構築モジュール
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（同点時 signal_rank によるタイブレーク）および max_positions 制限。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに基づく重み付け（全スコアが 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を越える場合に新規候補を除外（"unknown" セクターは除外対象外）。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告と共に 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。リスクベース計算、単元株（lot_size）丸め、1銘柄上限・合計投下資金（max_utilization）による aggregate cap、コストバッファ（slippage/commission）を考慮したスケーリングと残差処理を実装。
  - portfolio パッケージは上記関数群をエクスポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report を追加。ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から統計を取得し、稼働率・注文成功率・送信率・レイテンシ等の指標を計算してレポート出力。
  - P95 レイテンシ計算、閾値による PASS/FAIL 判定（デフォルト閾値をソース内に定義）。

- リサーチ（未完）
  - research/factor_research モジュールを追加（モメンタム等のファクター計算を行う設計を含む。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（注: ファイル末尾で未完の部分あり）

### Changed
- ロギングの標準出力は stderr ではなく stdout を使用するように変更（cron / スケジューラで stdout/stderr を統一してリダイレクトする運用に配慮）。
- .env 読み込みの優先順位を明確化: OS 環境 > .env.local > .env（既存 OS 環境変数を保護するため protected set を利用）。

### Fixed
- .env 読み込み時にファイルオープン失敗した場合の警告を改善（警告を emit して自動ロードを継続しない）。
- ログハンドラ再設定時に既存ハンドラを安全に flush/close してから削除することでハンドラリークを防止。
- run_monitoring の MONITOR_POLL_INTERVAL が 0 以下や非整数の場合に time.sleep に渡して ValueError となる問題を防ぐため、入力検証とフォールバック処理を実装。

### Notes / Known issues
- research/factor_research の末尾に未完の実装が見られます（calc_momentum の途中で途切れ）。今後のリリースで完成予定。
- 一部のコンポーネント（例: monitoring.monitoring_db や monitoring.system_monitor、execution.Engine）への参照があるが、これらの実装は本差分に含まれないため、統合時に依存関係の確認が必要です。
- process_priority / set_cpu_affinity は権限が必要な環境があり、権限不足時は警告を出してスキップする設計です。

---

(この CHANGELOG はコードベースの内容から推測して作成しました。実際のリリースノート作成時は、コミットメッセージや PR の説明に基づく精査を行ってください。)