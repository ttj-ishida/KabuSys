CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-18
-----------------

Added
- 基本バージョンを追加（__version__ = 0.1.0）。
- 初期起動スクリプト:
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）に記録する仕組みを導入。起動時に停止フラグ (data/stop_requested.flag) の監視と PID ファイル管理 (data/execution.pid) を行う。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する。
- 設定関連ツール:
  - config.py — .env の自動読み込み機構（.env < .env.local、OS 環境変数保護）、プロジェクトルート検出（.git または pyproject.toml）および Settings クラスを導入。多くの設定プロパティ（DB パス、ログレベル、KABUSYS_ENV、PAPER_FILL_MODE 等）とバリデーションを実装。
  - config_setup.py — 対話式 .env 設定ウィザードを追加（python -m kabusys.config_setup）。シークレット入力のマスク、既存 .env の読み込み・編集、保存テンプレートを提供。
  - validate_config.py — 起動前検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数や config/*.yaml の存在・パース（PyYAML 利用時）をチェック、--strict オプションで警告も失敗扱いにできる。
- 運用・ユーティリティ:
  - utils/logging_setup.py — 統一的なログ設定ユーティリティを追加。コンソール（stdout）出力と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）をルートロガーに設定。LOG_DIR 指定や権限エラー時のフォールバック処理を実装。
  - utils/process_priority.py — プロセス優先度（Windows および POSIX の nice）と CPU affinity 設定を行うユーティリティを追加。set_process_priority/set_cpu_affinity を提供。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py — 候補選択（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio/risk_adjustment.py — セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py — 発注株数計算（calc_position_sizes）。risk_based / equal / score の割当方式、単元株丸め（lot_size）、aggregate cap スケーリング、コストバッファ考慮を実装。
- 運用ツール:
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下、レイテンシ（P95 など）を集計して PASS/FAIL 判定を行う。CLI 引数で期間指定・DB パス指定が可能（python -m kabusys.tools.paper_verification_report）。
- research/factor_research.py — ファクター計算モジュール（モメンタム等）の追加（duckdb を用いた prices_daily/raw_financials 参照でファクター計算を想定）。一部実装（モメンタム計算）を含む。

Changed
- .env 読み込みロジックの強化:
  - export KEY=val 形式、クォート（シングル/ダブル）内のエスケープ、インラインコメント処理に対応したパーサを実装。
  - 自動ロードの優先順位を明確化（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - OS 環境変数は protected として .env.local/.env により上書きされないよう保護。
- ログ設定:
  - StreamHandler を stdout に固定（cron/Task Scheduler と相性向上）。
  - ログファイル日次ローテーションを標準化（logs/<app_name>.log、既定 LOG_DIR は logs/）。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- Execution / Monitoring の動作:
  - run_monitoring: MONITOR_POLL_INTERVAL に負の値や 0 を許容しないようバリデーションを追加。値が不正な場合は警告を出してデフォルト 60 秒を使用する。
  - run_execution: paper_trading モード時は paper_sqlite_path を使用し本番 DB と完全分離。起動前に監視テーブルの存在を保証するため init_monitoring_db を呼ぶ（冪等）。
  - run_execution: ExecutionEngine はバックグラウンドスレッドで run_session を実行し、main スレッドで停止フラグを監視して安全停止する論理に変更。
- 設定のバリデーション強化:
  - Settings.paper_fill_mode に有効値検証（instant, partial, never, reject）を追加。
  - Settings.env と Settings.log_level に対する入力検証を厳格化。
- ポートフォリオ計算の改善:
  - calc_score_weights: 全スコアが 0 の場合は等金額配分にフォールバックして警告を出す。
  - apply_sector_cap: "unknown" セクターはセクター上限適用対象外とする。
  - calc_position_sizes: lot_size（単元株）で丸め、cost_buffer による保守的コスト見積り、aggregate cap 超過時のスケールダウンと残余分の優先配分アルゴリズムを実装。
- validate_config: config/*.yaml の存在確認と、PyYAML がない場合はパース検証をスキップして警告を出すよう変更。KABUSYS_ENV=live 時の追加チェック（LINE トークン、KILL_FLAG_CLEAR_ON_START の警告）を追加。

Fixed
- DB 接続のクローズ処理を finally ブロックで行うようにしてリソースリークを防止。
- init_monitoring_db を起動経路で呼び、監視テーブルが存在することを常に保証（冪等）。
- .env パーサの不正な行やコメント処理に起因する設定読み込み誤りを改善。
- process_priority の例外処理を強化し、アクセス権限不足や未サポート OS でも安全にフォールバックするようにした。

Notes / Upgrade
- 新しい CLI:
  - .env の初期作成・編集: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report
- 環境変数の追加／変更点:
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）。
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）。
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。正の整数。未設定または不正値の場合は 60 秒。
  - KILL_FLAG_CLEAR_ON_START: 本番環境で 1 にすると危険（validate_config で警告）。
  - LOG_DIR: ログ出力先（デフォルト: logs/）。
- 運用上の注意:
  - 本番運用（KABUSYS_ENV=live）の場合、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。notify が未設定だとアラートを受け取れません。
  - .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も警告を出します）。
  - ログディレクトリの権限不足等でファイルハンドラが作成できない場合はコンソール出力のみとなります。必要に応じて LOG_DIR の作成と適切な権限設定を行ってください。

Acknowledgements / TODO
- research/factor_research.py の一部（モメンタム計算など）は実装中（継続実装予定）。
- 将来的に position_sizing の lot_size を銘柄別に扱う拡張（stocks マスタに lot_size を追加）を検討済み（コード内に TODO を記載）。
- apply_sector_cap の価格欠損（price が 0）の取り扱い改善（前日終値や取得原価のフォールバックを検討）を今後対応予定。