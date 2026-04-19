# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- バージョンごとに「Added / Changed / Fixed / Removed / Security」などの見出しを使用しています。
- 日付は YYYY-MM-DD 形式です。

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期リリース。以下の主要コンポーネントを追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（本番/モックの切替）。
    - スレッドで engine.run_session を実行し、data/stop_requested.flag による停止制御、実行用 PID ファイル出力をサポート。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - Execution 用の既定 RiskConfig 値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - DuckDB 接続と monitoring 用テーブルの初期化（init_monitoring_db）を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - data/stop_requested.flag による外部停止制御、例外発生時のログ出力とポーリング継続処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理と CLI
  - config.py
    - 環境変数および .env ファイルの読み込みロジックを追加。
    - プロジェクトルート検出（.git または pyproject.toml を基準）に基づく .env の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - 独自の .env パーサ実装（export 形式、クォート、エスケープ、コメント処理対応）。
    - Settings クラスを追加し、アプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API など）。各種検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新する CLI を追加。
    - シークレット入力のマスク表示、既存 .env の読み込み・再利用、生成した .env の書き込みロジックを提供。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスや config ファイル存在チェック、KABUSYS_ENV=live 時の追加ガード（LINE 設定や kill flag 設定の警告）を実装。
    - --strict オプションで警告を FAIL として扱うモードを提供。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。
    - stdout 出力用 StreamHandler と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力を組み合わせて設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力を自動的にスキップするフォールバックあり。
  - utils/process_priority.py
    - Windows/Linux/macOS を意識せずプロセス優先度を設定する set_process_priority を追加（psutil 利用）。
    - CPU affinity を設定する set_cpu_affinity を追加（利用可能なコア数に合わせて最初の N コアにピン留め）。
    - 権限不足や未対応プラットフォーム時に警告ログを出して安全にスキップする実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates: スコア降順、タイブレーク処理）を実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中リスク制御（apply_sector_cap）を実装。既存保有エクスポージャーに基づき特定セクターの新規候補を除外するロジック（"unknown" セクターは除外しない）。
    - 市場レジームに基づく乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマップ、未知はフォールバックして警告）。
  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮した保守的な見積り、残差処理（lot 単位での追加配分）を実装。

- Paper Trading 関連ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから指標を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを出力。
    - Pass/Fail 判定基準（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプション対応。デフォルト DB: data/paper_trading.db。

- research/factor_research.py（分析用初期実装）
  - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム・MA200・ATR・出来高などの計画と定数を定義）。
  - 関数 calc_momentum の導入が開始されている（実装途中でファイル終端が来ています）。

- パッケージメタ
  - __init__.py にてバージョンを "0.1.0" に設定。

### Changed
- （初回リリースため該当なし）

### Fixed
- （初回リリースため該当なし）

### Known issues / Notes
- research/factor_research.py の一部（calc_momentum 等）は実装途中で終端しているため、本番利用前に完成が必要です。
- process_priority / set_cpu_affinity は権限やプラットフォーム制約（psutil の機能差）に依存するため、実行環境によっては優先度設定がスキップされる場合があります（警告ログで通知）。
- .env パーサはかなり柔軟に実装されていますが、極端に複雑な .env 構成（多重エスケープ等）は未検証のため注意してください。
- Paper Trading と本番 DB は設計上分離されていますが、運用時は環境変数とファイルパスの設定を確認してください（validate_config を推奨）。

---

今後の予定（非網羅）
- research モジュールの完成（ファクター計算の SQL/集計実装）。
- ExecutionEngine / SystemMonitor のより詳細なログ・メトリクス統合。
- 単体テストおよび CI ワークフローの追加（現在はコードのみの提供）。

--- 

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはリリース履歴やコミットメッセージに基づいて更新してください。）