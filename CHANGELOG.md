# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys 基本機能一式を追加。
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
- 実行用スクリプトを追加。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。停止はプロジェクト内の `data/stop_requested.flag` によるフラグ検知で行う（src/kabusys/run_monitoring.py）。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、ペーパートレード用 DB を分離して記録する（src/kabusys/run_execution.py）。
- 設定・環境管理を実装。
  - Settings クラスを追加し、環境変数（.env ファイル）から設定を取得するユーティリティを提供。各種デフォルトや型検査・妥当性チェックを実装（src/kabusys/config.py）。
  - .env 自動ロード機能を追加。プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込む。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（src/kabusys/config.py）。
  - 環境変数パーサの改良: export プレフィックス、クォート文字列（エスケープ対応）、インラインコメント取り扱いをサポート（src/kabusys/config.py）。
- 設定支援 CLI を追加。
  - config_setup: 対話式ウィザードで `.env` の初期作成・更新を行うツールを追加。複数の項目定義とデフォルト値・シークレット入力・保存確認を提供（src/kabusys/config_setup.py）。
  - validate_config: `.env` および config/*.yaml の検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス確認、YAML パース（PyYAML があれば実行）、本番環境向けの注意喚起を実装。`--strict` モードをサポート（src/kabusys/validate_config.py）。
- ポートフォリオ構築関連の純粋関数群を追加（DB非依存）。
  - portfolio_builder: 候補選定（スコア順ソート）、等金額配分、スコア加重配分（全てのスコアが 0 の場合のフォールバックを含む）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームによる投下資金乗数（calc_regime_multiplier）を実装。未知レジームのフォールバックやログ出力を含む（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score 向け）。単元株丸め、per-position・aggregate キャップ、コストバッファ、スケーリング処理（残差配分ロジック）を実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。
- ユーティリティを追加 / 改良。
  - logging_setup: ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート）を設定する共通ユーティリティを追加。ログディレクトリ自動作成、作成失敗時のフォールバック（コンソールのみ）、ログレベル/ディレクトリ解決順を実装（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows / POSIX の差異を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定関数も提供し、権限不足時に警告を出して安全にスキップする（src/kabusys/utils/process_priority.py）。
- Paper Trading 検証レポート生成ツールを追加。
  - tools/paper_verification_report: ペーパートレード用 SQLite から各種指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95））を集計してレポート出力。基準閾値に基づく PASS/FAIL 判定を実装（src/kabusys/tools/paper_verification_report.py）。
- DuckDB 統合: 分析用途に DuckDB 接続を利用する実装を追加（各スクリプトで duckdb.connect を使用）。

### Changed
- ロギングにおける標準出力の扱いを明示的に stdout に統一（cron/タスク実行時のリダイレクト対策）（src/kabusys/utils/logging_setup.py）。
- run_monitoring のデフォルトポーリング間隔を 60 秒に設定。環境変数で上書き可能だが不正値はデフォルトにフォールバックして警告を出す（src/kabusys/run_monitoring.py）。
- run_execution: ペーパートレード環境では専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番データと分離するよう変更（src/kabusys/run_execution.py）。

### Fixed
- .env 自動ロード時にプロジェクトルートが検出できない場合は自動ロードをスキップし、テスト環境等での誤動作を防止（src/kabusys/config.py）。
- logging_setup: ログディレクトリ作成に失敗した場合でもアプリがクラッシュしないようファイルハンドラ作成をスキップしてコンソール出力のみで継続する処理を追加（src/kabusys/utils/logging_setup.py）。
- process_priority: サポート外 OS や権限不足時に例外で落ちないよう警告ログでスキップするように改善（src/kabusys/utils/process_priority.py）。
- position_sizing: 投下合計が利用可能現金を超える場合のスケーリングと residual（端数）配分アルゴリズムを実装して、より安定した株数決定を行うように修正（src/kabusys/portfolio/position_sizing.py）。
- Paper Verification レポート: レイテンシ P95 算出ロジックを追加（空データへの安全な対応含む）（src/kabusys/tools/paper_verification_report.py）。
- validate_config: PyYAML が未インストールの環境でも実行可能にし、YAML の検証有無を警告で扱うように改善（src/kabusys/validate_config.py）。

### Notes
- 監視（monitoring）機能は本番用 sqlite_path を参照する実装になっているため、環境に関わらず monitoring 用 DB の取り扱いに注意してください（src/kabusys/run_monitoring.py）。
- run_execution は起動時に stop フラグ（data/stop_requested.flag）を検査し、既に立っている場合は起動を中止します。また、エンジンは別スレッドで動作し、停止フラグ検知で engine.stop() を呼ぶことで安全に終了します（src/kabusys/run_execution.py）。
- config_setup で生成される `.env` はセキュアな情報を含むため、絶対に Git 等へコミットしないことを README 等で明示する想定です（src/kabusys/config_setup.py）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

この CHANGELOG はソースコード（主に src/ 以下）から推測して作成しています。実際のリリースノート作成時は、コミット履歴や実際の変更差分に基づき必要に応じて調整してください。