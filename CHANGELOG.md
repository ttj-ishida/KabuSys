# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` で設定。

- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を設定してエンジンを起動。
    - KABUSYS_ENV による paper_trading モード対応。paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検出による安全停止処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。
    - 停止フラグ検出でループ終了、例外はログに記録して次ループへ。KeyboardInterrupt をハンドリング。

- 設定管理・ツール
  - config.py: 環境変数 / .env 自動読み込み機能を追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env, .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサを実装（コメント・クォート・export 形式に対応）。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境分類など）をプロパティ経由で取得。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 既存 .env 読み込み、項目別入力、シークレットのマスク表示、保存機能を提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV 値・ログレベル・DB パス親ディレクトリ・config/*.yaml（PyYAML が存在する場合はパース検証）・本番用ガードを検査。
    - --strict オプションで警告も FAIL 扱い可能。

- データベース / 監視
  - monitoring_db 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring 起動時に実行して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重の重み計算。全スコアが 0 の場合は等重にフォールバックし警告ログ出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック。既存保有のセクターエクスポージャに基づき新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull/neutral/bear に対応、未知値はフォールバック 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数計算（risk_based / equal / score 対応）。
      - lot_size（単元）丸め、max_position_pct の適用、stop_loss に基づく risk_based ロジックを実装。
      - aggregate cap（available_cash 超過時）でスケーリングし、残差に応じて lot 単位で再配分するアルゴリズムを実装。
      - cost_buffer を考慮した保守的コスト見積りをサポート。

- 研究用モジュール
  - research.factor_research
    - calc_momentum: DuckDB の prices_daily テーブルを用いた 1M/3M/6M リターン・MA200 乖離率の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算（欠損時の扱いを考慮）。
    - DuckDB 接続を受け取り SQL + Python で処理（外部 API 呼び出しなし）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX の差分を吸収してカレントプロセスの優先度を設定。権限不足や未サポート環境では警告を出してスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能を追加（未サポート環境では警告を出してスキップ）。

- ツール
  - tools.paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計し、PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を採用。
    - --from / --to / --db オプションで期間・DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を参照。

### Changed
- 設計方針の明文化
  - ポートフォリオ / リスク計算関数群は副作用のない純粋関数として実装され、DB 参照は行わない方針を明記。
  - DuckDB を分析用 DB として明確に分離し、SQLite は監視・発注履歴保存用とする。

### Fixed
- 安全対策の実装
  - run_execution/run_monitoring に停止フラグ検出機構を追加して外部停止ファイルに依る安全停止を容易にした。
  - config._load_env_file: .env 読み込み失敗時に警告を出すようにして起動時の明確な診断を可能に。

### Notes / Implementation details
- 環境変数の自動読み込みはプロジェクトルートを .git または pyproject.toml で探索するため、パッケージ配布後も動作するよう設計。
- .env パーサはシングル/ダブルクォート内のエスケープや export プレフィックス、インラインコメントの扱いに配慮。
- リスク計算・ポジションサイジングは将来的な拡張（銘柄別 lot_size 等）を見据えた注釈を含む。
- クロスプラットフォームのプロセス優先度設定は権限やプラットフォーム差分を考慮して安全にフォールバックする実装。

---

開発中の変更や追加機能は Unreleased に記録してください。リリースのたびにこのファイルを更新し、上記フォーマットに沿って変更点を明確にしてください。