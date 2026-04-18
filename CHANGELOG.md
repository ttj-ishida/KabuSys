# Changelog

すべての変更履歴はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

なお本履歴は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴と異なる可能性があります。

## [Unreleased]

### Added
- 起動スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory からブローカークライアントを生成する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定関連 CLI を追加:
  - config_setup.py: .env ファイルの対話式ウィザード（作成・更新）。
  - validate_config.py: .env および config/*.yaml の設定検証ツール（--strict 対応）。
- 設定/環境読み込み:
  - kabusys.config.Settings: 環境変数のラップ。自動 .env / .env.local 読み込み（OS 環境変数保護）、多数のプロパティ（DB パス、ログ設定、paper_trading 用オプション等）。
  - .env パースの堅牢化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント取り扱い等）。
- ロギング・プロセス管理ユーティリティ:
  - utils.logging_setup.setup_logging: stdout ストリームハンドラ + 日次ローテートするファイルハンドラをルートロガーに設定。ログディレクトリ自動作成と失敗時のフォールバック。
  - utils.process_priority.set_process_priority / set_cpu_affinity: Windows/Linux/macOS を吸収する優先度・CPU affinity 設定ユーティリティ。権限不足時は警告を出してスキップ。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の各配分方法、単元株丸め、aggregate cap に基づくスケーリング、コストバッファ考慮。
- Paper Trading 向け検証ツール:
  - tools.paper_verification_report: ペーパートレード用 SQLite を集計し、稼働率・注文成功率・送信率・レイテンシ（P95含む）を算出して PASS/FAIL 判定するレポート生成スクリプト。
- 研究用モジュール（ファクター計算）:
  - research.factor_research: モメンタム等のファクター計算用の土台（DuckDB を用いた prices_daily / raw_financials 参照）。（実装中・一部関数が続きあり）

### Changed
- データベース取り扱い:
  - Execution 起動時に paper_trading 環境では専用の paper_trading.db を使用する（本番 DB と完全分離）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する意図を明示。
  - DuckDB を分析用 DB として採用。
- ログ出力:
  - ログは stdout に出力し、ファイルは日次ローテーションで保持（既定 30 日）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス管理:
  - 起動時に優先度を "high" に設定する呼び出しを各起動スクリプトの最初に実行。
- 設定検証:
  - validate_config により必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行うようにした。

### Fixed
- .env 自動読み込みの安全化:
  - OS 環境変数（既存の環境）を保護する仕組みを導入（.env.local は上書き可能だが OS 環境変数は保護）。
- 起動時の監視/実行停止処理:
  - data/stop_requested.flag による外部停止フラグ検知を導入、検知時に安全にループを抜けるようにした。
- DB 初期化の冪等性:
  - init_monitoring_db を使用して監視テーブルの存在を保証（複数回呼んでも安全）。

### Security
- 機密情報の取り扱い:
  - config_setup の対話時・表示でシークレット項目はマスク表示。`.env` は絶対に Git にコミットしない旨を README に注記（ファイルヘッダに記載）。

### Known issues / Notes
- research.factor_research の実装は途中（ソース末尾が未完の痕跡あり）。投入前に追加実装・レビューが必要。
- position_sizing / risk_adjustment 内に将来の拡張を示す TODO やフォールバックの記載あり（銘柄別 lot_size、価格フォールバック等）。
- 一部の機能は権限や OS に依存（プロセス優先度、CPU affinity）。権限不足時は警告を出して処理をスキップする仕様。

---

## [0.1.0] - 2026-04-18

### Added
- 初回公開リリース相当の機能群を追加:
  - 実行系: ExecutionEngine 起動スクリプト（run_execution.py）、ブローカー抽象化及び実行パイプライン組立て。
  - 監視系: SystemMonitor 起動スクリプト（run_monitoring.py）、監視用 SQLite 初期化。
  - 設定管理: Settings クラス、.env 自動ロード、config_setup（対話ウィザード）、validate_config（検証ツール）。
  - ポートフォリオ構築ライブラリ（候補選定、重み付け、リスク制御、ポジションサイズ計算）。
  - ユーティリティ: ロギング設定（stdout + 日次ローテート）、プロセス優先度 / CPU affinity 設定。
  - ツール: Paper Trading 検証レポート生成スクリプト。
  - 研究用基盤: ファクター計算モジュール（DuckDB 参照ベース）。
- ドキュメント的注記と多数の docstring を追加して設計意図・使用例を明示。

### Changed
- （初回リリースのため特記事項なし）

### Fixed
- （初回リリースのため特記事項なし）

---

未リリースの変更については、今後の開発で確定次第このファイルに反映してください。