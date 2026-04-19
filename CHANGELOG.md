# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースのスナップショット作成日（推定）を使用しています。

## [Unreleased]
- なし（現状のスナップショットはバージョン 0.1.0 を示しています）

## [0.1.0] - 2026-04-19

### Added
- 基本的な自動売買システム「KabuSys」を初期リリース
  - パッケージ version: `0.1.0` （src/kabusys/__init__.py）
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB 初期化を行い、停止フラグの検出で安全にループを終了（src/kabusys/run_monitoring.py）。
  - run_execution: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用 DB を使用し MockBrokerClient 経由で分離された運用が可能（src/kabusys/run_execution.py）。
- 設定管理
  - Settings クラスを実装（環境変数読み取り／検証、デフォルト値、便利プロパティ: is_live/is_paper/is_dev、DB パス、PID/kill flag パス等）facilitates centralised configuration（src/kabusys/config.py）。
  - .env 自動ロード機能を実装（プロジェクトルート検出、.env/.env.local 読み込み、OS 環境変数保護対応）。
  - PAPER_FILL_MODE の検証（有効値チェック）や PAPER_TRADING_SQLITE_PATH 等のプロパティを追加。
- 設定周りの CLI
  - config_setup: 対話式ウィザードで .env を作成・更新するツールを追加（src/kabusys/config_setup.py）。既存値の再利用、シークレットマスク、保存前の確認などを備える。
  - validate_config: 起動前に .env と config/*.yaml を検査する CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性チェック、PyYAML があれば config ファイルのパース検証、--strict オプションによる警告を FAIL 扱いにする機能（src/kabusys/validate_config.py）。
- ログ & プロセス制御ユーティリティ
  - logging_setup: stdout に出す StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ自動作成・失敗時のフォールバック、LOG_LEVEL/LOG_DIR の解決順を実装（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows/Linux/macOS を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティを追加（psutil ベース）。権限不足等は警告でスキップ（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定、等金額配分、スコア加重配分（フォールバック時の警告）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数(calc_regime_multiplier) を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: リスクベース／等配分／スコア配分に基づく発注株数決定ロジック（単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮など）を実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- Paper Trading 向けレポート
  - tools/paper_verification_report: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計して PASS/FAIL 判定する検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
- DB 関連
  - run_* スクリプトで DuckDB と SQLite を併用する設計を採用（分析用に DuckDB、監視・履歴に SQLite）。
  - 監視 DB の初期化ユーティリティ呼び出し（init_monitoring_db）を Runner で保証（冪等な初期化）。
- Research（初期実装）
  - research/factor_research.py の骨格を追加（モメンタム・MA200・ATR・流動性等のファクター計算設計、DuckDB 接続により prices_daily/raw_financials を参照する方針）。一部関数実装が始まっているが、ファイル末尾で未完了の箇所が存在（src/kabusys/research/factor_research.py）。

### Changed
- 監視（monitoring）動作の決定: run_monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用するよう明記（監視は環境に依存させない設計）（src/kabusys/run_monitoring.py）。
- logging_setup:
  - StreamHandler を stdout に出力するように仕様化（cron 等で stdout/stderr をリダイレクトする用途を想定）（src/kabusys/utils/logging_setup.py）。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重設定を防止。
- .env パーサの改善（config.py）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、保護対象 OS 環境変数の上書き防止など、実用的な .env 読み込みロジックを実装（src/kabusys/config.py）。

### Fixed
- 起動時の安全性向上
  - run_execution/run_monitoring が停止フラグ（data/stop_requested.flag）や既存のフラグを検出して安全に起動／終了する動作を追加（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。
  - run_execution の場合、ペーパートレード時に本番 DB と完全分離する（paper_sqlite_path を使用）ことでテスト時の混入リスクを低減（src/kabusys/run_execution.py）。
- position_sizing での端数処理や aggregate cap のスケールダウン処理、lot_size（単元株数）を考慮した安全な丸めロジックを実装し、過度の注文発行を防止（src/kabusys/portfolio/position_sizing.py）。
- process_priority / set_cpu_affinity:
  - 未対応 OS や権限不足時にスキップして警告を出すように変更。Windows/Linux/macOS 向けのデフォルトマッピングを実装し、エラーによる起動失敗を回避（src/kabusys/utils/process_priority.py）。

### Documentation / Examples
- config_setup が生成する .env テンプレートにコメントとセクションを追加。Git へコミットすべきでない旨を明記（src/kabusys/config_setup.py）。
- 各モジュールに docstring と使用例コメントを追加し、用途・引数・戻り値の説明を充実。

### Known issues / Notes
- research/factor_research.py の calc_momentum 実装が途中で切れている（ファイル末尾に途中の記述あり）。ファクター計算の完全実装は次リリースで継続予定。
- 一部の TODO コメントが残っており（例: price のフォールバック、lot_size の銘柄別対応など）、将来的な拡張ポイントとして残っている。
- パッケージはいくつかの外部依存 (psutil, duckdb, sqlite3, PyYAML(オプション)) を利用するため、環境に応じたインストールが必要。

---

注: 上記はソースコードの内容とコメントから推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。