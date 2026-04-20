# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: 本 CHANGELOG はソースコードの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期リリース。本プロジェクトは日本株自動売買システム「KabuSys」として基本的な実行・監視・設定ツール群、ポートフォリオ構成ロジック、リサーチユーティリティなどを提供します。

- 設定・起動系
  - 環境変数読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の読み込みは OS 環境変数を保護（protected）して上書きの制御が可能。
    - 多数のプロパティを通じて設定値を取得（J-Quants トークン、kabu API パスワード、DB パス、各種しきい値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話形式で .env を作成・更新し、秘密項目はマスク表示。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの存在確認、config/*.yaml の存在とパース（PyYAML がある場合）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを構築。OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine を起動。
    - 起動時にプロセス優先度を高く設定（set_process_priority("high")）。
    - 停止フラグ（data/stop_requested.flag）を検知してセッションを安全に停止。
    - 実行 PID を data/execution.pid に記録する仕組みを使用（pid_file 引数）。
  - SystemMonitor ポーリング実行スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - duckdb 接続も確立して SystemMonitor に渡す。
    - stop フラグ検出・KeyboardInterrupt による正常終了処理を実装。

- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーへ設定。
    - 既存ハンドラをクリアして重複設定を防止。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac 等）で差分を吸収して優先度を設定。失敗時は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。

- ポートフォリオ構築・リスク関連（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア順で上位 N を選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア比率配分、スコア合計が 0 の場合は等配分にフォールバック）
  - セクター集中・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率が上限を超える場合に新規候補をブロック。unknown セクターは除外しない）
    - calc_regime_multiplier（market regime に応じた乗数、未知のレジームはフォールバックで 1.0）
  - 株数決定・投資上限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算（"risk_based" / "equal" / "score"）
    - risk_based: 損切り幅・risk_pct に基づいて株数を算出
    - per-position 上限、lot_size（単元）で丸め、cost_buffer を考慮した aggregate cap（利用可能現金を超えた場合はスケーリング）と残差処理（lot 単位で再配分）
  - portfolio パッケージのエクスポート API を整備（src/kabusys/portfolio/__init__.py）

- 解析・レポート
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出して PASS/FAIL 判定を出力。
    - しきい値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプションで期間・DB 指定可能。
  - research/factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム等のファクター計算（DuckDB の prices_daily / raw_financials を参照）を実装する設計。モメンタム計算用定数・関数群を追加。

- パッケージ情報
  - バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）

### Changed
- （初期リリースのため該当なし）

### Fixed
- 環境値のバリデーション強化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出して警告し、デフォルトにフォールバックするように改善（run_monitoring）。
  - PAPER_FILL_MODE の不正値を検出し例外を発生させるバリデーションを追加（config.Settings）。
- DB 初期化の冪等性
  - monitoring 用テーブルが存在することを保証する init_monitoring_db を実行することで、monitoring/実行開始時に監視テーブルを確実に準備する（run_execution/run_monitoring）。
- paper_trading の DB 分離
  - paper_trading 実行時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番の monitoring DB と完全分離する仕様を導入（run_execution）。

### Security
- .env 自動読み込み時に OS 環境変数を保護する仕組みを導入（config._load_env_file の protected 引数）。既存の OS 環境変数が上書きされないように制御。
- 対話式ウィザードで秘密情報はマスク表示（config_setup）。

### Notes / Migration
- 監視（run_monitoring）は「環境にかかわらず」settings.sqlite_path（本番監視 DB）を使用します。監視データを別 DB にしたい場合は SQLITE_PATH を適切に設定してください。
- ペーパートレード時は run_execution が settings.paper_sqlite_path を使用します（デフォルト: data/paper_trading.db）。ペーパートレード DB と本番 DB は分離されます。
- 起動時の Kill / Stop フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の運用に注意してください。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険（validate_config で警告）。
- research/factor_research モジュールは DuckDB のテーブル（prices_daily / raw_financials）に依存します。運用前に DuckDB のスキーマが整備されていることを確認してください。
- ログ出力先はデフォルト logs/ ディレクトリです。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。必要に応じて LOG_DIR 環境変数で変更してください。

### Known issues / TODO
- research/factor_research.py のモメンタム計算実装が途中で切れている（ソース末尾が不完全）。完成させる必要があります。
- position_sizing は lot_size を全銘柄共通としている（将来的に個別単元対応の拡張を注記）。  
- apply_sector_cap の価格欠損時（price == 0.0）にエクスポージャーが過少見積りされる注記あり（TODO: フォールバック価格を採用する改善案）。

---

以上。必要であればセクションの分割（リリース日付の確定、より細かいフィアル単位の変更ログ化）を行います。