# Changelog

すべての重要な変更履歴をこのファイルに記載します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。  

最新リリース: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境変数周り
  - Settings クラスを実装し、環境変数からアプリ設定を取得する機能を追加。
    - 必須値の強制取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - 値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - SQLite / DuckDB / PID ファイルパス等のデフォルト値を提供。
    - is_live / is_paper / is_dev のヘルパープロパティを提供。
  - 自動 .env ロード機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先順位: OS環境 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントの扱いに対応。

- CLI ツール
  - 設定ウィザード: `kabusys.config_setup`（対話式で .env を生成・更新）
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話式に編集可能。
    - 既存 .env の読み込みおよび既存値の再利用に対応。
  - 設定検証ツール: `kabusys.validate_config`（.env と config/*.yaml の事前チェック）
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば実施）。
    - `--strict` オプションで警告も失敗扱いにできる。
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から指標を集計しレポート出力。
    - 指標: 稼働率（uptime）, 注文成功率（fill rate）, 送信率（send rate）, レイテンシ（avg/max/P95）など。
    - Pass/Fail の閾値を定義し、自動判定を行う。
    - コマンドラインで期間指定（--from/--to）および DB パス指定（--db）可能。

- 実行・監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を上げる（set_process_priority("high")）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag による停止を監視。PID ファイルの取り扱いあり。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計（監視データは常に本番 DB に記録）。
    - stop flag（data/stop_requested.flag）による安全終了、例外発生時のログ捕捉と継続動作。
    - DuckDB および SQLite の接続初期化と監視用テーブルの作成（init_monitoring_db）を行う。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア順で候補選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（max_sector_pct）を適用して候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に応じた投下資金乗数を提供（未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・リスクベース等に基づく発注株数計算。
    - 単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリングと端数処理）、cost_buffer 考慮などを実装。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を DuckDB 上で計算。
    - calc_volatility（実装途中含む）: ATR、相対 ATR、20日平均売買代金、出来高比率等を計算するためのクエリを実装（設定されたスキャン窓を使用）。
    - DuckDB SQL を用いた時系列ウィンドウ関数の利用により高速集計を想定。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するヘルパーを追加（psutil ベース）。
    - POSIX 系での nice 値、Windows 用の priority class を取り扱い、権限不足や未対応 OS の場合は警告ログでスキップ。
    - set_cpu_affinity による CPU ピンニング機能を追加（利用可能コア数を超える指定は全コア使用にフォールバック）。

- DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を run 系で呼び出し、監視テーブルが存在しない場合の自動作成を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- run_monitoring のポーリング間隔取得ロジックで 0 以下や不正値が指定された場合にデフォルトへフォールバックするよう改善（time.sleep に不正値を渡さないための保護）。
- .env パーサーのクォート/エスケープ処理を強化し、インラインコメントやバックスラッシュエスケープに対応。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いにおいてシークレットは .env ウィザードでマスク表示され、デフォルトで .env をリポジトリにコミットしないよう README 等で注意喚起（.env は絶対に Git にコミットしない旨を .env ヘッダに明記）。

---

注記:
- 本リリースはコードベースから推測して作成した CHANGELOG です。運用上の細かな仕様（ExecutionEngine の内部挙動、BrokerClient の実装、monitoring/system_monitor の詳細など）は該当モジュールの実装に依存します。今後の変更では「Added / Changed / Fixed」区分ごとに差分を記載してください。