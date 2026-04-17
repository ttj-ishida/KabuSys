# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

注: コードベースから挙動を推測して記載しています。実装上の詳細はソースをご確認ください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

Added
- プロジェクト初期リリース。
- 環境設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントをサポート。
  - 必須環境変数チェック用の _require 関数と Settings クラスを導入（J-Quants, kabuAPI, DB パス等のプロパティを提供）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）と paper_trading 用 SQLite パスの分離を実装。
  - KABUSYS_ENV / LOG_LEVEL の検証および is_live/is_paper/is_dev 判定を提供。
  - デフォルト値やパス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）の取得ロジックを実装。

- 環境セットアップ対話ウィザード（kabusys.config_setup）
  - .env を対話式に作成・更新する CLI を追加。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）と既存 .env の読み込み・確認・保存機能を実装。
  - シークレット項目は出力時にマスク。

- 設定検証ツール（kabusys.validate_config）
  - 起動前に .env と config/*.yaml（存在する場合）を検証する CLI を追加。
  - 必須/任意環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がインストールされている場合）を実施。
  - KABUSYS_ENV=live の際の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START などの警告）を実装。
  - --strict オプションで警告も失敗扱いにできる。

- 実行エンジン起動スクリプト（kabusys.run_execution）
  - ExecutionEngine の起動エントリポイントを提供。
  - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - paper_trading 環境では専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てを行い、ExecutionEngine.run_session を別スレッドで実行。
  - 停止フラグ（data/stop_requested.flag）を検知すると安全に停止。PID ファイル出力位置を指定可能。

- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループを開始するスクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に格納）。
  - 起動時にプロセス優先度を "high" に設定。停止フラグ（data/stop_requested.flag）検知でループ終了。

- 監視 DB 初期化フック
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼んで監視テーブル存在を保証（冪等）。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows と POSIX を吸収する set_process_priority(level) を実装（high/normal/low）。
  - set_cpu_affinity(cpu_count) による CPU 固定機能を実装。
  - 権限不足や未対応 OS では警告を出してスキップする堅牢性を実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナルから候補選択 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合は等金額にフォールバックして警告。
  - risk_adjustment: apply_sector_cap（既存保有含めてセクター集中を検査し超過セクターの新規候補を除外）、calc_regime_multiplier（regime に応じた投下資金乗数）を実装。unknown セクターはセクター上限適用除外。未知レジームは 1.0 にフォールバック。
  - position_sizing: calc_position_sizes を実装（allocation_method: risk_based/equal/score 対応、損切りパラメータ、max_position_pct, max_utilization, lot_size, cost_buffer を考慮した計算）。aggregate cap 超過時のスケールダウンと lot_size 単位での丸め・端数配分ロジックを実装。

- リサーチ / ファクター計算（kabusys.research.factor_research）
  - DuckDB 接続を受け取り prices_daily / raw_financials 等からファクターを計算するモジュールを追加。
  - モメンタム（1m/3m/6m リターン、MA200 乖離）計算（calc_momentum）。
  - ボラティリティ・流動性指標計算（calc_volatility）など（SQL ベースの実装）。

- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から期間指定でレポートを生成する CLI を追加。
  - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値に基づいた PASS/FAIL 判定を出力。
  - P95 計算、欠損データの堅牢な取り扱い、DB 存在チェックを実装。

Changed
- なし（初期公開のため実装が追加された項目を中心に記載）。

Fixed
- 例外耐性を強化：
  - run_monitoring のループ内で monitor.check_once() が例外になってもループを継続し、例外情報をログ出力するようにした。
  - DB 接続後の finally でのクローズ処理を適切に配置。

Security
- .env 出力テンプレート（config_setup）に関する注意を明記（.env を絶対に Git にコミットしない旨をコメントとして出力）。

Notes / Implementation details
- stop/kill フラグは data/stop_requested.flag, data/kill.flag 等のファイル存在で制御する実装になっている（パスは Settings で上書き可能）。
- Settings の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる（テスト用途等）。
- DuckDB, sqlite3, psutil 等に依存。YAML 検証は PyYAML の有無で挙動が変わる。

Acknowledgements
- 本リリースはプロジェクトコードからの推測に基づく CHANGELOG です。追加の変更や補足はソース管理の履歴（コミットログ）を参照してください。