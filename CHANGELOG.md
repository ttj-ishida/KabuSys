# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベース（src/ 以下）から推測できる実装内容に基づいて作成されています。

フォーマット:
- Unreleased: 現在開発中の変更（このスナップショットでは主に既実装機能の一覧）
- 各リリース: 追加 (Added) / 変更 (Changed) / 修正 (Fixed) / 非推奨 (Deprecated) / 削除 (Removed) / セキュリティ (Security)

---------------------------------------------------------------------

## [Unreleased]

### Added
- ドキュメント化・ユーティリティの追加
  - 環境設定ウィザード `kabusys.config_setup`（`python -m kabusys.config_setup`）を追加。対話式で .env を生成／更新可能。
  - 設定検証 CLI `kabusys.validate_config`（`python -m kabusys.validate_config`）を追加。.env や config/*.yaml の検証と起動前チェックを実施。
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report`（`python -m kabusys.tools.paper_verification_report`）を追加。稼働率、注文成功率、レイテンシ(P95) 等を集計して PASS/FAIL を判定。
- 実行スクリプト・監視
  - 実行エンジン起動スクリプト `run_execution.py` を追加。`KABUSYS_ENV=paper_trading` 時はペーパートレード用 DB を使用し MockBroker を利用して本番 DB と分離。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。監視用 DB 初期化、DuckDB 接続、ポーリングループ、停止フラグ検知（data/stop_requested.flag）を実装。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能。
- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数の取得・検証（KABUSYS_ENV, LOG_LEVEL 等）、各種パス（DuckDB / SQLite / paper_trading DB）やペーパートレードの設定（PAPER_FILL_MODE）をラップ。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。`.env.local` が `.env` をオーバーライドする優先度を採用。
  - .env パーサを強化。export プレフィックス、クォート文字列のエスケープ、行内コメントの取り扱いなどを考慮して安全に読み込み。
- ポートフォリオ構築モジュール
  - `kabusys.portfolio` を実装。以下の純粋関数群を提供:
    - 候補選定: select_candidates（スコア降順、同点は signal_rank でブレーク）
    - 重み付け: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）
    - セクター集中制限: apply_sector_cap（既存保有を基にセクター比率上限を超える場合に新規候補を除外）
    - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に対応、未知レジームはフォールバック）
    - ポジションサイズ計算: calc_position_sizes（allocation_method: risk_based/equal/score、単元株（lot）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り）
- 監視・プロセス運用ユーティリティ
  - `kabusys.utils.logging_setup` を追加。root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（daily, 30 日保持）を設定。ログレベル・ログディレクトリの優先順位を明示。
  - `kabusys.utils.process_priority` を追加。Windows・POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定。権限不足時は安全にスキップして警告を出力。

### Changed
- ログ関連
  - コンソール出力は stderr ではなく stdout に送る仕様を採用（cron 等で stdout/stderr をまとめる運用に配慮）。
  - ログハンドラが既に存在する場合は一旦 flush/close してから再設定し、重複ハンドラを防止。
- DB 初期化
  - 監視テーブル初期化処理（init_monitoring_db）を実行起点で呼ぶことで、監視・実行双方でテーブル存在を冪等に保証。

### Fixed
- .env 読み込みでのエラー時に警告を出しつつ起動を続行する安全策を追加（ファイル読み込み失敗時に warnings.warn を使用）。
- process_priority や CPU affinity の未対応 OS / 権限エラーを捕捉して警告に落とすように変更（起動失敗を防止）。

### Security
- 環境変数の必須チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を validate_config で明示し、プレースホルダ値の検出と警告を追加。

---------------------------------------------------------------------

## [0.1.0] - 2026-04-19

初回公開（コードベースのスナップショットに基づく推定）

### Added
- ベースライブラリ構成
  - パッケージエントリポイントとバージョン定義（kabusys.__version__ = "0.1.0"）。
  - モジュール群:
    - config: 環境変数読み込み・Settings（パス・閾値等）
    - config_setup: .env 対話式ウィザード
    - validate_config: 起動前チェック CLI
    - run_execution: ExecutionEngine 起動スクリプト（ペーパートレード用 DB 分離）
    - run_monitoring: SystemMonitor 起動スクリプト（ポーリング、停止フラグ）
    - portfolio: 候補選定、重み付け、セクター制限、レジーム乗数、株数計算
    - utils: logging_setup、process_priority（プロセス優先度・CPU affinity）
    - tools.paper_verification_report: Paper Trading の検証レポート生成
    - research.factor_research: ファクター計算モジュール（モジュール骨子、モメンタム等の計算関数を実装予定）
- Execution / Monitoring の運用機能
  - 停止フラグ（data/stop_requested.flag）検出による安全停止
  - PID ファイル管理（設定経由で pid_file_path を指定可能）
  - ポーリング間隔制御（MONITOR_POLL_INTERVAL 環境変数）
- Paper Trading
  - PAPER_FILL_MODE によるペーパートレードの約定挙動切替機能（"instant","partial","never","reject" を想定）
  - paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）を分離して利用

### Changed
- ログ設定の標準化（全起動スクリプトから setup_logging を呼ぶことを想定）
- DuckDB を分析用に導入（duckdb_path の設定を追加）

### Fixed
- 仕様上の安全策（例: ポーリングの sleep に 0 秒以下を渡さないガード）を追加

---------------------------------------------------------------------

注記:
- 本 CHANGELOG は提供されたソースコードの内容から実装意図や利用方法を推測して作成したものです。実際のコミット履歴やリリースノートと完全に一致するとは限りません。
- 日付はこのスナップショットの参照日時（2026-04-19）を利用しています。必要に応じて実際のリリース日・バージョン管理に合わせて調整してください。