# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

次のバージョンは semver に基づき管理してください。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本アプリケーション骨格を追加
  - パッケージ情報: kabusys/__init__.py にバージョン 0.1.0 を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を利用する設計を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番用 sqlite_path を使用する（環境に依存しない）。
- 環境設定・検証ツール
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI を追加（`--strict` オプションで警告も失敗扱い）。
  - 環境変数自動読み込み機能を追加（プロジェクトルート(.git または pyproject.toml) を探索して `.env` → `.env.local` の順で読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
- 設定管理
  - config.py: Settings クラスを実装。環境変数のパース/検証ロジック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション）やパス解決（duckdb/sqlite/paper_sqlite/pid/kill flag）を提供。`.env` のクォートやエスケープ、インラインコメント等を正しく扱う堅牢なパーサを実装。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定するユーティリティを追加。LOG_DIR/LOG_LEVEL の解決やファイル出力失敗時のフォールバックをサポート。
  - utils/process_priority.py: psutil を使ったプロセス優先度設定・CPU affinity ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足時には警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークルール）と等配分・スコア加重配分の関数を追加。スコア全てが0の場合のフォールバックとログ出力を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap、および市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバックして 1.0 を返す。
  - portfolio/position_sizing.py: 単銘柄・集計上限・lot 単位丸め・コストバッファ・リスクベース配分などを考慮した株数決定ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポートし、aggregate cap 超過時にはスケールダウンと余剰配分ロジックを持つ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、PASS/FAIL 判定付きレポートを出力するスクリプトを追加。しきい値はソース内定数で定義（稼働率 99% 等）。
- 研究用モジュール（骨組み）
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールのスケルトンを追加（モメンタム・ボラティリティ等の計算方針と定数を含む）。将来的なファクター計算実装の基盤を提供。

### Changed
- DB 周りの動作方針を明文化
  - 監視(run_monitoring)は KABUSYS_ENV にかかわらず監視用（本番） sqlite_path を使用する方針を明示。
  - 実行(run_execution)は paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離する。

### Fixed
- .env パーサの堅牢化
  - config._parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、export プレフィックス対応などを実装し、実運用での .env 設定ミスを低減。
- ロギング設定の安全化
  - ログディレクトリの作成失敗やファイルハンドラの作成失敗時にコンソール出力のみで継続するようにし、起動失敗につながらないように変更。
- プロセス優先度・CPU 固定処理の安全化
  - 権限不足や未対応 OS の場合に警告ログを出して処理をスキップするように変更。Windows/POSIX 間の定数差異を考慮。

### Security
- .env の取り扱いに関する注意書きを config_setup.py に追加（.env を絶対に Git にコミットしない旨）。

### Notes / Implementation details
- stop フラグ / pid ファイル:
  - 実行・監視スクリプトはプロジェクト直下 data ディレクトリに配置された stop_requested.flag を検知して安全に停止する設計。
  - ExecutionEngine は起動時に停止フラグが立っていれば起動を中止する。
- CLI 実行例を各モジュールにコメントで記載（python -m kabusys.validate_config 等）。
- 一部モジュール（monitoring.monitoring_db、monitoring.system_monitor、execution.* の詳細実装）は本差分に含まれないが、起動フロー/依存注入の設計が整備されている。

(今後)
- research/factor_research の具体的実装（SQL/計算ロジック）を継続実装予定。
- 実運用向けにログフォーマットやアラート（LINE 連携）周りの強化、各種設定値のドキュメント化を推進。