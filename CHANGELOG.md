# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリース日: 2026-04-19

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。
- 実行用エントリスクリプトを追加:
  - run_execution: ExecutionEngine を起動するスクリプト。起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続してエンジンをデーモン Thread で実行。停止フラグを検知して安全に停止する仕組みを備える。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する設計。
- 環境設定 / 検証用 CLI を追加:
  - config_setup: .env の対話的ウィザード。主要な環境変数の初期作成・更新を支援。
  - validate_config: .env および config/*.yaml の静的検証ツール。--strict オプションで警告も失敗扱いに可能。
- Paper Trading 向けツール:
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH を指定して DB を参照可能。
- ポートフォリオ構築関連モジュールを追加（純粋関数群、DB 参照なし）:
  - portfolio.portfolio_builder: シグナル絞り込み (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier)。
  - portfolio.position_sizing: 発注株数計算 (calc_position_sizes)。risk_based / equal / score の複数方式に対応。lot_size・cost_buffer・aggregate cap スケーリング等を実装。
- 研究（リサーチ）基盤の一部を追加:
  - research.factor_research: DuckDB を用いたファクター計算ユーティリティ（モメンタム、MA200 乖離等を計算するための下地）。（ファイルは途中まで実装）
- 共通ユーティリティを追加:
  - utils/logging_setup: stdout ストリームと日次ローテートのファイルハンドラ（logs/<app_name>.log）をルートロガーに設定。既存ハンドラをクリアして二重設定を回避。ログディレクトリ作成に失敗した場合はファイル出力をスキップ。
  - utils/process_priority: psutil を用いて Windows / POSIX 間の差を吸収したプロセス優先度設定、及び CPU affinity 設定用ユーティリティを提供。
- 設定管理:
  - config.Settings: 環境変数から設定を取得するクラス。各種既定値とバリデーションを含む（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - .env 自動ロード機能: プロジェクトルート（.git / pyproject.toml）を自動検出して .env / .env.local を読み込む。OS 環境変数の保護、export やクォート対応、コメント処理等を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 監視 DB 初期化ユーティリティ (monitoring_db.init_monitoring_db) と SystemMonitor 呼び出しの統合（run_monitoring / run_execution から利用）。
- パッケージ初期バージョン情報を設定: __version__ = "0.1.0"

### Changed
- ログ出力は stdout を標準ストリームとして利用する設計に（cron / スケジューラとの相性を考慮）。従来の stderr 出力をしない仕様へ変更。

### Fixed
- (設計時点) 環境変数パースの堅牢化: export 形式、クォート内のエスケープ、インラインコメント処理、未定義キーの扱い等を明示的に実装して .env の柔軟な記述に対応。

### Security
- 実機発注に関係する機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings で必須チェックを行い、.env の取り扱い（Git へコミットしない旨のメッセージ）を明確化。

### Notes / Known limitations
- run_monitoring は意図的に KABUSYS_ENV にかかわらず production 用の sqlite_path（settings.sqlite_path）を使用します。監視データを環境ごとに分離したい場合は運用側で sqlite_path を切り替えてください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を利用する想定で本番 DB と分離します。
- portfolio.position_sizing の price フォールバックは未実装（price が欠損 / 0.0 の場合はスキップ）。将来的に前日終値や取得原価でのフォールバックを検討。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する場合があり、失敗時は警告ログを出して処理をスキップします。
- research.factor_research はファクター計算のための下地を含むが、実装が完了していない部分があります（今後の拡張予定）。
- validate_config は PyYAML が未インストールの場合 YAML のパース検証をスキップします（警告を出力）。

### CLI / 実行例
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

注: 本 CHANGELOG はリポジトリ内のソースコードから挙動・機能を推測して作成したものであり、実際の運用・設計当初の意図と若干異なる可能性があります。必要があればリリースノートを調整します。