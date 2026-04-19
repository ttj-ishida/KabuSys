# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。主要なバージョンは semantic versioning に従います。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初回リリースを作成。
  - パッケージメタ情報として `__version__ = "0.1.0"` を追加。

- 実行用エントリスクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - Broker クライアント生成を `BrokerClientFactory` 経由で行う。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。停止フラグ（data/stop_requested.flag）を検知して安全に停止する仕組みを実装。
    - PID ファイルを出力（デフォルト: data/execution.pid）。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視では環境に関わらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 例外発生時はログ出力して次のポーリングへ継続。

- 設定・環境管理
  - `kabusys.config.Settings` を追加。環境変数から各種設定（DB パス、API トークン、各種閾値、実行環境）を取得する。
    - `env` の検証（`development` / `paper_trading` / `live` のみ有効）。
    - `paper_fill_mode` の検証（`instant` / `partial` / `never` / `reject`）。
    - 各種パスは Path オブジェクトで返却（expanduser を適用）。
    - `is_live` / `is_paper` / `is_dev` の補助プロパティ。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出して `.env` / `.env.local` を読み込む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` のパースはシングル／ダブルクォート、エスケープ、行末コメント等に対応する堅牢な実装を提供。

- 設定支援 CLI
  - `config_setup` ウィザードを追加（対話式で .env を作成・更新）。
    - J-Quants / kabu API トークン等を対話的に入力可能。
    - デフォルト値・選択肢・シークレットマスク表示をサポート。
    - 保存前に確認プロンプトを表示。

- 設定検証 CLI
  - `validate_config` を追加。起動前に .env と config/*.yaml の存在・整合性を検査。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE パスの親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml のパース検証（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で配分（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に候補を除外。`unknown` セクターは除外対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株（lot_size）対応、max_position_pct や max_utilization、cost_buffer を考慮した aggregate cap スケーリングアルゴリズムを実装。

- ユーティリティ
  - utils.logging_setup: 統一的ログ設定ユーティリティを追加。
    - stdout に StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_DIR や LOG_LEVEL の環境変数・引数優先順を実装。
  - utils.process_priority: クロスプラットフォームでプロセス優先度および CPU affinity を設定するユーティリティを追加。
    - psutil を利用して Windows の priority class、POSIX 系の nice 値を適用。失敗時は警告を出してスキップ。
    - set_cpu_affinity を提供（指定コア数でプロセスをピン留め）。

- データ解析・検証ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、システム稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - P95 計算ロジック、日付フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
    - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

- データ分析基盤接続
  - DuckDB 接続を各所で利用（`duckdb.connect` を使用）。分析用 DB は `DUCKDB_PATH` で指定可能（デフォルト: data/kabusys.duckdb）。

### Changed
- 監視データベースの初期化
  - 監視起動時・Execution 起動時に `init_monitoring_db(sqlite_conn)` を呼び、監視テーブルの存在を保証（冪等に初期化）。
- ログ出力の統一化
  - すべての起動スクリプトで `setup_logging(app_name=...)` を呼び出すことでログのフォーマット・出力先を統一。

### Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープや行末コメントの扱い、`export KEY=val` 形式に対応することで .env 読み込みの失敗や誤読を軽減。

### Security
- 秘密情報の取り扱い
  - config_setup の対話表示でシークレット項目はマスク表示（既存値や確認時に ***** 表示）。
  - .env の生成に関する注意書きを明示（.env を Git にコミットしない旨）。

### Notes / Implementation details
- ExecutionEngine 側の RiskManager 生成時に `initial_portfolio_value` を BrokerClient の `get_available_cash()` で初期化しており、ブローカー実装に依存した起動時初期値が設定される。
- run_monitoring は環境に依らず本番 sqlite_path を参照する設計（監視は常に本番 DB 参照を想定）。
- デフォルトのログディレクトリ作成やファイルハンドラの作成に失敗した場合はログファイル出力をスキップして stdout のみで継続する堅牢化を行っている。
- process_priority の設定はプラットフォームや権限によって失敗する可能性があり、該当場合は警告ログを出して処理を継続する。

---

今後のリリースで予定している改善例:
- 銘柄ごとの lot_size をマスタに持たせる（position_sizing の拡張）。
- run_monitoring のポーリング間隔を動的に調整する機能（負荷に応じたバックオフ等）。
- Paper Trading 検証レポートの HTML/PDF 出力や日時粒度の柔軟化。