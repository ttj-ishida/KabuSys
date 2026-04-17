CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys コードベースを追加。
- コア設定/ユーティリティ
  - Settings クラスを追加し、環境変数経由でアプリ設定を提供。
    - 主な環境変数: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE 等。
    - デフォルト値を明示（例: KABU_API_BASE_URL, DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db）。
    - is_live / is_paper / is_dev の簡易判定プロパティを提供。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱い等を実装。
- CLI / ユーティリティ
  - config_setup.py: 対話式ウィザードを追加。.env の初期作成／更新を支援。
    - 質問項目・デフォルト・シークレット扱いをサポート。保存前の確認プロンプトを実装。
    - .env を生成する際のテンプレート（Git に絶対コミットしない旨の注記付き）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、本番向けガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）等。
    - --strict オプションで警告もエラー扱いにできる。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
    - デフォルトの DB パスは data/paper_trading.db。--from/--to/--db オプション対応。
    - Pass/Fail 基準値（稼働率 >=99%、fill >=90%、send >=95%、P95 <=200ms）を実装。
- 実行系（Execution / Broker / Risk）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
    - BrokerClientFactory により環境に応じて実際のブローカーまたは MockBroker を生成する想定。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立て、別スレッドでエンジン実行。stop フラグ検知で安全に停止。
    - RiskManager のデフォルト構成を明示（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
    - execution.pid（PID ファイル）/ stop_requested.flag による起動制御を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視 DB は本番を想定）。
    - SystemMonitor.check_once() を定期呼び出し、例外時はログに例外情報を出力してループ継続。
    - stop_requested.flag 検知でループを終了。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順＋同点は signal_rank 昇順で候補選出。
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 のときは等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別既存エクスポージャーに基づく候補除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた乗数を返す（未知レジームはフォールバックで 1.0、未知時に警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。
    - 単元株（lot_size）で丸め、per-position 上限（max_position_pct）と aggregate 上限（available_cash）を考慮。
    - cost_buffer を使った保守的コスト見積およびスケールダウン、端数処理（残余キャッシュで lot 単位の追加配分）を実装。
    - risk_based における stop_loss_pct / risk_pct に基づく株数算出を実装。
- 研究用 / ファクター計算
  - research.factor_research: DuckDB 接続を受けてファクター（Momentum, Volatility, Liquidity, Value 等）を計算するための基盤関数を追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率等を計算するためのクエリ枠組み（prices_daily テーブル参照）。
    - 日付スキャン幅や窓サイズ等を定数で定義し、データ不足時の None ハンドリングを行う。
- DB / 分析
  - DuckDB を分析用に統合（Settings.duckdb_path）。多くの分析/ファクター計算が DuckDB 接続を前提に記述。
  - 監視系で monitoring_db の初期化ユーティリティ（init_monitoring_db）を参照して利用する設計（冪等にテーブル作成を保証）。
- プロセス制御ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度を設定。権限不足や未対応 OS 時は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に固定するユーティリティ。権限や未対応環境は警告してスキップ。
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。
  - exports を __all__ で整理（data, strategy, execution, monitoring 等）。

Changed
- （初回リリースのため過去変更はなし）

Fixed
- （初回リリースのため過去修正はなし）

Notes / 注意事項
- .env ファイルは機密情報を含むため、README 等にも再掲している通り Git にコミットしないでください。
- run_monitoring は監視用途のため「本番用の SQLite パス」を常に使用する設計になっています。テスト環境で監視 DB を分離したい場合は設定やコードの見直しを推奨します。
- 一部の機能（ブローカークライアント、ExecutionEngine の内部実装、monitoring の DB スキーマ等）はこの変更履歴で参照されるが、実装の詳細は各モジュール（execution.*, monitoring.*）を確認してください。
- PyYAML がインストールされていない場合、validate_config は YAML パース検証をスキップします（警告を出力）。

References
- 主要エントリポイント:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from --to --db]
  - run_execution.py / run_monitoring.py を直接実行してそれぞれのサービスを起動可能。