# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回リリース。以下の主要機能・モジュールを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数経由で各種設定（J-Quants / kabu API / DB パス / ログ等）を取得。
  - .env 自動読み込み機構を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を優先）。自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - .env パーサーは `export KEY=val`、引用符付き値、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - 必須環境変数未設定時に例外を出す `_require` を提供。
  - Paper Trading 用設定（`PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH`）をサポート。
- 環境設定ウィザード
  - `kabusys.config_setup`：対話式ウィザードで .env を作成/更新する CLI を追加。デフォルト値・選択肢表示・シークレットマスク表示をサポート。
- 設定検証ツール
  - `kabusys.validate_config`：起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）等をチェック。`--strict` オプションで警告を失敗扱いにできる。
- 実行/監視ランナー
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（`KABUSYS_ENV=paper_trading` の場合は専用 DB と MockBrokerClient の利用を想定）。PID ファイル管理、停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- ログユーティリティ
  - `kabusys.utils.logging_setup`：統一ログ設定関数 `setup_logging` を追加。stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日分保持）を設定。ログレベル・ログディレクトリの解決順を定義。
- プロセス優先度 / CPU アフィニティ
  - `kabusys.utils.process_priority`：クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）と CPU affinity 固定のユーティリティを追加。権限不足時は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア全て 0 の場合は等重にフォールバック。
  - `kabusys.portfolio.risk_adjustment`：セクター集中制限の適用（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック動作を持つ。
  - `kabusys.portfolio.position_sizing`：株数算出ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）および余りを考慮した追加配分ロジックを実装。
  - これらはすべてメモリ内純粋関数で DB 参照なし。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード用 SQLite（デフォルト data/paper_trading.db）からメトリクス（稼働率、注文成功率、送信率、レイテンシ等）を集計しレポート出力する CLI を追加。P95 計算・閾値による PASS/FAIL 判定を実装。期間フィルタ（--from/--to）と --db オプションをサポート。
- リサーチ（ファクター計算）
  - `kabusys.research.factor_research`：DuckDB 接続を受けて各種定量ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計を追加。モメンタム計算のための定数・スキャン範囲を定義（実装途中ファイルあり）。

### Changed
- なし（初回リリースのため既存変更はなし）

### Fixed
- なし（初回リリースのため bugfix は無し）

---

注記:
- 設定や挙動に関する多くの安全策（停止フラグ、PID ファイル、監視 DB 初期化、ログディレクトリ作成失敗時のフォールバックなど）が実装されています。
- Paper Trading は本番 DB と完全分離されることを意図しており、`Settings` 経由で切り替え可能です。
- 今後のリリースではリサーチ系の関数の完成、外部依存（PyYAML 等）に対するさらなる検証、ユニットテスト追加、ドキュメントの充実を推奨します。