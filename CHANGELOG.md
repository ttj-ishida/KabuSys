CHANGELOG
=========

すべての注目すべき変更履歴を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに分類しています。
- 日付はリポジトリ内の実装状況から推定した初期リリース日を使用しています。

[Unreleased]
------------

- 今後の変更・修正をここに記載してください。

[0.1.0] - 2026-04-19
-------------------

Added
- 実行用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。起動時にプロセス優先度を "high" に設定し、BrokerClientFactory からブローカークライアントを生成してスレッドで実行する。停止は data/stop_requested.flag によるフラグ検知で行う。paper_trading 環境では専用の paper_trading SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する実装。

- 設定・環境管理
  - config.py: .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）を追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。.env のパースは export プレフィックス、クォート、インラインコメント、エスケープに対応。Settings クラスを介して環境変数をプロパティとして安全に取得できるように実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目や PAPER_FILL_MODE のバリデーションを含む）。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。主要設定項目の説明・デフォルト値・シークレット扱いをサポートし、.env を安全に書き出す機能を提供。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml（存在すれば PyYAML によるパース検証）を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パスの親ディレクトリ存在チェック、KABUSYS_ENV=live 時の追加警告等を実施。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler（stdout を使用）と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみ継続する。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。許可されない環境や権限不足時は警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソート、タイブレークに signal_rank を使用。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックして WARNING を出力）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限をチェックし、上限を超過しているセクターの新規候補を除外（"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を返す。未知レジームは 1.0 にフォールバックして WARNING を出す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて各銘柄の発注株数を計算。lot_size（単元）で丸め、各銘柄上限（max_position_pct）や aggregate cap（available_cash）を尊重。cost_buffer により保守的に約定コストを見積り、合計が available_cash を超える場合はスケールダウンして残差配分ロジックで単元単位の割当てを行う。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（または --db）から DB を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を出力。判定基準（閾値）はソースに定数で定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を run_* スクリプトで呼び出し、監視用テーブルの存在を保証（冪等）。

Changed
- ログ出力先を stdout に統一（StreamHandler は stdout を使用）。cron / Task Scheduler 等で stdout/stderr を一本化する運用に配慮。

Fixed
- 環境変数の読み込み順序を明確化（OS 環境 > .env.local > .env）、OS 環境を保護する protected キーセットを導入して上書き制御。

Known issues / Work in progress
- research/factor_research.py にモメンタムファクター計算の実装開始あり（関数 calc_momentum 等を実装中）。ファイル末尾が途中で切れている（実装未完・WIP の状態）ため、完全なファクター計算は未提供。
- 一部関数に TODO コメントあり（例: apply_sector_cap の price 欠損時のフォールバック戦略、position_sizing の銘柄別 lot_size 対応など）。将来的な改善が想定される。

Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する運用を想定。config_setup.py の出力に「.env は絶対に Git にコミットしないこと」という注意を追加。

Notes / 運用上の挙動（ドキュメント化）
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を制御（不正値または 0 以下はデフォルト 60 秒にフォールバックし警告を出力）。
- run_execution は data/execution.pid を PID ファイルとして扱い、data/stop_requested.flag により停止を制御。起動時に停止フラグが既にある場合は起動を取りやめる。
- PAPER_FILL_MODE（paper trading の約定モード）に対して有効値チェックを実装（instant, partial, never, reject）。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出力する。

----------

この CHANGELOG は、リポジトリ内のソースコード（エントリポイント、ユーティリティ、ポートフォリオ構築ロジック、ツール群）から推測して作成したものです。実際の開発履歴やコミット履歴が存在する場合はそれを優先して差し替えてください。必要であれば各項目をより詳細に分解（例: 個別モジュールごとの変更履歴、関数レベルの修正点）して出力します。どの粒度で記載したいか教えてください。