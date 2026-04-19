Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。
このプロジェクトのバージョンはセマンティックバージョニングに従います。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys 基本機能群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB に切り替え（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を経由して環境に応じたブローカークライアントを生成（コメントで MockBrokerClient を使用する旨明記）。
    - ExecutionEngine をスレッドで実行し、data/execution.pid に PID を書き込みつつ stop flag ファイルで安全に停止可能。
    - RiskManager / Reconciler / OrderManager / OrderRepository 等の組み立てロジックを実装。
- 監視スクリプト
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒、無効値はフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨明記。
    - stop フラグファイル（data/stop_requested.flag）でループ終了。
- 設定管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルートを .git または pyproject.toml で自動検出し、.env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export KEY=... 形式、クォート・エスケープ、インラインコメントに対応する独自の .env パーサを実装。
    - Settings クラスを提供し、各種設定値（J-Quants / kabu API / DB パス / PID / Kill Switch / CPU/MEM/DISK 閾値 / env 判定等）をプロパティで取得可能に。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject）。
- 設定関連ユーティリティ
  - config_setup.py: 対話式 .env ウィザードを追加（.env の作成・更新を支援）。
  - validate_config.py: 設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml 存在と YAML パース確認、live 時の追加ガードなど）。--strict オプションで警告を FAIL 扱いにできる。
- ロギング/プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）をルートロガーに設定するユーティリティを提供。
    - LOG_DIR / LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py:
    - set_process_priority(level) により Windows/Linux/Mac の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity 固定が可能。権限不足等は警告でスキップ。
- Portfolio ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・タイブレークを signal_rank で処理。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全銘柄のスコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用（当日売却予定はエクスポージャー計算から除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジームに応じた資金乗数（bull/neutral/bear）と未知レジーム時のフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株（lot_size）丸め、per-stock/aggregate の上限適用、cost_buffer を考慮したスケーリングと端数配分ロジックを実装。
  - portfolio/__init__.py: 上記関数をエクスポート。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード結果の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し PASS/FAIL を判定。閾値はソース内で定義（例: uptime >= 99% 等）。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH を環境変数で指定可能。
- Research
  - research/factor_research.py:
    - DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA200乖離、ATR、出来高系等の計算方針と定数を定義）。prices_daily / raw_financials テーブルに依存する設計。

Changed
- プロセス起動時の挙動統一
  - 全起動スクリプトが setup_logging() を呼び出し、set_process_priority("high") を最初に行うように設計。これによりログ出力やプロセス優先度設定が一貫。

Fixed
- 環境変数の取り扱いと堅牢性強化
  - MONITOR_POLL_INTERVAL が不正値（0 以下や非整数）の場合に警告しデフォルトへフォールバックする挙動を追加（run_monitoring.py）。
  - .env 読み込み時にファイル読み込み失敗を warnings.warn で通知し続行するようにした（config.py）。
  - logging_setup でログディレクトリ作成失敗時にハンドラ作成をスキップして fallback することで起動失敗を回避。
- DB 初期化
  - run_execution/run_monitoring で起動時に init_monitoring_db を呼び出し（冪等）、monitoring 用テーブルの存在を保証。

Notes / Implementation details
- デフォルトのパス、環境変数、挙動
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH (monitoring): data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - PID ファイル: data/execution.pid 等
  - Kill/Stop フラグ: data/kill.flag, data/stop_requested.flag を用いた外部からの停止制御
  - KILL_FLAG_CLEAR_ON_START による Kill Switch 自動クリアの制御（config のガードに反映）
- 安全設計
  - 本番環境（KABUSYS_ENV=live）では追加の警告チェックを行い、LINE 通知設定や Kill Switch の設定ミスに注意喚起する（validate_config.py）。
  - ログは標準出力（stdout）とファイルに出力する設計で、cron/タスクスケジューラからの運用を想定。

未実装 / TODO（ソース内コメントより）
- position_sizing: 銘柄別の lot_size を stocks マスタから取得する拡張。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）時のフォールバック価格処理（前日終値や取得原価の使用）を検討。
- research/factor_research.py: 関数の続き（calc_momentum 等の実装完了）が必要（ソース末尾が途中で切れている）。

開発者向けメモ
- 自動 .env 読み込みはプロジェクトルートの特定に依存するため、パッケージ配布後や CI 環境で不要な自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベルやファイル出力を明示的に変更したい場合は setup_logging の引数または環境変数 LOG_LEVEL / LOG_DIR を利用してください。

----------