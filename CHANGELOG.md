# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

※ 本ドキュメントはソースコードの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回公開リリース（推測）。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - パッケージ外部公開 API（portfolio モジュールの主要関数など）を __all__ に定義。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて Paper Trading 用 DB を分離（data/paper_trading.db を使用）。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。
    - 停止フラグ（data/stop_requested.flag）検出で安全に終了。実行 PID 管理（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（monitoring DB 初期化を保証）。
    - 停止フラグ検出でループを終了。

- 環境設定・検証ツール
  - config_setup.py: 対話式 .env 設定ウィザードを追加。
    - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）を案内。
    - シークレット値はマスクして表示。生成した .env を上書き保存。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 設定管理
  - config.py:
    - .env の自動ロード機能（プロジェクトルートに基づく .env / .env.local の読み込み。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースロジックを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - 環境変数取得用 Settings クラスを提供（duckdb/sqlite パス、PID/kill flag パス、各種閾値、paper_trading 用設定等）。
    - 設定値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ初期化関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/）を設定。
    - LOG_DIR / LOG_LEVEL の優先解決をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作。
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX に対応したプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）。
    - set_cpu_affinity: CPU affinity を最初の N コアに固定するユーティリティ（権限や未対応 OS では安全にスキップ）。
    - 許容レベル: "high" / "normal" / "low"。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア順にソートして上位を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は警告して等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの露出上限チェック（既存ポジションと価格マップを用いて除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）でのスケーリング、cost_buffer による保守見積もり、スケール後の残余分を公平に配分するアルゴリズムを実装。

- リサーチ / ファクター算出（準備）
  - research/factor_research.py:
    - DuckDB 接続を受け取り、Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR）、Liquidity、Value（財務指標）などの計算を行う設計を追加（prices_daily / raw_financials を参照）。
    - 各種定数やスキャン窓、P95 等のユーティリティを含む（モジュールは一部実装が続く形で追加）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL を判定。
    - デフォルト基準値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）を定義。

- DB / 分析
  - duckdb を使用した分析用 DB 接続をサポート（Settings.duckdb_path）。
  - monitoring 用 SQLite DB 初期化関数（init_monitoring_db）を起動時に呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- なし（初回公開のため該当なし）

### Fixed
- なし（初回公開のため該当なし）

### Security
- config_setup の出力でシークレット項目はマスク表示。README 等で .env を Git に絶対にコミットしない旨を注記（.env ファイルヘッダに説明あり）。

### Notes / Implementation details（重要な動作）
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しません。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数から取得し、不正な値（0 以下や非整数）の場合はデフォルト 60 秒にフォールバックします。値がログに警告されます。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
- process_priority / cpu_affinity は権限不足や未対応プラットフォーム時に安全にスキップし、警告ログを出力します。
- Paper Verification レポートは対象 DB が存在しない場合にエラー出力して終了します。

---

今後のリリース候補（想定）
- factor_research の完成実装とテスト
- ExecutionEngine / SystemMonitor の詳細なユニットテスト追加
- 各種設定のより詳細なバリデーション（config/*.yaml のスキーマ導入）
- Windows/Cross-platform テストの強化

（この CHANGELOG はコードの内容を元に推測して作成しています。実際の変更履歴やリリースノートは運用方針に合わせて調整してください。）