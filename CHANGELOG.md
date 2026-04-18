CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン管理システムのコミット履歴がないため、リポジトリ内のソースコードから推測して主要な追加・変更点をまとめています。

Unreleased
----------

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使い分ける（data/paper_trading.db をデフォルト）。起動時にプロセス優先度を高く設定し、停止用フラグファイルで安全に停止できる。
  - run_monitoring.py: SystemMonitor を定期ポーリングする監視用スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を参照する仕様。

- 設定関連
  - config.py: 環境変数/`.env` 読み込みと Settings クラスを実装。`.env` 自動ロード（.env/.env.local）機能、複数の設定プロパティ（DB パス、J-Quants/Kabu API トークン、Paper Trading 関連設定、監視しきい値など）を提供。PAPER_FILL_MODE のバリデーションを実装。
  - config_setup.py: .env 作成・更新のための対話式ウィザードを追加。既存 .env の読み込み、シークレット項目のマスク表示、保存確認などの UX を提供。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば検証）を行い、--strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数モジュール）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等金額配分とスコア比率配分を実装。
  - portfolio/risk_adjustment.py: セクター集中度制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）での丸め、ポートフォリオおよび銘柄ごとの上限、aggregate cap によるスケーリング、コストバッファ考慮の処理を含む。
  - portfolio/__init__.py: 上記機能をパッケージとしてエクスポート。

- ユーティリティ
  - utils/logging_setup.py: アプリ共通のログ設定ユーティリティを追加。コンソール stdout 出力と日次ローテーションファイルログ（TimedRotatingFileHandler）を組み合わせ、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定（set_cpu_affinity）も実装。psutil が扱えない環境や権限不足時にログ警告で安全にフォールバック。

- モニタリング DB 初期化
  - monitoring/monitoring_db（参照により init_monitoring_db を利用）を起動スクリプトから呼び出すことで、必要な監視テーブルが存在することを保証する仕組みを追加。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の SQLite データベースを読み、システム稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計してレポート出力するCLIを追加。閾値に基づく PASS/FAIL 判定機能を搭載。

- 研究用モジュール（duckdb 利用）
  - research/factor_research.py: DuckDB 接続を受けてモメンタム・ボラティリティ等のファクター計算を行うためのモジュールを追加。設計方針と定数が定義され、一部（モメンタム計算）を実装中。

### Changed
- .env 読み込みロジックを強化
  - config._parse_env_line: export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いをより厳密に処理するよう改善。既存 OS 環境変数を保護するため protected パラメータを導入し、.env.local を上書き許可の対象にするなどの読み込み優先度を明確化。

- ログ出力の標準化
  - setup_logging によりアプリ全体で同一フォーマット・日次ローテーションが使用されるようになり、起動スクリプトはこのユーティリティを呼ぶことで統一的なログ管理が可能になった。

### Fixed
- 起動時の安全性向上
  - run_execution/run_monitoring において起動直後にプロセス優先度を設定するようにし、停止フラグや停止監視（stop_requested.flag）を利用して安全に停止処理を行うようにした。
  - init_monitoring_db を実行して監視テーブルの不整合によるエラーを未然に防止。

0.1.0 - 2026-04-18
------------------

初回公開版（コードベースから推測）。以下を含む主要機能を実装。

### Added
- 基本アーキテクチャと CLI
  - 実行コンポーネント: ExecutionEngine 起動スクリプト（run_execution.py）と SystemMonitor 起動スクリプト（run_monitoring.py）。
  - 設定 CLI: 対話式 .env ウィザード（config_setup.py）と設定検証ツール（validate_config.py）。
  - バージョン情報: パッケージ version を __version__ = "0.1.0" として設定。

- 設定管理
  - Settings クラス（config.py）により環境変数を一元管理。必須項目チェック（_require）や列挙型パラメータのバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - 自動 .env ロード（プロジェクトルート検出機能を含む）。

- データベース統合
  - SQLite と DuckDB の両方を使用する設計を採用。Monitoring 用の SQLite、分析用の DuckDB を想定。

- ポートフォリオ構築機能
  - シグナル選別、重み付け（等金額・スコア加重）、セクター上限処理、レジーム乗数、ポジションサイズ計算（各種制約・単元丸め・スケーリング）を実装。

- 運用ユーティリティ
  - ロギング設定ユーティリティ（stdout + 日次ファイルローテーション）、プロセス優先度/CPU affinity 設定ユーティリティを提供。
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report.py）。

### Changed
- 監視ロジック
  - SystemMonitor のポーリングループは環境変数 MONITOR_POLL_INTERVAL で調整可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を参照するよう明記。

### Fixed
- 安全停止と PID 管理
  - 実行エンジンは停止フラグの存在チェックを行い、既に停止フラグが立っている場合は起動を中止する。エンジン実行中に停止フラグが立った場合は安全に停止処理を行う。

注記
----
- config/research モジュールや monitoring_db、ExecutionEngine 本体、BrokerClientFactory 等の実装ファイルは本 changelog の対象外（今回提示されたコードの参照・利用を前提としたエントリのみ記載）。実際のリリースノート作成時はそれらの変更点（新規追加/修正/互換性の破壊）を合わせて反映してください。
- 日付はソース解析時点の日付を使用しています。実際のリリースではタグ付け日を使用してください。