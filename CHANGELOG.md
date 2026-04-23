# Changelog

すべての注目すべき変更履歴はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を参照しています。

現在のパッケージバージョン: 0.1.0
リリース日: 2026-04-23

## [0.1.0] - 2026-04-23

### Added
- 実行エントリ / 実行コンポーネント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV によって paper_trading モードを切り替え。paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離する設計。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。EngineConfig はデフォルトで target_date = today。
    - 実行中はデーモンスレッドでセッションを回し、 data/stop_requested.flag を検知すると安全に停止する。
    - PID ファイルを data/execution.pid に書き出す仕組み（設定から変更可能）。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor をポーリング起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB パスを参照）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - DB 初期化（init_monitoring_db）を呼び出して監視テーブルの存在を保証。
    - duckdb と sqlite 両方の接続を扱う。

- 設定管理・初期化ツール
  - config.py: 環境変数読み込み・ラッパー Settings を追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）を実装し、.env / .env.local を自動読み込み（OS 環境変数より低優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / PID・Kill flag パス / 監視閾値 / 環境判定メソッド等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
  - config_setup.py: 対話的 .env 作成ウィザードを追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話式に生成・更新可能。
    - 既存 .env の読み込み／マスク表示（シークレット）対応。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 有無に依存）など。
    - --strict オプションで警告を FAIL 扱い（exit(1)）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す（signal_rank によるタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコアに基づく重み。全スコアが 0 の場合は警告を出し等金額にフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、上限を超えているセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数計算ロジックを実装（allocation_method: "risk_based" | "equal" | "score"）。
      - 単元（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash に対するスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと端数処理を実装。
      - risk_based: 損切り率 stop_loss_pct と risk_pct に基づく単位算出。
      - equal/score: weight に基づく配分。
      - ログ出力で価格欠損等の状況を報告。

- ユーティリティ
  - utils.logging_setup: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数または引数での上書き対応。既存ハンドラの二重登録を防止するためクリア後再設定する。
    - ファイルハンドラ作成失敗時にコンソールのみで継続。
  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority("high"|"normal"|"low") を提供。権限不足時に警告を出してスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定（未サポート環境は警告を出す）。

- 解析 / レポートツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定された paper_trading DB から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ 等）を集計しレポート出力。
    - Pass/Fail 基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 latency <= 200ms 等）を実装。
    - P95 計算、期間フィルタ（--from / --to）対応。
    - DB テーブルが存在しない場合に安全に N/A / 0 を返すフェイルセーフ実装。

- 研究（Research）
  - research.factor_research: DuckDB を用いたファクター計算モジュール（モメンタム、移動平均乖離、ATR、売買代金等）を追加（設計および一部実装）。
    - prices_daily / raw_financials のみ参照し、外部 API に依存しない。
    - 関数は (date, code) をキーとする dict のリストを返す設計。

- パッケージ初期情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Security
- N/A（初回リリース）

### Notes / Migration
- 環境変数の自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml）を探索し .env / .env.local を読み込みます。OS 環境変数が優先され、既存 OS 環境変数を上書きしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の DB 分離
  - paper_trading モードではデフォルトで data/paper_trading.db を使用し、本番の monitoring.db とは分離されます。PAPER_TRADING_SQLITE_PATH で上書き可能。
- 監視モードについて
  - run_monitoring は監視用 DB のパス（Settings.sqlite_path）を使用します。MONITOR_POLL_INTERVAL でポーリング間隔を調整できます（正の整数のみ有効）。
- ログ
  - デフォルトログディレクトリは logs/、日次ローテーションで 30 日分保持します。LOG_DIR / LOG_LEVEL により変更可能です。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- Kill / Stop フラグ
  - 停止制御は data/stop_requested.flag（プロジェクトルート data ディレクトリ）を利用します。KILL_FLAG_CLEAR_ON_START 設定に注意してください（特に本番では 0 推奨）。

もし追加で各モジュールの利用例（CLI 実行方法、環境変数リファレンス、設定例の .env テンプレート等）をCHANGELOG に追記したい場合は指示してください。