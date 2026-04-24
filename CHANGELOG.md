CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」準拠の形式で、コードベースの内容から推測して作成した変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 起動スクリプトを追加・整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag を監視して行う。check_once() 実行中の例外はキャッチしてログ記録のうえ次回ポーリングまで待機するようになっている。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用し、MockBrokerClient を利用することで本番 DB と分離してペーパートレードを行える。停止フラグ（data/stop_requested.flag）検知時の安全停止と PID ファイル出力に対応している。

- 設定関連ユーティリティ
  - config.py: .env 自動読み込み機能を提供（.env と .env.local の読み込み順序、.env.local は上書き）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。エントリポイントや運用で使う Settings クラスを実装し、各種環境変数（J-Quants、kabu API、DB パス、監視閾値、環境種別など）をプロパティとして提供。PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - config_setup.py: 対話式の .env 作成ウィザードを追加。各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 関連など）を対話的に入力して .env を生成・更新できる。既存値の取り込み・シークレットマスク表示に対応。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ検出、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加警告を実装。--strict オプションで警告をエラー扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。標準出力（stdout）用 StreamHandler と日次ローテートされたファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する。LOG_DIR / LOG_LEVEL の解決順を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows は psutil の優先度クラス、POSIX は nice 値を使用）。CPU affinity を最初の N コアへ固定する set_cpu_affinity も実装。権限不足や未対応プラットフォームでは安全にフォールバックし、警告ログを出す。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順で選択し、同点は signal_rank でタイブレークする実装を追加。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全銘柄のスコア合計が 0 の場合は警告を出して等金額配分にフォールバックする。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を実装。既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。当日売却予定銘柄をエクスポージャー計算から除外するパラメータを受け取る。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各配分方式を実装。損切り率・リスク許容率に基づく株数算出、単元株（lot_size）丸め、1 銘柄上限・集約上限（available_cash）に基づくスケーリング、cost_buffer を使った保守的コスト見積り、スケーリング後の端数分配（remainder ベースで安定した再現性を確保）などを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を指定することでペーパートレード DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 >= 99% 等）に対する PASS/FAIL 判定を出力。コマンドラインで期間フィルタ（--from/--to）や DB パス（--db）を指定可能。DB 内のテーブル不在を安全に扱うための例外ハンドリングを行う。

- 研究モジュールの追加（部分実装）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加。モメンタム・ボラティリティ・バリュー等の指標を DuckDB の prices_daily / raw_financials テーブルから計算する設計（関数 calc_momentum 等の実装開始、営業日ベースのウィンドウ設定や P95 等を想定）。

- パッケージ情報
  - __init__.py: パッケージバージョンを 0.1.0 に設定。エクスポートするサブパッケージリストを定義。

Changed
- DB 周りの扱いの明確化
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録する設計（run_monitoring.py の挙動）。
  - 実行（execution）は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する実装（run_execution.py）。

- ログ出力の振る舞い
  - logging_setup でコンソールには stdout を利用するよう明示（stderr ではない）。ログファイル名は <log_dir>/<app_name>.log（app_name は起動スクリプトが指定）。

Fixed
- 起動時の堅牢性向上
  - init_monitoring_db() を呼び出して監視用テーブルの存在を冪等的に保証（存在しない場合の初期化を行う）。
  - run_monitoring のポーリング間隔取得関数で不正な環境変数値を検出すると警告を出しデフォルトにフォールバックするように改善。
  - run_execution / run_monitoring 共にデータベース接続を finally で閉じるようにしてリソースリークを防止。
  - run_execution のスレッド監視と停止処理で停止フラグに応じた安全停止を実装。

Security
- 環境変数の取り扱い改善
  - config_setup による .env ファイル生成で機密情報（J-Quants トークンや kabu API パスワード）をシークレット扱いにし、画面表示時にマスクする UI を導入。
  - config._load_env_file() では protected set（OS 環境変数）を尊重して、意図せぬ上書きを防ぐ。

Notes / Implementation details
- .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォートありはコメント無視、クォートなしは '#' の前が空白の場合のみコメント扱い）に対応。
- portfolio の複雑なスケーリング処理（aggregate cap と lot_size の兼ね合い）は再現性を保つため残差ソートに安定したサブキー（code）を利用している。
- process_priority は権限不足や未サポート OS の場合に警告を出して安全にスキップする実装。

Acknowledgements
- 本 CHANGELOG はソースコードの実装内容から推測して作成されています。実際のリリースノート作成時は、各コミットや PR の詳細、著者情報、既知の既存問題などを追加してください。