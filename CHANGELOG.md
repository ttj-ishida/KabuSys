CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

## [Unreleased]

### Added
- 設定ウィザード CLI を追加（kabusys.config_setup）。対話式で .env の初期作成 / 更新を支援し、テンプレート書き出し機能を持つ。
- 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数・パス・config/*.yaml の存在と簡易パースを検証し、--strict オプションで警告を FAIL 扱いにできる。
- 実行系起動スクリプトを追加（kabusys.run_execution）。ExecutionEngine の起動フローを組み立て、以下を実現:
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し、本番 DB と分離（MockBrokerClient の利用を想定）。
  - BrokerClientFactory によるブローカークライアント生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動・監視。
  - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイルの扱い。
- 監視系起動スクリプトを追加（kabusys.run_monitoring）。SystemMonitor のポーリングループを実装:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
  - 停止フラグ検知、例外発生時のログ出力とポーリング継続処理を実装。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
  - 日付フィルタ (--from / --to) と DB パス指定 (--db / 環境変数) に対応。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）:
  - portfolio_builder: 候補選定（select_candidates）、等重配分 / スコア加重（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数算出（calc_position_sizes）。allocation_method（risk_based / equal / score）、lot_size による丸め、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り等を実装。
- 汎用ユーティリティを追加 / 強化:
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）: stdout 出力と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに統一的に設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度ユーティリティ（kabusys.utils.process_priority）: Windows / POSIX を吸収した優先度設定、CPU affinity 設定、および失敗時のフォールバックロギングを実装。
- Settings（kabusys.config.Settings）周りの追加 / 強化:
  - .env 自動読み込み機構（.env / .env.local）をプロジェクトルート検知ロジックとともに実装。OS 環境変数（既存値）は保護され、.env.local は上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - PAPER_FILL_MODE の検証（有効値: instant / partial / never / reject）。不正値は例外を送出。
  - paper_trading 用 SQLite パス（paper_sqlite_path）や監視用閾値などのプロパティを提供。
- 監視 DB 初期化ヘルパを追加（monitoring.monitoring_db.init_monitoring_db）を呼び出して、監視テーブルの存在を起動時に保証（冪等）。
- パッケージメタ情報にバージョンを追加（kabusys.__version__ = "0.1.0"）。

### Changed
- .env パーサーの強化:
  - export KEY=val 形式に対応。
  - シングル / ダブルクォートされた値のバックスラッシュエスケープ処理を実装し、対応する閉じクォートまで正しくパース。
  - クォートなし値に対するインラインコメント判定のルールを明確化（'#' の直前が空白/タブの場合のみコメントとみなす）。
  - .env 読み込みはプロジェクトルート（.git または pyproject.toml 基準）を探索して行うため、CWD に依存しない。
  - _load_env_file に protected 引数を追加し、OS 環境変数の上書きを防止。
- ロギング設定の挙動調整:
  - stdout に StreamHandler を出力先として使用（cron / Task Scheduler 環境を考慮）。
  - 既存ハンドラがある場合、二重設定を防ぐために一度 flush/close してから再設定。
  - ログディレクトリ作成失敗時の振る舞いをファイル出力スキップへ明示化。
- run_execution / run_monitoring 起動フローを整理し、最初にプロセス優先度を上げる（set_process_priority("high")）処理を共通化。
- ExecutionEngine 起動フローで、停止フラグが既に立っている場合は起動を中止してすぐに終了するように変更。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数値）を検出してデフォルト（60 秒）にフォールバックし、警告ログを出力するように修正。
- ログディレクトリ作成やファイルハンドラ作成で例外が発生してもプロセスがクラッシュしないようにフォールバック処理を追加。
- process_priority / set_cpu_affinity で権限不足や未実装の機能に遭遇しても警告を出してスキップするようにし、起動継続を保証。

### Security / Notes
- config_setup によって生成される .env のヘッダに「.env は絶対に Git にコミットしないこと」という注意書きを追加。
- validate_config では本番環境（KABUSYS_ENV=live）向けに LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告する追加チェックを実装。

---

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: 基本的な自動売買システムのコア機能群を実装。
  - 起動スクリプト: run_execution, run_monitoring
  - 設定管理: Settings クラス、.env 自動読み込みロジック
  - 設定ツール: config_setup（ウィザード）、validate_config（検証 CLI）
  - 監視基盤: monitoring DB 初期化、SystemMonitor 起動ループ（stop flag / poll interval）
  - Execution コンポーネントの骨格: BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler（各コンポーネントの実装は別モジュールに分離）
  - ポートフォリオ構築ライブラリ（選定・重み付け・リスク適用・ポジションサイジング）
  - ツール: paper_verification_report（Paper Trading 向け検証レポート）
  - ユーティリティ: logging_setup（統一ロギング設定）、process_priority（優先度 / affinity 設定）
  - DuckDB / SQLite の接続ラッパと利用例を含むデータ分析基盤（ファクター計算用の雛形）

### Changed
- パッケージの初期バージョンを 0.1.0 に設定。

### Fixed
- n/a（初回リリースのため該当なし）

---

注記:
- 上記の変更点は、ソースコードの状態から推測して記載しています。実際のリリース履歴やコミットメッセージがある場合は、それに合わせて調整してください。