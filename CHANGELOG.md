# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- （現時点のコードベースでは初回リリース相当の機能群が実装されています。次回の変更点はここに記載されます）

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。実行中は PID ファイルを管理し、停止フラグ検知でエンジンを停止。

- 設定管理
  - config.py: 環境変数/.env の読み取りロジックを実装。プロジェクトルート自動検出（.git または pyproject.toml ベース）、.env/.env.local の読み込み順序、クォート処理や export KEY=val 形式のパース、各種設定値（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境判定 等）を Settings クラスにプロパティとして提供。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性チェックを実装。
  - settings オブジェクトを簡易的に利用可能。

- 設定ツール・検証
  - config_setup.py: 対話式ウィザードで .env ファイルの初期作成・更新を支援。シークレットマスク表示、デフォルト値提示、保存確認を実装。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース（PyYAML が無い場合はスキップして警告）や本番環境向けガード（LINE 通知設定や Kill Switch の自動クリア設定）を実装。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを実装。stdout（StreamHandler）出力および日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバック、既存ハンドラのクリアなどをサポート。
  - utils/process_priority.py: psutil を使ったプロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを実装。クロスプラットフォーム対応と権限不足時の安全な警告処理を行う。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で上位 N を選定（タイブレークは signal_rank）。
    - calc_equal_weights: 等分配重みを計算。
    - calc_score_weights: スコアに基づく重み計算。全スコアが 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクター集中の上限チェック（max_sector_pct）を実行。既存保有の時価を考慮し、上限超過セクターの新規候補を除外。売却予定銘柄は除外して計算。未知セクター("unknown")は上限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告後に 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた銘柄ごとの発注株数計算機能を実装。単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、全体投下上限（max_utilization / available_cash）、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap のスケーリング、スケールダウン時の残差分配ロジックを備える。

- 監視 DB 初期化ユーティリティ呼び出し
  - run_monitoring.py / run_execution.py の両方で init_monitoring_db(sqlite_conn) を呼び出し、監視テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95））を集計して人間向けレポートを生成。閾値（稼働率/成功率/送信率/P95 レイテンシ）を定義し PASS/FAIL 判定を行う。日付フィルタ（--from/--to）対応。

- research/factor_research.py（ファクター計算）
  - DuckDB を使った定量ファクター計算モジュールの骨格を実装。モメンタム/MA/ATR/流動性/バリュー等の計算を行う設計（DuckDB の prices_daily/raw_financials を参照）。（ファイル末尾は断片的に含まれており、実装の続きが存在することを示唆）

- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Documentation
- 各モジュールにドキュメンテーション文字列（docstring）を付与し、動作の注意点や設計方針、使い方（CLI の例や環境変数）を明記。

### Notes / Implementation details / Caveats
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探して行う。プロジェクトルートが見つからない場合は自動ロードをスキップする。
- SETTINGS では本番/ペーパートレードの DB を分離する設計（Settings.is_paper を利用）。
- process_priority や CPU affinity の設定は権限やプラットフォームによって失敗する可能性があり、その場合は警告を出して処理をスキップする。
- ログ出力は標準出力（stdout）優先で、ログファイル出力はディレクトリ作成に成功した場合のみ有効となる。失敗時はコンソールのみで継続。
- portfolio/position_sizing の一部（価格欠損時のフォールバック等）は TODO コメントが残っているため、将来的に改善予定。
- config/*.yaml の内容検証は PyYAML の存在に依存する。未インストール時は YAML 内容チェックをスキップして警告のみ出す。

## リリース方針（推奨）
- 次回以降は機能追加は "Added"、API/挙動互換を壊す変更は "Changed"（Breaking changes を明記）、
  バグ修正は "Fixed" に追記してください。

（以上）