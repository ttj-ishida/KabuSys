CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行ループを実装。
    - 停止フラグファイル（data/stop_requested.flag）検知により安全に停止する仕組みを備える。実行 PID ファイルを data/execution.pid に書き出し管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒、無効値はデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して監視テーブルを記録。
    - 停止フラグでループを終了する仕組みを実装。
- 設定関連
  - config.py: 環境変数と .env 自動ロード機構を追加。
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づいて .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 複雑な .env 行のパース (export 対応、クォートとバックスラッシュエスケープ処理、インラインコメント処理) を実装。
    - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API、DB パス、Paper Trading モード、監視しきい値等）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）や KABUSYS_ENV の妥当性チェックを実装。
  - config_setup.py: .env 初期作成・対話ウィザードを実装。
    - 対話形式で主要環境変数を作成・更新可能。既存 .env の読み込み・デフォルト提示・シークレットマスク表示に対応。
    - 書き出し時に .env ファイルヘッダーを付与し、Git にコミットしない旨の注意を書き込む。
  - validate_config.py: 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live の場合に本番特有の注意（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を出力。
- 監視（Monitoring）
  - monitoring_db.init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。
  - run_monitoring が SQLite および DuckDB を開いて SystemMonitor を初期化するフローを提供。
- utils
  - process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(N) で最初の N コアにプロセスを固定（未指定時は無変更）。
    - 権限不足や未サポート環境では警告を出して安全にフォールバック。
  - utils パッケージ基盤を追加。
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定および重み算出関数を追加。
    - select_candidates: スコア降順・タイブレークに signal_rank を用いる候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア0のとき等配分にフォールバック）を実装。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有時価ベース）と候補フィルタ機能。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知はフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づいて発注株数を計算。
    - 単元株単位（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリングと残余配分ロジックを実装。
    - cost_buffer によりスリッページ等を考慮した保守的見積もりを行う。
- 研究用ファクター計算
  - research.factor_research: DuckDB 接続を使ったファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、MA200乖離の計算（prices_daily を参照）。
    - calc_volatility: ATR20、相対 ATR、20日平均出来高、出来高比率等の計算（prices_daily を参照）。
    - 大量データ処理のため DuckDB を前提に SQL + Python で実装。
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数を算出。
    - Pass/Fail 基準（稼働率 99%、成立率 90%、送信率 95%、P95レイテンシ 200ms）に基づく総合判定を出力。
- パッケージ初期化
  - __init__.py にて __version__ を "0.1.0" に設定し、公開 API の一部（data/strategy/execution/monitoring）を __all__ に定義。

Notes / 注意事項
- デフォルトの DB パス・各種環境変数は Settings クラスのプロパティで管理され、.env/.env.local により上書きされます。機密情報（API トークン等）は .env に保存し、Git 管理対象から除外してください。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようと試みますが、権限がない場合は警告が出てフォールバックします。
- Paper Trading と Live はデータと振る舞いが分離されています（paper_trading 用 DB、MockBrokerClient の挙動制御など）。
- レジームやリスク設定のデフォルト値（RiskConfig 等）はコード内でハードコードされています。運用時は適宜調整してください。
- config_setup.py / validate_config.py を使って環境構築と事前検証を行うことを推奨します（特に本番運用前）。

Acknowledgements
- 本プロジェクトは DuckDB / SQLite / psutil 等のライブラリを利用します。機能の一部（YAML 検証など）は optional な依存関係に依存します（PyYAML がない場合は YAML 内容検証はスキップされます）。

-- end of changelog --