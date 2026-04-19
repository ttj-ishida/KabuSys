# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-19

初回リリース。以下の機能・モジュールを実装しました。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、SQLite / DuckDB 接続、BrokerClientFactory を経由したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine のバックグラウンド実行を行います。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）と MockBrokerClient を利用する仕組みを実装。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB は環境にかかわらず本番 sqlite_path を参照する設計。

- 設定管理・検証
  - config.py: .env 自動読み込み（.env.local を優先）、堅牢な .env パーサ（クォート・エスケープ・インラインコメント対応）、Settings クラス（環境変数のラッパー・妥当性チェック）を実装。Paper Trading 用パスや各種閾値・フラグ取得用プロパティを提供。
  - config_setup.py: 対話式 .env 作成ウィザードを実装（J-Quants / kabu API / DB パス等の入力支援、既存値の再利用、保存機能）。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）。--strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: シグナルの上位選定（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）を実装。スコア全0 の際のフォールバックと警告を含む。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。レジームマップ（bull/neutral/bear）と未知レジームのフォールバックを備える。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）に対応し、単元株丸め（lot_size）、1銘柄上限・アグリゲートキャップ、cost_buffer を考慮したスケーリングロジック、端数処理のための残差配分ロジックなどを実装。

- ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定ユーティリティを追加。コンソール出力（stdout）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバックをサポート。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows / POSIX（Linux, macOS, FreeBSD）に対応し、権限不足等は警告でスキップ。

- 監視・レポート
  - monitoring DB 初期化の呼び出しを各スクリプトで行う仕組みを追加（init_monitoring_db を利用して監視テーブルの冪等な作成を保証）。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。期間指定（--from / --to）や DB 指定（--db）に対応し、稼働率・注文成功率・送信率・P95 レイテンシなどを算出して PASS/FAIL 判定を行う。P95 計算、しきい値（稼働率99%、成立率90% 等）を定義。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨格を追加。モメンタム・移動平均・ATR・流動性等の計算方針と定数を定義し、calc_momentum のインターフェースを着手（prices_daily / raw_financials を DuckDB 経由で参照する設計）。（実装は一部未完）

- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 に設定し、主要サブパッケージを __all__ で公開。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注記:
- 多くのモジュールは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。運用時は必要な依存関係をインストールしてください。
- 一部の実装（例: research/factor_research.calc_momentum の詳細実装、価格フォールバックロジックなど）は将来の改善候補として TODO コメントがあります。