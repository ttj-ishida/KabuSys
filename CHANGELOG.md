# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。  

- リリースノートは主にソースコードの内容から推測して作成しています。
- 日付は本ファイル作成日（2026-04-22）を使用しています。

## [Unreleased]

### Added
- 初期実装（主要コンポーネント群）。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動用スクリプト。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB を使用し MockBrokerClient を利用する旨をサポート。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知による安全停止に対応。
  - 設定管理
    - config.py: .env 自動読み込み（.env, .env.local、OS 環境変数保護ルール）、Settings クラス（各種環境変数のラッパーとバリデーション）を実装。paper_trading 用の PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などをサポート。
    - config_setup.py: 対話式 .env 作成・更新ウィザード。デフォルトや既存値の再利用、シークレットマスク表示などを提供。
    - validate_config.py: 起動前に .env と config/*.yaml の簡易検証を行う CLI。--strict オプションで警告も失敗扱いに可能。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額 / スコア加重の重み計算（calc_equal_weights / calc_score_weights）。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）。単元株（lot_size）対応、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮。
    - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティ。stdout ストリームハンドラおよび日次ローテート（TimedRotatingFileHandler）を使用。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows / POSIX を吸収）、CPU affinity 設定ユーティリティ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプト。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 含む）等を集計・判定。閾値はソース内に定義（稼働率 99% など）。
  - 研究モジュール（途中実装）
    - research/factor_research.py: ファクター計算モジュールの骨組み。モメンタム等の定義と calc_momentum の記述開始（DuckDB を使用して prices_daily を参照する設計）。

### Changed
- ログ管理の挙動を明確化
  - setup_logging で、既存ハンドラを一度 flush/close してから再設定することで多重ハンドラ登録を防止。
  - stdout を StreamHandler に使用（cron 等で stdout/stderr を一本化する運用を想定）。
- run_monitoring の DB 接続/初期化
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の仕様を明記。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にて quote とエスケープ処理、インラインコメントの扱い、export KEY=val 形式をサポート。
- MONITOR_POLL_INTERVAL の不正値対処
  - run_monitoring._get_poll_interval で非数値や 0 以下が指定された場合に警告を出しデフォルトにフォールバックするよう処理を追加。

### Notes
- デフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/（環境変数 LOG_DIR で上書き可能）
- 実行時にプロセス優先度を "high" に設定する呼び出しを各起動スクリプトで行う（set_process_priority("high")）。

## [0.1.0] - 2026-04-22

初回公開バージョン（推定）として次を含むリリース。

### Added
- 上記 Unreleased の主要機能を初期リリースとして追加。
  - Execution/Monitoring 起動スクリプト、Settings/.env 自動読み込み、設定ウィザード、設定検証 CLI、ポートフォリオ構築/サイズ決定/リスク調整モジュール、ログ設定・プロセス優先度ユーティリティ、Paper Trading 検証レポート、研究モジュールの基盤。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリースで既知の振る舞いを安定化）。

### Known issues / TODO (初回リリース時点)
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされ、想定外の除外漏れが発生する可能性あり。ソース内に将来的な価格フォールバック案（前日終値や取得原価）を注記。
- position_sizing:
  - 将来的には銘柄ごとの lot_size を対応する拡張を想定（現在はグローバル lot_size のみ）。
- research/factor_research:
  - ファイルは設計方針・定数・calc_momentum の冒頭まで実装されているが、完全実装・テストが必要。
- DB / ファイル操作のエラー処理やリカバリ、ユニットテストなどの強化が必要。
- 監視や実行コンポーネントの統合テスト（本番接続や Mock の検証）未整備。

## 開発者向け備考
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行うため、パッケージ化後でも CWD に依存せず機能する設計。
- 設定の自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップし警告を出す。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップされコンソールログのみで動作するため、運用環境ではログディレクトリ権限に注意。

---

この CHANGELOG はソースコードから推測して作成しています。より正確な差分や過去の変更履歴が必要な場合は、コミット履歴（git log）やリリースノートの追加情報を提供してください。