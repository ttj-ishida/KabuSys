CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

現在のバージョン: 0.1.0
リリース日: 2026-04-18

Unreleased
---------

（なし）

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーションとユーティリティ群を初回リリースとして導入。
  - パッケージ `kabusys` の初期バージョン（__version__ = 0.1.0）。
- 実行・監視用の起動スクリプトを追加。
  - run_execution.py: ExecutionEngine を起動するスクリプトを提供。KABUSYS_ENV に応じて paper_trading 用のモックブローカーを使用可能。別 DB（data/paper_trading.db）で本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知で安全に停止。
- 環境設定関連の CLI を追加。
  - config_setup.py: 対話式ウィザードで .env を生成・更新するユーティリティを提供。機密項目はマスク表示。
  - validate_config.py: .env や config/*.yaml の起動前検証 CLI を提供。--strict オプションで警告を失敗扱いにできる。
- 環境変数読み込みロジックを実装。
  - 自動 .env ロード（優先順: OS 環境 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースは `export KEY=val`、クォート値、インラインコメントなどに対応。
  - _require() による必須環境変数チェックを提供。
- ロギングユーティリティを追加。
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度 / CPU affinity ユーティリティを追加。
  - utils/process_priority.py: set_process_priority(level)、set_cpu_affinity(cpu_count) を実装。Windows / POSIX の差分を吸収し、許可がない場合は警告出力にフォールバック。
- ポートフォリオ生成とリスク調整の純粋関数群を追加（メモリ内計算）。
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア重み (calc_score_weights) を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: apply_sector_cap（セクター集中排除）、calc_regime_multiplier（レジーム乗数）を実装。未知レジームや unknown セクターの扱いにフォールバック動作あり。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出ロジックを実装（risk_based / equal / score）。lot_size 単位の丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りなどを含む。
- 研究用ファクタ計算モジュールを追加（実装途中のエントリポイントあり）。
  - research/factor_research.py: DuckDB 接続を用いたモメンタム等のファクター計算を意図した実装。設計方針と定数を定義（価格テーブル参照前提）。
- Paper Trading 検証レポートのツールを追加。
  - tools/paper_verification_report.py: ペーパートレード用 SQLite から各種指標（稼働率、注文成立率、送信率、レイテンシ P95 等）を集計してレポート出力。閾値を定義し PASS/FAIL の判定を行う。--from / --to / --db オプションをサポート。
- モニタリング DB 初期化ユーティリティをプロジェクト内で使用（init_monitoring_db の呼び出し）。
- PID / stop / kill フラグの取り扱いを導入。
  - 実行エンジンは PID ファイルを使用し、data/stop_requested.flag の有無で安全に停止できる。

Changed
- run_execution/run_monitoring の設計上の挙動を明確化:
  - 監視側は KABUSYS_ENV にかかわらず production の sqlite_path を使用する（監視データは共通に取得したい設計意図）。
  - 実行側は paper_trading であれば paper_sqlite_path を使用して発注履歴を本番 DB から分離。
- ログ出力は stdout を使用（stderr ではない）ことで、cron/Task Scheduler 等でのリダイレクト運用を考慮。
- .env 読み込みの上書きルールを明確化（.env.local は OS 環境を保護して上書き可）。

Fixed
- 複数の堅牢性向上（入力チェック・フォールバック）を追加:
  - MONITOR_POLL_INTERVAL: 不正値（非整数または 0 以下）はデフォルト 60 秒にフォールバックし、警告をログに出す。
  - PAPER_FILL_MODE: 無効な値が設定された場合は ValueError を送出して早期に気付けるようにした。
  - LOG_LEVEL / KABUSYS_ENV の環境変数検証を追加（有効値外はエラー / 例外）。
  - validate_config: PyYAML がない場合は YAML 検証をスキップして警告出力する（起動に耐える）。
  - paper_verification_report: 対象テーブルが存在しない場合に sqlite3.OperationalError をキャッチして N/A 等で扱うようにし、レポート生成時にクラッシュしないようにした。
  - position_sizing: price が欠損または 0 の場合に無視する安全処理を追加。
  - risk_adjustment: unknown セクターはセクター上限チェックの対象外にする（除外しない）。

Security
- .env に関する注意を README 相当の出力に組み込み（config_setup が .env を生成する際に「絶対に Git にコミットしないこと」を明記）。

Notes / Migration
- 環境自動ロード: デフォルトでプロジェクトルート（.git または pyproject.toml）にある .env/.env.local を起動時に自動ロードします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境での影響に注意）。
- .env の構文サポートを拡張したため、既存の .env にクォートや export キーワードを使っている場合でも正しく読み込まれます。
- ロギングは既定で logs/<app_name>.log に日次ロールされます。ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります。
- paper_trading を利用する場合、発注履歴はデフォルトで data/paper_trading.db に保存され、本番監視 DB（data/monitoring.db など）とは分離されます。

Removed / Deprecated
- なし（初回リリース）。

開発者向けメモ
- 実行・監視プロセスは stop/kill フラグ（data/stop_requested.flag / data/kill.flag など）を用いて外部から安全に停止させる設計です。運用時の kill フラグの扱い（自動クリアの有効化）は本番環境では注意が必要（KILL_FLAG_CLEAR_ON_START）。
- process_priority と CPU affinity の適用は権限や OS に依存します。アクセス許可がない場合は警告を出してスキップします。

以上。README やドキュメント（PortfolioConstruction.md / StrategyModel.md 等）と合わせて本 CHANGELOG を参照してください。