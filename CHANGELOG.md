# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 以下の履歴はコードベースの内容から推測して作成したものです。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-25

### Added
- 基本アーキテクチャ・実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使って本番 DB と完全に分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する仕様。

- 設定管理・自動読み込み
  - kabusys.config.Settings: 環境変数経由の設定アクセスラッパーを追加。多数のプロパティを提供（J-Quants, kabu API, DB パス, pid/kill フラグパス, 監視閾値, 環境判定メソッド等）。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み。OS 環境変数は保護され、.env.local は .env を上書きする。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- 設定ユーティリティ・検証ツール
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。デフォルト値・選択肢・シークレット入力に対応し、保存前に確認を行う。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML あれば）パース検証等を実施。--strict モードで警告を FAIL 扱いにできる。

- ロギング／プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging(): ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日分保持）を設定するユーティリティを追加。ログレベル・ログディレクトリは環境変数または引数で解決。ログディレクトリ作成に失敗した場合はファイルハンドラを無効化し、コンソール出力のみで継続する。
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX(nice) の差分を吸収し、権限不足や未対応環境では警告を出してスキップする。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates(): BUY シグナルをスコア降順で選定（タイブレーク: signal_rank）。
    - calc_equal_weights(), calc_score_weights(): 等分配・スコア正規化による重み計算（スコア合計が 0 の場合は警告して等分配にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap(): セクター集中上限を評価して候補をフィルタする機能。売却予定銘柄の除外や "unknown" セクターの扱いを明記。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告して 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") に基づいて銘柄ごとの発注株数を計算。単元（lot_size）丸め、1 銘柄上限（max_position_pct）、全体の aggregate cap（available_cash）を考慮。コストバッファを使用した保守的な見積りと、スケールダウン時の残差配分ロジックを実装。

- Research / ファクター計算（基礎）
  - research.factor_research.calc_momentum(): DuckDB の prices_daily を使ったモメンタム系ファクター計算機能（モジュール設計と定数を追加、実装の一部としてモメンタム期間等を定義）。（注: ファイル末尾は途中で切れているため一部未完）

- ツール
  - tools.paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで上書き可）。以下の指標・閾値を用いて PASS/FAIL を判定:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill_rate) >= 90.0%
    - 送信率 (send_rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - レポートは期間指定 (--from/--to) に対応、P95 の計算はサンプルを昇順ソートして index を取る実装。

- データベース関連
  - duckdb と sqlite3 の両方を使用する設計を採用（分析用に DuckDB、監視・履歴は SQLite）。
  - 監視用の init_monitoring_db(sqlite_conn) を呼ぶことで監視テーブルの存在を冪等に保証。

- その他
  - パッケージバージョン: __version__ = "0.1.0"
  - モジュール公開: kabusys.portfolio パッケージの public API を __all__ で整理。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- .env パーサーの堅牢化（_parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、クォートなし値のコメント判定ルールなどを実装し、.env の多様なフォーマットに対応。

- ログ設定の堅牢化
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に安全にフォールバックするロジックを追加。

- プロセス優先度周りの例外対策
  - 権限不足や未実装のメソッドに対して警告を出して落ちないように変更。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues
- research.factor_research モジュールはファイル末尾で切れている（calc_momentum の実装が途中）ため、完全なファクター算出パスは未完成。実運用前に補完が必要。
- position_sizing の price フォールバック（価格欠損時の取り扱い）について TODO コメントあり。price が 0.0 の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価でのフォールバックを推奨。
- run_monitoring と run_execution は stop/kill フラグファイル（data/stop_requested.flag, data/kill.flag）および PID ファイルを用いる運用を前提としている。運用手順（ファイル配置／削除）に注意。

---

参考: 主要な環境変数とデフォルト値（抜粋）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（秒、run_monitoring 用）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（値 1）

以上。必要があれば、リリースノートをより詳細（ファイルごとの変更点や関数仕様の箇条書き）に拡張します。