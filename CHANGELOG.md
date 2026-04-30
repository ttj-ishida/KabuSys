CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

## [0.1.0] - 2026-04-30

### Added
- 新しい CLI / エントリーポイントを多数追加
  - run_execution.py: ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を専用 DB として利用（本番 DB と完全に分離）。
    - 起動時にブローカーから利用可能資金とポジション評価額を取得して総資産を算出。
    - 起動時のリコンシリエーションと Execution Startup Summary（生成・保存）を実行。
    - 実行はデーモンスレッドで行い、停止フラグ（data/stop_requested.flag）により安全に停止可能。
    - 起動時に execution.pid を作成。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 監視プロセス用に monitoring.pid を作成。停止フラグでループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
  - run_intraday_monitor.py: ザラ場中簡易監視 CLI（単発/監視モード）を追加。  
    - 実行・監視プロセス、Kill Switch、ドローダウン、注文エラー・滞留注文などをまとめて表示。watch モードで定期更新。
  - run_signal_queue_report.py, run_position_reconciliation_report.py, run_pre_market_report.py, run_market_close_report.py, run_performance_report.py: 各種レポート生成 CLI を追加。  
    - 日付・保存・JSON 出力・watch モード等のオプションを提供。
    - DuckDB / SQLite を読み取り専用で接続するフローを採用（該当箇所）。
  - tools/paper_verification_report.py: ペーパートレーディング検証レポート生成スクリプトを追加。稼働率・注文成功率・レイテンシ（P95 など）を算出する機能を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。秘密情報はマスク表示。既存 .env の読み込みと更新に対応。
  - validate_config.py: 起動前の設定検証ツールを追加（必須環境変数・YAML ファイルの存在/パース・本番用チェック等）。--strict オプションで警告を FAIL 扱いに可能。

- 設定/環境管理
  - config.py を追加・整理。以下を提供:
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）に基づく .env 自動ロード（.env, .env.local）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env の自動ロードは OS 環境変数を保護（既存キーは上書きしない / .env.local は上書き可能だが保護対象は除外）。
    - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB / 監視閾値 / PID / Kill Flag 等のプロパティを型安全に取得可能。
    - PAPER_FILL_MODE（instant|partial|never|reject）の検証、PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）のサポート。
    - 環境（development / paper_trading / live）やログレベルの検証ロジックを内蔵。

- 監視・DB 初期化
  - monitoring 用 DB の初期化を行う init_monitoring_db 呼び出しを各プロセスで保証（冪等に監視テーブルを作成）。

- ロギング / プロセス優先度
  - 多数の起動スクリプトで共通の logging 設定と set_process_priority("high") を導入し、起動直後にプロセス優先度を上げるように統一。

### Changed
- レポート／CLI の振る舞いを明確化
  - 各種 CLI が標準化された引数（--date, --save, --json, --watch, --interval 等）を持つように整理。
  - DuckDB は読み取り専用で接続する方針を採用する部分が増加（誤操作でのデータ破壊を防止）。
  - SQLite への接続では URI モード（mode=ro）や親ディレクトリ存在チェックなど、より堅牢な接続処理に変更。

- Exit code（終了コード）ルールを明確化
  - レポート系 CLI はレポート結果に応じた終了コードを返すように統一（例: Signal Queue READY -> 0 / READY 以外 -> 1、Position Reconciliation で差異検出 -> 1、Market Close BLOCKED -> 1 等）。

### Fixed
- .env のパース・読み込みの堅牢化
  - export プレフィックス、クォート文字内のバックスラッシュエスケープ、クォートなし行のインラインコメント扱い等、現実の .env ファイルで発生しうるケースに対応。

- risk_config.yaml の読み込みと検証ロジックを強化
  - 型キャストと必須キーチェック、各パラメータの範囲チェック（比率は (0,1]、整数閾値は >=1 など）を実装。誤設定時に明示的なエラーメッセージを返すよう改善。

- 起動/停止の安全停止フロー
  - execution / monitoring プロセスで stop_requested.flag を監視して安全にシャットダウンする処理を追加。
  - PID ファイルの作成・削除を統一的に扱い、強制終了後のクリーンアップを考慮。

- Intraday モニタの表示改善
  - ステータス判定ロジックと CLI 表示（絵文字、閾値表示、詳細メッセージ）を追加し、運用時の視認性を向上。

### Security
- .env ファイルの取扱いに関する注意書きを config_setup で明示（.env を Git に絶対コミットしない旨を記載）。

### Internal / Refactor
- 共通ユーティリティの活用
  - logging_setup, process_priority 等のユーティリティを各スクリプトで共通利用するように整理。
- パッケージバージョン
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

### Removed
- 特に削除はなし。

注記
- この CHANGELOG はリポジトリ内のスクリプト・モジュールの実装内容から推測して作成しています。実際のコミット履歴や設計意図に基づく正式な変更履歴は、Git のコミットログやリリースノートを参照してください。