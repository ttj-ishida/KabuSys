# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

本ファイルは、コードベースから推測可能な変更点・追加機能をまとめたものです。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-04-19

初回リリース — 基本的な実行・監視・設定・ポートフォリオ構築・ユーティリティ群を追加。

### Added
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。  
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っていれば起動を中止。実行時は別スレッドで engine.run_session を実行し、停止フラグ検出で engine.stop() を呼び出して終了する。PID ファイル（data/execution.pid）を利用。  
    - BrokerClientFactory によりブローカークライアントを生成（ペーパートレード時には MockBrokerClient が利用される想定）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。  
    - 監視 DB は環境に関係なく production 用 sqlite_path を使用する設計（監視は本番 DB に記録）。停止フラグでループを終了する。

- 設定管理 & 初期化
  - config.Settings: 環境変数から設定値を取得する Settings クラスを追加。  
    - 多数のプロパティを提供（J-Quants トークン、kabu API、LINE トークン、DB パス、監視閾値、環境判定プロパティ等）。  
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実施。  
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込み（OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup: .env を対話式に作成・更新するウィザード CLI を追加。既存値の読み込み、秘密値マスク、保存内容確認などをサポート。

- 設定検証
  - validate_config: .env と config/*.yaml の起動前チェック CLI を追加。  
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイル存在・パース確認（PyYAML 未インストール時はスキップ）等を実施。  
    - --strict オプションで警告も失敗（exit 1）として扱う。

- ロギング & プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーを統一的に設定するユーティリティを追加。  
    - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler, デフォルト logs/ ディレクトリ、30日分保持）を設定。LOG_LEVEL, LOG_DIR の環境変数や引数で上書き可能。既存ハンドラをクリアして二重設定を防止。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。権限不足など失敗時は警告を出してスキップ。  
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定する関数を追加。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして候補を選択。  
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分の重み計算。全スコアが 0 の場合は warning を出して等金額にフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（max_sector_pct）を適用して候補をフィルタ。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。unknown セクターは制限対象外。  
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数を計算するロジックを追加（allocation_method: risk_based / equal / score をサポート）。  
      - リスクベース（risk_based）ではリスク率・損切り幅から基準株数を算出、単元（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）でのスケーリングを実装。  
      - aggregate cap 超過時のスケールダウンでは残差（fractional_remainder）に基づく追加配分を行い、安定な順序で割り当てを決定する。cost_buffer（スリッページ・手数料見積り）を考慮。

- 研究・ファクター計算（下地）
  - research.factor_research: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。calc_momentum の実装開始（ファイル末尾は続きがある想定）。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き）。  
    - 指標: システム稼働率（uptime_pct）、注文成立率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）など。P95 算出ロジック実装。  
    - PASS/FAIL 判定閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。

- DB / analytics
  - DuckDB を分析用に組み込み（Settings.duckdb_path）。run_execution / run_monitoring で duckdb.connect を利用して解析用接続を生成。

### Changed
- ログ出力の統一
  - すべての起動スクリプトで setup_logging を呼ぶことでログ出力が統一され、ファイルローテーションとコンソール出力が同じフォーマットで行われるようになった。

### Fixed
- .env パーサの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォート無しは '#' の前にスペース/タブがあればコメントとみなす）などを実装し、.env の柔軟な記述に対応。

### Notes / Known issues
- research.factor_research の calc_momentum はファイル末尾が途中である（実装継続の余地あり）。詳細実装は今後追加予定。  
- position_sizing は現状単元株数（lot_size）をグローバル固定想定（各銘柄別の単元対応は TODO として記載あり）。  
- process_priority / cpu_affinity はプラットフォームや権限に依存するため、権限不足時は警告を出してスキップする設計。

### Removed
- （なし）

### Security
- （なし）

---

（注）本 CHANGELOG は現在のコード内容から推測して作成しています。実際のコミット履歴やリリースノートと完全に一致しない可能性があります。必要であれば、実コミットメッセージを基に詳細を調整します。