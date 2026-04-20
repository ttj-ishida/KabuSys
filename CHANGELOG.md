CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。
意味のある変更（追加・変更・修正など）が行われた場合に更新してください。

Unreleased
----------

- なし

0.1.0 - 2026-04-20
------------------

Added
- 初期リリース: KabuSys v0.1.0 を公開。
- 実行用エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）に完全分離して記録する。
    - 実行中の停止制御に data/stop_requested.flag を利用。実行 PID を data/execution.pid に記録。
    - スレッドでエンジンをデーモン実行し、停止フラグで安全停止を試みる実装。
- 監視用エントリポイント:
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は環境設定に関わらず本番用の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理:
  - config.py:
    - .env 自動読み込み機能を追加（プロジェクトルートの .env, .env.local）。OS 環境変数は保護され上書きされない。
    - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 複雑な .env のパースをサポート（export プレフィックス、クォート・エスケープ、インラインコメント等）。
    - Settings クラスを提供し、各種設定値（API トークン、DB パス、PID ファイル、各種閾値、環境種別など）をプロパティ経由で取得可能。
    - PAPER_FILL_MODE の妥当性チェックおよび Paper Trading 用 sqlite パスの設定を追加。
- 設定ユーティリティ/CLI:
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話的に設定・保存可能。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純関数群）:
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート（score 降順、同点時 signal_rank）と上位 N 抽出を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックを実装。既存保有を考慮して新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各割当方式に対応した株数決定ロジックを実装。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer（手数料/スリッページ見積）考慮などを実装。
- ユーティリティ:
  - utils/logging_setup.py:
    - 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - ログレベル、ログディレクトリは引数・環境変数・デフォルトの順で解決。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。
  - utils/process_priority.py:
    - プロセス優先度と CPU affinity の設定ユーティリティを追加。Windows/Linux/macOS に対して適切にフォールバック。
    - 標準的なレベル（high/normal/low）をサポート。権限不足等は警告でスキップ。
- ツール:
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。SQLite（Paper Trading DB）を読み込み、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究モジュール（計算基盤）:
  - research/factor_research.py（骨子を追加）:
    - モメンタム・ボラティリティ・流動性・バリュー等のファクター計算設計を追加。DuckDB の prices_daily / raw_financials を利用する設計方針を明記。
    - モメンタム計算の定数（1M/3M/6M、MA200 等）とインターフェースの骨格を実装（実装途中の箇所あり）。

Changed
- N/A（初期リリースのため履歴なし）。

Fixed
- N/A（初期リリースのため履歴なし）。

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数や機密項目（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env で管理し .env を絶対に Git にコミットしない旨をドキュメント（.env ヘッダ）に明記。

Notes / Known limitations
- research/factor_research.py はファクター計算の骨子を備えていますが、一部実装が途中です。将来的な完成とテストが必要です。
- portfolio.position_sizing の lot_size は現状すべての銘柄で共通の単位（例: 100）を想定しています。将来的に銘柄別単元対応（lot_map）を検討しています（TODO コメントあり）。
- apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーを過小見積もりする可能性があるため、前日終値や取得原価でのフォールバックを将来的に検討しています（TODO コメントあり）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に処理をスキップしログで警告します。
- .env 自動ロード処理はプロジェクトルートの検出（.git または pyproject.toml）に依存します。配布環境でプロジェクトルートが見つからない場合は自動ロードをスキップします。

開発者向けメモ
- .env の自動読み込みをテスト時に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能です。
- 実運用では KABUSYS_ENV を正しく設定し（development|paper_trading|live）、validate_config.py で事前検証を行うことを強く推奨します。