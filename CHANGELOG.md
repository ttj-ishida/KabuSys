# Changelog

すべての注目すべき変更履歴をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

なおバージョンはパッケージ内の __version__ に合わせています。

## [Unreleased]

### Added
- 新規: プロジェクト初期実装として自動売買システム "KabuSys" のコア機能を追加。
- 設定管理:
  - 環境変数 / .env 読み込み機能を実装（kabusys.config）。
  - .env/.env.local の自動読み込み（OS 環境変数を保護）および自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの強化（export プレフィックス、クォートされた値、インラインコメントの取り扱い）。
  - Settings クラスで各種設定プロパティを提供（DB パス、API トークン、Paper Trading 設定、閾値など）。
- 初期化・対話ツール:
  - 環境設定ウィザード CLI を実装（kabusys.config_setup）。.env の初期作成 / 更新を対話形式で支援。
  - 設定検証 CLI を実装（kabusys.validate_config）。必須環境変数・パス・YAML ファイル等の事前チェックと --strict モードをサポート。
- 実行/監視スクリプト:
  - run_execution.py: ExecutionEngine の起動用スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading DB を分離して使用する振る舞いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
  - 停止制御フラグ（data/stop_requested.flag, data/execution.pid など）によるプロセス停止制御を実装。
- ログ / プロセス運用ユーティリティ:
  - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。コンソール出力（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler、30日保持）を設定。
  - プロセス優先度および CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。Windows / POSIX の差分を吸収しフォールバックを実装。
- ポートフォリオ構築:
  - 銘柄候補選定と重み計算（kabusys.portfolio.portfolio_builder）。
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア全0時のフォールバック処理を含む。
  - セクター集中チェック・レジーム乗数（kabusys.portfolio.risk_adjustment）。
    - apply_sector_cap: セクター別上限超過時の候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear）および未知レジームでの警告。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）。
    - risk_based / equal / score の発注株数算出、lot_size（単元）考慮、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer の考慮などを実装。
- 研究用ファクター計算基盤:
  - factor_research モジュールを追加（DuckDB による価格・財務データ参照を前提）。（一部未完の実装箇所あり）
- ペーパートレード検証:
  - tools/paper_verification_report.py を追加。Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定レポートを生成する CLI を実装（--from/--to/--db オプション対応）。
- Execution 周りの依存コンポーネント（リポジトリ、オーダーマネージャ、リスクマネージャ、再整合化器等）の組み立てを run_execution 側で行う実装を追加（BrokerClientFactory 利用）。

### Changed
- ログ出力:
  - StreamHandler を stdout に固定（stderr ではなく）。cron 等で stdout/stderr 統合リダイレクトしやすくするため。
  - 既存ハンドラがある場合は一旦 flush/close の上でクリアして再設定（重複設定防止）。
- 設定検証:
  - validate_config により起動前に .env と config/*.yaml の基本チェックを行い、PyYAML 未インストール時は YAML 検証をスキップして警告に留める。

### Fixed
- env ファイル読み込み時のエラー処理強化（ファイル読み込み失敗時に警告を出す）。
- process_priority の例外処理を強化し、設定権限不足や未対応プラットフォームでも安全にスキップするようにした。
- run_monitoring のポーリングで check_once() が例外を投げても監視ループを継続し、例外内容をログ出力するように改善。
- run_execution で paper_trading 環境時に本番 DB と分離し専用 DB を使用するよう修正（PAPER_TRADING_SQLITE_PATH を尊重）。

### Security
- .env 取り扱い注意をドキュメント内で明記（.env を絶対に Git にコミットしない旨を config_setup の出力に追記）。

---

## [0.1.0] - 2026-04-20

初回公開リリース。上記の機能群をまとめて v0.1.0 としてリリース。

### Added
- パッケージ初期実装一式（config, utils, portfolio, monitoring, execution, tools, research 等）。
- CLI: config_setup（対話式 .env 作成）、validate_config（設定検証）、tools.paper_verification_report（ペーパートレード検証レポート）。
- run_execution / run_monitoring の起動スクリプトと停止フラグ制御。
- DuckDB / SQLite を利用したデータアクセス基盤の利用（設定可能なパスとデフォルトパスを提供）。
- ロギングの統一設定（コンソール + 日次ローテーション、ログディレクトリ作成失敗時のフォールバック）。
- Process 優先度 / CPU affinity のユーティリティ（クロスプラットフォーム対応のフォールバック実装）。
- ポートフォリオ構築ロジック（候補選定・重み付け・セクター制限・ポジションサイズ算出）。
- Paper Trading 用検証レポートおよび判定基準（稼働率、成功率、送信率、P95 レイテンシ等）。

### Changed
- 初期リリースのため該当なし（ベース実装としてのリリース）。

### Fixed
- 初期リリースのため該当なし（実装段階での堅牢性向上を反映済み）。

---

### 表記・運用上の注意
- デフォルトのデータパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- 本番環境（KABUSYS_ENV=live）では .env の設定、特に LINE 通知周り（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください。validate_config が警告を出します。
- .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください（config_setup が警告を出します）。

---

（必要に応じて今後のバージョンで細分化された変更をこのファイルに追記してください）