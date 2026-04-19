CHANGELOG
=========

すべての日付は YYYY-MM-DD 形式。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: パッケージバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き、停止フラグファイルによる終了検知、プロセス優先度設定、SQLite / DuckDB 接続の初期化を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を分離して使用する仕組み（MockBrokerClient の利用想定）、PID ファイル・停止フラグ対応、スレッドでのエンジン実行・停止処理を実装。
- 設定管理・読み込み
  - src/kabusys/config.py: Settings クラスを導入。.env 自動読み込み機能（プロジェクトルート検出を行い .env / .env.local を適切な優先度で読み込む）、.env 行のパース（クォート・エスケープ・インラインコメント対応）、必須環境変数取得ヘルパーを提供。環境（development/paper_trading/live）・ログレベル・各種パス・Paper Trading 設定などをプロパティで取得可能。
- 設定関連 CLI
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加。既存 .env 読み込み、値のマスク表示、保存前の確認、.env に書き込むテンプレートを実装（.env を絶対にコミットしない旨のヘッダ付与）。
  - src/kabusys/validate_config.py: 起動前チェック用 CLI を追加。必須環境変数の存在、KABUSYS_ENV の妥当性、ログレベル、DB パス親ディレクトリ確認、config/*.yaml の存在確認（PyYAML が無ければパース検査をスキップ）、本番環境向けガードチェックを実装。--strict モードで警告を FAIL 扱いにできる。
- ロギング / 実行環境ユーティリティ
  - src/kabusys/utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を組み合わせ、既存ハンドラのクリア、LOG_DIR/LOG_LEVEL の解決ロジック、フォールバック動作を提供。
  - src/kabusys/utils/process_priority.py: Windows / POSIX に対応したプロセス優先度設定と CPU affinity ユーティリティを追加（psutil 依存）。権限不足や未対応プラットフォームでは警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。全銘柄スコアが 0 の場合のフォールバックも実装。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。unknown セクター扱いの取り扱いなど仕様を明記。
  - src/kabusys/portfolio/position_sizing.py: position sizing の主要ロジックを実装（risk_based / equal / score 対応）。単元株丸め（lot_size）、max_position_pct/aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、スケールダウン後の残余配分アルゴリズムを実装。
  - src/kabusys/portfolio/__init__.py: 上記関数群のエクスポートを提供。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を追加。system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値比較して PASS/FAIL を判定する。P95 計算、日付フィルタ、DB パスの CLI オーバーライド対応を実装。
- DuckDB 統合
  - Execution / Monitoring スクリプトおよび一部モジュールで DuckDB 接続を受け渡す設計（duckdb_conn を使用）。
- 監視 DB 初期化の冪等化
  - init_monitoring_db が呼び出され、必要な監視テーブルが存在することを保証する処理を追加（起動スクリプトから実行）。

Changed
- ログ出力系の仕様
  - StreamHandler を stdout に固定。cron/Task Scheduler 等からの起動時に stdout/stderr を一本化して扱いやすくする意図。
- .env の読み込み挙動
  - OS 環境変数は保護され、.env.local での上書きを許す設計（protected keys による保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Fixed
- 起動時にログディレクトリ作成失敗やファイルハンドラ生成失敗が発生した場合でも、コンソールログのみで安全に継続するようにフォールバックを強化（ログ初期化時の例外ハンドリング改善）。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で例外を握りつぶして安全にスキップするように改善。

Security
- config_setup が生成する .env ヘッダに「.env を絶対に Git にコミットしないこと」を明記。
- Settings._require() により必須トークンが未設定の場合は起動前に明示的にエラーを出すため、誤って空トークンで本番を動かすリスクを低減。

Notes / Known issues
- research/factor_research.py はファクター計算モジュールの実装を開始しているが一部実装が続行中（ファイルの途中で処理が途切れている箇所あり）。本モジュールはまだ WIP（ベータ）として扱うべきです。
- position_sizing の price フォールバックは TODO コメントで明示（価格欠損時の扱いに注意）。
- apply_sector_cap の unknown セクターは上限チェック対象外となる仕様。必要に応じてマスタでの sector マッピング整備を推奨。
- validate_config の YAML パース検査は PyYAML がインストールされている場合のみ実行される。CI 等で厳密に検査する場合は PyYAML を依存に追加すること。

Acknowledgments
- 本 CHANGELOG はソースコードの内容から実装意図を推測して作成しています。実際のリリースノートや履歴管理はコミット履歴・リリース時の changelog 管理ポリシーに従って整備してください。