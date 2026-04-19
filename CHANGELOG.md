# Changelog

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

最新変更は Unreleased セクションに記載し、各リリースごとに日付付きで整理します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中はプロセス優先度を "high" に設定する処理を追加（utils.process_priority を利用）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止するループ制御。
    - PID ファイルを書き込む機能をサポート。
    - ExecutionEngine の起動前に監視テーブルの初期化を呼ぶ（冪等）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を利用する仕様。
    - 停止フラグの検知・例外の捕捉・接続クローズなどを含む安定したポーリングループを実装。

- 設定・環境周り
  - config.py: Settings クラスを導入して環境変数をプロパティ経由で取得する仕組みを追加。
    - J-Quants / kabu API / LINE / DB / 監視閾値 / 環境 (development/paper_trading/live) 等の主要設定をカプセル化。
    - PAPER_FILL_MODE（paper trading の約定モード）や PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の環境変数を解釈。
    - 自動 .env ロード機能（プロジェクトルートを自動検出し `.env` → `.env.local` の順で読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env 読み込みは既存 OS 環境変数を保護するための上書き制御を実装。
  - config_setup.py: .env の対話式ウィザードを追加。
    - 既存 .env の読み込み、対話式入力、シークレットのマスク表示、.env ファイル生成機能を提供。
    - デフォルト値・選択肢を提示し、最終確認後にファイルを保存。

- 検証ツール
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を登録。
    - ログディレクトリの自動作成、作成失敗時はファイル出力をスキップしてコンソール出力のみで続行。
    - ログレベルは関数引数 > 環境変数 LOG_LEVEL > デフォルト INFO の順で解決。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収してカレントプロセスの優先度変更を行う（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対しては警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - 銘柄選定 select_candidates（スコア降順、タイブレークに signal_rank）を追加。
    - 重み計算 calc_equal_weights（等金額）および calc_score_weights（スコア加重、全スコア 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap によるセクター集中制限（既存ポジションを考慮して新規候補を除外）を実装。unknown セクターは免除。
    - calc_regime_multiplier によるレジーム別投下資金乗数（bull/neutral/bear）を実装（未知レジームは警告を出し 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した丸め・集計上限・スケールダウンアルゴリズムを実装。
    - 価格欠損やゼロ価格の扱い、端数配分の再配分ロジックを含む。

- 研究（リサーチ）モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum／Value／Volatility／Liquidity を設計）。
    - DuckDB 接続を受け prices_daily / raw_financials テーブルを参照してファクターを算出する方針を実装（関数設計と定数定義を含む）。

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、API レイテンシ（P95）等を集計して PASS/FAIL 判定を行う。
    - CLI 引数で期間指定（--from/--to）および DB パス指定（--db）に対応。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）で自動判定。

- パッケージ情報
  - __init__.py にてバージョンを定義: __version__ = "0.1.0"

### Changed
- ロギングの設計方針: stdout を主要なコンソール出力先とし、ファイル出力はログディレクトリ作成に成功した場合にのみ有効化するようにした（Task Scheduler / cron 等での取り扱いを考慮）。
- .env 自動ロードの優先順位と保護ロジックを明確化:
  - OS 環境変数 > .env.local (override) > .env（未設定時にのみセット）
  - 自動ロードはプロジェクトルートが検出できない場合はスキップ（パッケージ配布後の安全性向上）。

### Fixed
- 環境変数パースの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、無効行のスキップなどを実装して .env の様々な書式に耐性を持たせた。
- プロセス停止・例外処理の強化:
  - run_monitoring と run_execution において停止フラグ検知時の安全停止、例外発生時のログ出力とループ継続を確実に行うようにした。
- DB 初期化の冪等性:
  - 起動時に監視テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（既に存在する場合も安全）。

### Known issues / Notes
- research/factor_research.py は設計に基づく関数群を含みますが、実際のクエリや全関数実装は DuckDB のスキーマ（prices_daily / raw_financials）に依存します。導入時はテーブルスキーマの整備を行ってください。
- process_priority の一部操作（優先度・CPU affinity 設定）は OS の権限やプラットフォームに依存し、権限不足時には警告を出してスキップします。
- .env ファイルは機密情報を含むため、生成した .env をリポジトリにコミットしないでください（config_setup.py のヘッダーに注意喚起あり）。

---

（この CHANGELOG はコードベースから推測して作成しました。実際のリリースノートはプロダクトのリリースポリシーに応じて調整してください。）