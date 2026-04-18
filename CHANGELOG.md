# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
/Unreleased/ セクションは将来の変更用に予約されています。各リリースは日付付きで記載します。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。プロジェクトの主要機能とユーティリティを実装しました。以下はコードベースから推測してまとめた主な追加・仕様です。

### Added
- 環境設定・読み込み
  - Settings クラスを実装し、環境変数経由で各種設定を提供（J-Quants / kabu API / DB パス / モード判定 等）。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づき .env / .env.local を自動ロードする機能を追加。OS 環境変数を保護して上書き制御を行う。
  - .env パーサー: export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理に対応。

- 対話式環境設定ウィザード
  - `kabusys.config_setup` により .env を対話的に作成・更新する CLI を実装。
  - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）、シークレット項目のマスク表示、デフォルト値・選択肢サポート、および保存処理を実装。
  - 生成される .env ファイルには注意書きを付与（.env を Git にコミットしない旨）し、書式を統一。

- 設定検証ツール
  - `kabusys.validate_config` CLI を実装。必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、本番環境向けガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を行う。
  - `--strict` オプションにより警告も失敗扱いにできる。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを実装。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知時に安全停止する実装。
    - RiskConfig にデフォルトパラメータを設定し、初期 portofolio value を broker.get_available_cash() から取得して利用する。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計。
    - stop flag の検出、例外ハンドリング（check_once() の例外をログ出力して次回ポーリングへ継続）を実装。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`
    - 全起動スクリプト共通のログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR の環境変数を尊重。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`
    - プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows と POSIX（Linux/Mac等）の差分を吸収し、psutil を用いた安全な操作・例外フォールバックを行う。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全ゼロ時に等配分へフォールバックして警告を出す。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用して候補を除外する apply_sector_cap を実装。既存保有と価格マップを参照してセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除去する。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングと未知レジームでのフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック（calc_position_sizes）を実装。allocation_method に応じた計算（risk_based / equal / score）、1銘柄上限、lot_size 整数丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、残余キャッシュでの端数分配ロジック等を提供。

- リサーチ（ファクター計算）枠組み
  - `kabusys.research.factor_research` にモメンタム等のファクター計算の骨組みを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照して各種指標を計算する設計）。（ファイル末尾は一部未完の実装を含む可能性あり）

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からデータを集計し、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを算出してレポート出力する CLI を実装。
    - P95 計算、日付フィルタ（--from/--to）、基準値閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を提供。

- その他
  - パッケージ初期化とバージョン情報を __version__ = "0.1.0" として設定。
  - モジュール構成を整理し、各モジュールをトップレベルにエクスポートする __all__ を設定（portfolio など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- ログディレクトリ作成/ファイルハンドラ作成に失敗した場合でも、コンソールログ（stdout）で継続するようフォールバックを実装。
- .env 読み込みでファイル読み込み失敗時に警告を出して安全に続行する挙動を追加。

### Security
- config_setup においてシークレット項目は入力表示をマスクし、.env への保存時に注意喚起を出力。
- .env を Git にコミットしないよう README/生成ファイルヘッダに明示。

### Notes / Known limitations / TODO
- research.factor_research はファクター計算の骨組みを提供しているが、完全実装（境界ケース処理やパフォーマンス最適化）が未完の箇所がある可能性があります（コード末尾が途中で切れているように見える）。
- position_sizing の価格欠損時（price が 0 or None）に対するフォールバック価格（前日終値や取得原価等）の利用は TODO コメントで示されている。
- process_priority / set_cpu_affinity は権限不足や未対応 OS での失敗を警告してスキップする設計。運用環境でのテストを推奨します。
- monitoring は意図的に KABUSYS_ENV にかかわらず本番 sqlite_path を参照するため、環境分離が必要な場合は実運用での設定に注意してください。

---

（本 CHANGELOG は提示されたコード内容から仕様・変更点を推測して作成しています。実際のリリースノートはリポジトリの履歴や開発者の意図に基づき調整してください。）