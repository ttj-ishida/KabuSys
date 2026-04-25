CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-25

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の MockBrokerClient と専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）管理。
    - 実行中は別スレッドで engine.run_session() を起動し、停止フラグ検知で安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検知でループを終了。
- 設定管理 / ユーティリティ
  - config.py: Settings クラスを実装。環境変数の取得・検証を提供。  
    - J-Quants / kabu API / DB パス / monitoring 閾値などのプロパティを提供。  
    - PAPER_FILL_MODE（instant/partial/never/reject）などの検証を行い、不正値は例外を投げる。
    - .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。.env.local を優先ロードし、OS 環境変数は保護される。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。既存 .env 読み込み・マスク入力・デフォルト表示・保存機能を提供。
  - validate_config.py: 設定検証 CLI を実装。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検証）を検査。--strict オプションで警告も FAIL 扱いにできる。
  - utils/logging_setup.py: ログ設定ユーティリティを実装。  
    - stdout (StreamHandler) と日次ローテート（TimedRotatingFileHandler、デフォルト logs/、30日分保持）をルートロガーに設定。  
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト の順で解決。標準出力に出すため stderr ではなく stdout を使用。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを実装。  
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応して set_process_priority("high"|"normal"|"low") を提供。権限不足等は警告を出してスキップ。set_cpu_affinity() でプロセスを最初の N コアに固定可能。
- Portfolio コンポーネント（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定およびウェイト計算関数を追加。select_candidates, calc_equal_weights, calc_score_weights を提供。calc_score_weights は全スコアが 0 の場合に等配分へフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター上限フィルタ apply_sector_cap とレジーム乗数 calc_regime_multiplier を追加。未知レジームはログで警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py: 株数算出ロジック calc_position_sizes を実装。  
    - allocation_method: "risk_based" / "equal" / "score" をサポート。  
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積り、端数配分ロジックを備える。
  - portfolio/__init__.py で主要 API をエクスポート。
- Research / ファクター計算
  - research/factor_research.py: モメンタム等のファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。モメンタム、MA200、ATR、出来高系等を想定した実装方針を反映（ファイルは途中実装状態の可能性あり）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。デフォルト閾値を定義（稼働率 >= 99%, fill >= 90%, send >= 95%, P95 <= 200ms）。コマンドラインで --from/--to 期間指定可能。
- 監視 DB ヘルパ
  - monitoring_db の初期化 util を呼び出して監視テーブルが存在することを保証する箇所を run_* スクリプトから呼び出す（冪等に実行）。

Changed
- ログ設計: ルートロガーの既存ハンドラを一旦クリアしてからハンドラを追加することで二重設定を防止。
- .env 読み込みの挙動: .env と .env.local の読み込み順と OS 環境変数の保護（保護キーは上書きされない）を明確化。
- run_monitoring の挙動: 監視ループは例外保護され、check_once() 呼び出しで例外が発生してもループは継続して次ポーリングまで待機するようにした。

Fixed
- 入力パース: .env パースで export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などを扱うよう改善（config._parse_env_line）。
- ポートフォリオ重み算出: スコアが全て 0 の場合のフォールバックを明示して警告を出すよう修正。

Security
- .env ファイルは生成時にコメントで Git にコミットしない旨を明示（config_setup._write_env）。

Notes / Implementation details
- 環境変数の検証や CLI ツール（config_setup, validate_config）を組み合わせることで、起動前に設定ミスを検出しやすくしている。
- Execution と Monitoring は停止フラグファイル（data/stop_requested.flag）を用いることで外部から安全に停止可能。
- Paper Trading は本番 DB と完全に分離する設計（専用 SQLite を使用）。PAPER_FILL_MODE により MockBroker の約定挙動を制御可能。
- logging_setup はログディレクトリ作成に失敗した場合でもプロセスを止めずにコンソール出力のみで継続する耐障害性を持つ。
- process_priority, cpu_affinity の変更は権限の有無やプラットフォームにより実行されない場合があるが、その場合は警告でスキップする。

開発者向けヒント
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- validate_config の --strict を使うと警告もエラー扱いになり exit code 1 を返すため、CI 等での厳密チェックに便利です。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで残ります。ログ出力先を変更するには環境変数 LOG_DIR を設定するか setup_logging に引数を渡してください。

-----------------------------------------------------------------------------