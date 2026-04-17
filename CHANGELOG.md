# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期リリース。
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 停止はプロジェクト配下の data/stop_requested.flag の検出で行う。  
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する（指定された sqlite_path に接続して監視 DB テーブルを初期化）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。  
    - 起動時にプロセス優先度を "high" に設定し、停止フラグに応じてセッションを停止する。  
    - ExecutionEngine をデーモンスレッドで起動し、実行中に停止フラグを監視する。  
- 設定・環境変数管理
  - config.py: Settings クラスを追加。環境変数から各種設定を取得する。  
    - 自動的にプロジェクトルートの .env/.env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
    - .env パーサは export KEY=val 形式、クォート（シングル/ダブル）のエスケープ、インラインコメントの扱い等に対応。  
    - PAPER_FILL_MODE（instant/partial/never/reject）などの検証ロジック、パス系や閾値のデフォルト値を提供。  
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。シークレット項目はマスク表示、保存前に確認プロンプトを表示。  
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、YAML のパース確認（PyYAML 未インストール時は警告）などを実施。  
    - --strict オプションで警告も失敗扱いにできる。  
- ポートフォリオ構築（純粋関数群、DB非依存）
  - portfolio.portfolio_builder: 候補銘柄選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）を実装。  
  - portfolio.risk_adjustment: セクター集中防止 apply_sector_cap（"unknown" セクターは免除）と市場レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）を実装。  
  - portfolio.position_sizing: 株数決定ロジック calc_position_sizes を実装。  
    - allocation_method に応じた "risk_based"/"equal"/"score" をサポート。  
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、集計上限（available_cash）に基づくスケーリング、cost_buffer による保守的なコスト見積り、残余キャッシュを使った端数配分ロジック等を実装。  
- 研究用ファクター計算
  - research.factor_research: DuckDB 接続を受けて Momentum（1M/3M/6M、MA200乖離）や Volatility（ATR 等）等のファクターを計算するユーティリティを追加（prices_daily / raw_financials テーブル参照）。  
- ユーティリティ
  - utils.process_priority: プロセス優先度と CPU affinity のユーティリティを追加。  
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、psutil を使って nice/priority を設定。失敗時は警告を出して安全にスキップ。  
- 運用用ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値（稼働率 99% など）に基づく PASS/FAIL を出力。  
    - 日付範囲指定（--from/--to）や DB パス指定（--db / 環境変数）に対応。  
- パッケージメタ
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

Notes
- いくつかの箇所で将来的な拡張や注意点をコード内コメントとして残しています（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の price 欠損時のフォールバック戦略、process_priority の未対応 OS 等）。必要に応じて実装を拡張してください。