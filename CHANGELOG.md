# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- コアランタイム / 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度を上げて実行し、KABUSYS_ENV に応じて本番/ペーパートレード用 DB を切り替え。ペーパートレード時は専用の SQLite（data/paper_trading.db をデフォルト）を使用する。停止フラグ（data/stop_requested.flag）検知によるシャットダウン、実行用 PID ファイル管理に対応。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番用 sqlite_path を使用する（監視は本番 DB を参照する設計）。
- 設定管理
  - config: 環境変数・設定管理クラス `Settings` を追加。.env 自動読み込み（プロジェクトルートを検出して .env / .env.local を読み込み）を実装。多くの設定プロパティ（J-Quants, kabuステーション, DuckDB/SQLite パス、Paper Trading 設定、監視閾値、環境 / ログレベル判定など）を提供し、値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）を行う。
  - .env パーサ: export 文対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの取り扱い等をサポートする堅牢なパーサを実装。
- 設定補助 CLI
  - config_setup: 対話式ウィザードを追加。.env の初期作成・更新を支援。シークレット項目は表示をマスク、選択肢・デフォルト表示、保存確認を実装。
  - validate_config: 設定検証 CLI を追加。必須環境変数や KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知・KILL_FLAG_CLEAR_ON_START など）をチェック。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを提供。ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで動作。
  - utils.process_priority: psutil を用いて Windows/Linux/Mac の差分を吸収したプロセス優先度設定関数を追加。CPU affinity を設定する set_cpu_affinity も提供。権限不足や未対応環境では警告を出して安全にフォールバックする。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定（スコア降順、タイブレークルール）と等金額／スコア重み付けを実装。スコアが全て 0 の場合は等重にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap（売却予定銘柄を除外可能、"unknown" セクターは制限除外）と、マーケットレジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知のレジームは警告とともに 1.0 でフォールバック）を実装。
  - portfolio.position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。損切り率・リスク割合・単元株（lot_size）丸め、1 銘柄上限や aggregate cap（利用可能現金を超える場合のスケーリング）を考慮。cost_buffer により手数料/スリッページを保守的に見積もるロジックを内蔵。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db）からデータを集計し、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（Avg/Max/P95）を出力。閾値による PASS/FAIL 判定を行い、期間指定（--from / --to）に対応。
  - P95 計算、欠損時の安全なフォールバック（テーブルが無い場合の例外処理）を実装。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等の定量ファクターを計算するためのモジュールを追加（prices_daily / raw_financials テーブル参照、Zスコア正規化を想定）。（モジュールは設計に基づく実装を含む）
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" として定義。
  - kabusys パッケージの主要エクスポートを定義（data, strategy, execution, monitoring 等を __all__ に含める）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / 動作上の注意
- run_monitoring は「監視用途」の DB 接続において環境にかかわらず Settings.sqlite_path（本番想定のパス）を使用します。監視データを分離したい場合は設定で適切な sqlite_path を指定してください。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正な値（0 以下や非数）は警告が出て 60 秒にフォールバックします。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストなどで利用）。
- ログディレクトリ作成やプロセス優先度の変更は権限に依存します。権限不足時は警告を出して処理をスキップします。
- Paper Trading（KABUSYS_ENV=paper_trading）時の Fill モードは PAPER_FILL_MODE で設定可能（instant/partial/never/reject）。不正な値は ValueError で弾かれます。

---

（今後は Unreleased セクションに変更を積み上げ、リリースごとにバージョンタグ・日付を追加してください。）