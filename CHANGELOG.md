# CHANGELOG

すべての重大な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はセクションごとに分けています（Added / Changed / Fixed / Removed / Security）。
- 日付はリリース日です。

## [Unreleased]
- 次回リリース用の変更点はここに記載します。

## [0.1.0] - 2026-04-17
初回リリース（初版機能セット）。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 環境変数・設定関連
  - Settings クラスを追加し、環境変数経由で各種設定を取得可能に。
  - .env 自動読み込み機能を追加（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
  - 自動読み込み順序: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を実装。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
  - 必須/オプション設定と各種プロパティ（DBパス、PIDファイル、監視閾値、KABUSYS_ENV 等）を実装。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
  - 環境種別判定プロパティ（is_live / is_paper / is_dev）を実装。

- 設定支援 CLI
  - 対話式 .env 作成・更新ウィザード（`kabusys.config_setup`）を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* など）。
    - 秘密項目はマスク表示。既存 .env の読み込みと Enter による既存値再利用に対応。
    - 保存時のテンプレート出力（.env 書き込み）を実装。
  - 設定検証 CLI（`kabusys.validate_config`）を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DBパスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）。
    - 本番環境（KABUSYS_ENV=live）向けの追加警告（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行/監視ランナー
  - run_execution スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper trading モード時は Paper 専用 SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - デーモンスレッドでエンジンを実行し、data/stop_requested.flag の検出で安全に停止する仕組みを実装。PID ファイル管理。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を導入。initial_portfolio_value を broker.get_available_cash() で初期化。

  - run_monitoring スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視ループは MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔を調整可能。0 以下や不正な値はデフォルトにフォールバックして警告を出力。
    - Monitoring は実行環境に関わらず本番 sqlite_path を使用する設計（監視情報は本番 DB に記録）。
    - stop フラグ（data/stop_requested.flag）を検知してループを終了。例外発生時はログに出しつつ次のポーリングへ継続。
    - sqlite3 / duckdb 接続の初期化とクローズ処理を実装。`init_monitoring_db` を呼び出して監視テーブルの存在を保証。

- 監視 DB 初期化
  - `init_monitoring_db` を各スクリプトで呼び出し、監視用テーブルが存在することを冪等的に保証。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有を考慮したセクター集中度チェックと候補除外（"unknown" セクターはセクター上限を適用しない）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（デフォルトフォールバックあり）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。リスクベースでの株数算出、単元（lot_size）丸め、1銘柄上限・総投下上限（aggregate cap）の適用、コストバッファ考慮、スケーリングと残差処理アルゴリズムを実装。

- 研究用ファクター計算
  - research.factor_research モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離率の計算（DuckDB の prices_daily テーブルを参照）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率など（DuckDB を使用）。データ不足時の None 処理あり。
    - 計算用の期間定数やスキャン範囲の設定を実装。

- ツール
  - tools.paper_verification_report を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、システム安定性、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して検証レポートを出力。
    - Pass/Fail 判定基準を組み込み（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - 日付フィルタ（--from / --to）対応、P95 計算実装。

- ユーティリティ
  - utils.process_priority を追加。
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン留め（未対応・権限不足時は警告してスキップ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

作成した CHANGELOG はコードベースの実装から推測して記載しています。実際のリリースノート用途には開発チームの確認・追記を推奨します。