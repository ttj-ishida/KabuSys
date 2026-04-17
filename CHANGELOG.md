CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys パッケージを追加（__version__ = 0.1.0）。
- 環境設定 / ロード
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応。
  - .env パーサーを実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを考慮した堅牢なパース。
  - Settings クラスを追加し、環境変数経由で設定値を取得（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境フラグなど）。
  - OS 環境変数を保護して .env.local を上書き可能にする実装。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。既存値の読み込み・マスク表示・保存確認あり。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML が存在すれば YAML のパース検証を実施。--strict オプションで警告を FAIL 扱いに可能。

- 実行/監視スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を利用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを取得。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動（スレッド実行、停止フラグ監視、PID ファイル管理）。
    - RiskManager にデフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値はブローカーの get_available_cash() を参照。
  - run_monitoring: SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。0 以下や不正な値はログ警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB 初期化を実行）。
    - stop フラグファイル（data/stop_requested.flag）存在時に優雅にループを終了。
  - 両スクリプトでプロセス優先度を最初に High に設定（utils の set_process_priority を使用）。

- 監視/データベースユーティリティ
  - monitoring_db.init_monitoring_db 呼び出しを両スクリプトで行い、監視テーブルの存在を保証（冪等処理）。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows と POSIX の差分吸収）。CPU affinity を最初の N コアに固定する関数も提供。権限不足等では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順/タイブレークで整列して上位 N を選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供。全スコアが 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用して候補を除外（売却予定銘柄を除外して既存エクスポージャーを計算）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは警告を出し 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて銘柄ごとの発注株数を決定。lot_size（単元）で丸め、per-stock 上限や aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的見積りを実装。価格欠損時のスキップや、将来の lot_map 拡張を示す TODO を含む。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離率を DuckDB の prices_daily から計算。データ不足銘柄は None を返す。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率等を計算するフレームワークを実装（SQL ウェアハウス的に DuckDB を利用）。欠損値伝播・ウィンドウ集計を考慮した実装。
    - 計算に用いるウィンドウ長やスキャン範囲の定数化（例: MA200, ATR_DAYS 等）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH/--db で DB を指定可能。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。閾値定義と PASS/FAIL 判定ロジックを含む。
    - P95 算出、日付フィルタ（from/to）サポート、DB 存在チェックと欠損テーブルへの耐性（OperationalError を捕捉してデフォルト値にフォールバック）。

Changed
- （初版のため該当なし）

Fixed
- .env 読み込みでファイル読み取り失敗時の警告出力を追加（warnings.warn）。
- .env パースの堅牢化（上記参照）。

Security
- .env ファイルに関する注意書きを config_setup の生成ファイルヘッダに追加（".env は絶対に Git にコミットしないこと"）。

Notes / Known limitations
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map を想定する TODO）。
- risk_adjustment.apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性あり（TODO コメントあり）。
- research.factor_research は DuckDB 上の prices_daily / raw_financials テーブル前提。環境によりデータ準備が必要。
- 一部モジュール（実際の ExecutionEngine / BrokerClient 等）は外部コンポーネントに依存（モック実装や外部ライブラリの組み合わせで動作確認が必要）。

Authors
- KabuSys 開発チーム（コード内モジュール群の初期実装）

References
- README / Documentation: 各モジュール内の docstring を参照してください（config_setup、validate_config、tools/*、portfolio/*、research/* 等）。