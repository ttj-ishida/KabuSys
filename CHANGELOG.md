# CHANGELOG

すべての重要な変更は SemVer に従って記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。KabuSys のコアユーティリティ、実行監視、ポートフォリオ構築、設定管理、解析ツール群を収録。

### Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を最初に High に設定し、スレッドでエンジンを起動／停止する仕組みを提供。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を経由してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理を実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する動作を明示。
    - 起動時にプロセス優先度を High に設定し、stop フラグ検知でループを終了する安全な設計。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local の読み込み順序（OS 環境 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env パーサを強化（export 形式、クォート中のエスケープ、インラインコメント扱いなど）。
    - Settings クラスを提供し、各種設定（J-Quants, kabuAPI, DuckDB/SQLite パス、Paper Trading 設定、監視閾値、環境種別判定 等）をプロパティで取得できるようにした。
    - PAPER_FILL_MODE の有効値検証を実装（"instant","partial","never","reject"）。
    - 環境種別（development/paper_trading/live）の検証やログレベル検証を備える。

  - config_setup.py
    - 対話式の .env ウィザードを追加（初期作成・更新を支援）。既存 .env の読み込み、値のマスク表示、保存確認などのフローを実装。
    - .env 書き込みテンプレートを提供（書き込む際に Git にコミットしない旨の注意を追加）。

  - validate_config.py
    - 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在（及び PyYAML が導入されている場合はパース検証）を行う。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）で選別。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等配分にフォールバック、警告ログ出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有を元にセクターごとの上限（デフォルト 30%）を評価し、新規候補から超過セクターを除外するロジックを実装。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（"bull":1.0、"neutral":0.7、"bear":0.3、未知は 1.0 にフォールバック且つ警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた株数計算を実装（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）に合わせた丸め、1 銘柄上限（max_position_pct）、投下資金の aggregate cap（available_cash を超える場合のスケーリングと残差処理）を実装。
    - cost_buffer を考慮した保守的見積り、価格未取得時のスキップ、内部デバッグログ等を導入。
    - TODO ノート: 銘柄別 lot_size、価格フォールバック（前日終値等）に関する拡張を注記。

- 監視・モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて監視用テーブルが存在することを保証（冪等に動作する初期化）。

- 解析（Research）
  - research.factor_research
    - DuckDB 接続を用いたファクター計算（Momentum / Volatility / Liquidity / Value 等の設計方針と、mom/ma/ATR 等の具体的な計算ロジックの実装）。
    - calc_momentum, calc_volatility 等の実装により、prices_daily テーブルから指標を算出して dict のリストを返す設計。

- ツール
  - tools.paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加（デフォルト DB: data/paper_trading.db、期間フィルタ対応）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し PASS/FAIL を判定する閾値を定義。
    - P95 計算、各種 NULL / データ不足時の N/A 処理を実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装し、Windows と POSIX（Linux/Mac/FreeBSD）に対応した優先度設定を抽象化。権限不足や未対応 OS は警告でスキップ。
    - set_cpu_affinity(cpu_count) を実装。利用可能コア数を超える指定時の挙動、安全な例外ハンドリングを含む。

### Changed
- なし（初回リリースのため）。

### Fixed
- なし（初回リリースのため）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

### Notes / Known limitations
- factor_research は DuckDB の prices_daily / raw_financials に依存しており、テーブルが存在しない場合は機能が限定されます。
- apply_sector_cap のエクスポージャー算出は price_map に依存しており、price が欠損した場合に過少評価される可能性がある旨を TODO コメントで残しています。
- position_sizing は現状 global lot_size（デフォルト 100）を前提としており、銘柄別単元対応は今後の拡張予定です。
- .env ファイルには機密情報（例: API トークン）が含まれるため、生成された .env を Git 等に絶対にコミットしないでください。

---

今後のリリースでは、ブローカークライアントの実装詳細、ExecutionEngine の挙動検証、銘柄別 lot_size 対応、監視アラート（LINE 通知等）統合の強化などを予定しています。