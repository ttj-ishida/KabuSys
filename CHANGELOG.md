# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴と差異がある可能性があります。

## [Unreleased]

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、ペーパートレーディング用 DB（data/paper_trading.db）を使用する分離設計を採用。実行中の PID 管理と stop フラグ検知ロジックを含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する仕様。
- 設定関連
  - config.py: 環境変数・設定の集中管理クラス `Settings` を実装。デフォルト値やバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を提供。
  - config_setup.py: 対話式ウィザードにより .env を初期作成／更新する CLI を追加。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加（--strict オプションあり）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: stdout 出力 + 日次ローテートファイルハンドラを統一的に設定するユーティリティを追加。ログディレクトリ作成失敗時のフォールバックや既存ハンドラのクリア処理を実装。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収してプロセス優先度（および CPU affinity）を設定するユーティリティを追加。失敗時は安全にスキップする設計。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコアでソート）と等配分・スコア加重配分の純粋関数を実装。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based, equal, score）・単元丸め・aggregate cap によるスケールダウン機構を実装。
  - portfolio.__init__: 上記機能のエクスポートを追加。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレーディング DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL 判定を出力するレポート生成スクリプトを追加。閾値は定数で定義（稼働率 99% など）。
- Research 用ユーティリティ（着手）
  - research/factor_research.py: DuckDB を利用したファクター計算モジュール（モメンタム、MA200、ATR、出来高等）の設計を追加（実装の一部が含まれる）。

### Changed
- 環境変数読み込みロジックを強化（config.py）
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env/.env.local をロード（OS 環境変数より優先されない、.env.local は上書き可）。
  - _parse_env_line により、export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、行内コメントの取り扱いを慎重に処理するよう改善。
  - _load_env_file は既存 OS 環境変数を protected として上書きを制御。
- ログ設定の挙動を明確化（utils/logging_setup.py）
  - stdout を使用することで外部ジョブスケジューラとのリダイレクト互換性を向上。
  - ログファイルの日次ローテーション（30 日保持）を導入。
- プロセス優先度の扱い（utils/process_priority.py）
  - Windows と POSIX の差分を吸収して呼び出し元が OS を意識せず利用可能に。
  - 権限不足や未サポート環境では警告ログを出して安全に継続。

### Fixed
- .env パーサーの不正行ハンドリング改善（config.py）
  - 空行やコメント行、export 付き行、クォート内エスケープ、インラインコメントの取り扱いに起因する誤設定を防止。
- run_execution / run_monitoring におけるリソースクローズ処理を確実化
  - finally ブロックで sqlite / duckdb 接続をクローズするようにしてリソースリークを防止。

### Documentation
- 各モジュールに docstring を追加・強化
  - 各関数・クラスに使用例や引数説明、設計上の注意（例: price 欠損時の挙動、regime multiplier の仕様）を明記。
- config_setup のウィザード出力テンプレートに .env ファイルの注記を追加（Git にコミットしない旨など）。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース相当の機能群を導入:
  - 実行・監視の起動スクリプト（run_execution, run_monitoring）
  - 環境設定/検証 CLI（config_setup, validate_config）
  - Settings ベースの環境変数管理（config.py）
  - ロギング設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度ユーティリティ（utils/process_priority.py）
  - ポートフォリオ構築（selection / weighting / position sizing / risk adjustment）
  - Paper Trading 検証レポート生成ツール
  - DuckDB を利用したリサーチ用ファクター計算の骨格

### Changed
- ログ出力とファイルローテーションのデフォルト設定を導入。
- Paper Trading と 本番 DB を分離する設計（PAPER_TRADING_SQLITE_PATH のサポート）。

### Fixed
- 環境変数パーサーの不具合修正（クォート・コメント処理等）。
- 各種起動処理における安全なクリーンアップを追加。

---

訳注:
- 上記はソースコードから推測して記載した CHANGELOG です。実際のリポジトリのコミット単位・日付・バージョン運用に合わせて必要に応じて調整してください。