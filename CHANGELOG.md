# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載します。日付はリリース日です。

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）検出でループ終了。Monitoring は環境に関係なく本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレーディング DB（data/paper_trading.db）を使用し、MockBrokerClient を使う想定。停止フラグ・PID 管理・スレッド監視を備える。

- 設定・環境管理機能を追加
  - config.py: 環境変数ラッパ（Settings クラス）を実装。各種設定（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定等）とバリデーションを提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV、LOG_LEVEL の検証。
    - .env 自動ロード機構（プロジェクトルート検出に基づく）。.env と .env.local の読み込み順を実装し、OS 環境変数は保護（上書き回避）。
    - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - config_setup.py: 対話式 .env ウィザードを提供。既存 .env の読み込み・マスク表示・確認・ファイル書き出し（書き出し時にコミットしないよう注意を促すヘッダ）を実装。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリチェック、config/*.yaml 存在チェック（PyYAML 未インストール時はスキップ）や本番環境向けのガードを実装。--strict モードで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを実装。StreamHandler（stdout）と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時のフォールバックと既存ハンドラのクリア処理を備える。ログレベル・ログディレクトリの解決順を明示。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度（および CPU affinity）設定ユーティリティ。Windows と POSIX（Linux/Mac 等）に対応し、設定失敗時は警告を出してスキップする安全設計。

- ポートフォリオ構築関連モジュールを追加（純粋関数で DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は警告を出して等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。セクター未定義は "unknown" 扱いで上限適用を行わない。未知レジームはフォールバックして 1.0。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）をサポートし、lot_size（単元）丸め、1銘柄上限や aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（コスト保守見積）に基づくスケールダウンアルゴリズムを実装。

- 分析・検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレーディング検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を集計し、閾値に基づく PASS/FAIL 判定を行う。P95 算出ロジック、期間フィルタ（--from / --to）および DB パスの CLI/環境変数 (--db / PAPER_TRADING_SQLITE_PATH) サポートを実装。デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- 研究用ファクター計算モジュールを追加（実装開始）
  - research/factor_research.py: モメンタム等のファクター計算を行うモジュールを追加。DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照して 1M/3M/6M リターンや MA200 乖離などを計算する設計方針。注: ファイル末尾が実装中で一部未完（実装継続予定）。

### Changed
- 全体設計
  - 起動スクリプト（monitoring / execution）が共通ユーティリティ（logging_setup, process_priority, Settings）を利用するよう統一。プロセス優先度を起動直後に High に設定するフローを導入。
  - ログ出力は stdout を標準に使用（stderr ではない）。これはタスクスケジューラや cron でのリダイレクト運用を意識した設計。

- .env 読み込みの振る舞いを明確化
  - .env のパースロジック（config._parse_env_line）で export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォートなしの場合のみ '#' をコメントとして扱う条件）を実装。上書きポリシー（.env.local は .env を上書き、OS 環境変数は保護）を定義。

### Fixed
- 環境値の安全性向上・バリデーション強化
  - Settings および validate_config において、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の妥当性チェックを追加。無効値時に早期に検出して明瞭なエラーメッセージを出すようにした。

- 起動時の DB 初期化整合性
  - run_monitoring.py / run_execution.py 内で monitoring 用テーブルの存在を保証するため init_monitoring_db() を呼び出す（冪等）。Paper trading 用の DB は本番 DB と分離して使用するよう修正。

### Notes / Known issues
- research/factor_research.py はモメンタム関連の実装が入っているが、ファイル末尾が切れている／実装継続中の箇所が存在します。追加実装およびテストが必要です。
- 一部のユーティリティ（process_priority.set_cpu_affinity 等）はプラットフォーム依存の API を利用するため、権限不足や未サポート環境では警告を出して機能をスキップします。運用環境での事前確認を推奨します。
- Paper Trading の検証レポートは DB スキーマ（system_status, trade_logs, risk_logs 等）に依存します。古い/欠損スキーマでは一部集計が N/A となる点に注意してください。

もしリリースノートに追記したい細かい変更点（例えば各関数の引数変更、エラー修正、テスト追加など）があれば教えてください。必要に応じてセクションを分割して詳細化します。