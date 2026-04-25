CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-25
------------------

初回リリース。本リポジトリの基盤機能をまとめて導入します。

### Added
- 基本バージョン情報
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"` を追加。

- 環境設定 / 設定管理
  - `kabusys.config`:
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
    - .env ファイルのパース実装（`export KEY=val`、クォート、インラインコメントの扱い等に対応）。
    - 環境変数の必須チェック用ヘルパー `_require` と `Settings` クラス（多数のプロパティ経由で設定取得）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロードの無効化。
    - Paper Trading 用 DB パス、PAPER_FILL_MODE 検証、環境判定プロパティ（is_live/is_paper/is_dev）などを実装。

- 設定関連 CLI / ウィザード / 検証
  - `kabusys.config_setup`:
    - 対話形式で .env を初期作成・更新するウィザード。
    - 入力のマスク、選択肢、既存値再利用、ファイル書き出し機能を提供。
  - `kabusys.validate_config`:
    - .env と config/*.yaml の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML パース検査（PyYAML があれば実施）、本番用ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の警告）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- 起動スクリプト
  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視用 DB は環境に関わらず本番用 `sqlite_path` を使用。
    - stop フラグ（data/stop_requested.flag）検知で安全にループ停止。
    - DuckDB / SQLite の接続初期化を行う。

  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（Mock 対応想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - プロセス優先度を "high" に上げる処理と、stop フラグ / pid ファイルの扱いを含む。

- 監視・レポートツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成スクリプト。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等の集計と PASS/FAIL 判定。
    - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - 閾値（稼働率/成功率/送信率/P95 レイテンシ）を定数で定義。日付フィルタ（--from/--to）対応。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 (`select_candidates`)、等配分 (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) を提供。
    - スコアが全て 0 の場合は等配分にフォールバックし警告を出力。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限適用 (`apply_sector_cap`)：既存保有のセクターエクスポージャーに基づき新規候補を除外。
    - レジーム乗数算出 (`calc_regime_multiplier`)：regime に応じた投下倍率（bull/neutral/bear）を返す。未知のレジームは 1.0 にフォールバックして警告。
  - `kabusys.portfolio.position_sizing`:
    - ポジションサイズ計算 (`calc_position_sizes`)：risk_based / equal / score に対応。
    - 単元（lot_size）丸め、1 銘柄上限・集計上限 (available_cash) によるスケーリング、cost_buffer（手数料／スリッページ見積）を考慮した保守的見積、残余キャッシュに基づく再配分ロジックなどを実装。

- 研究モジュール
  - `kabusys.research.factor_research`:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針を導入（DuckDB を利用し prices_daily / raw_financials を参照）。
    - モメンタム（mom_1m, mom_3m, mom_6m）、MA200乖離率、ATR/出来高平均等の計算を想定した実装基盤を追加（モジュール冒頭に定数・設計方針を定義）。

- 汎用ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、デフォルト logs/、30日保持）を統一して設定する `setup_logging` を追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`:
    - Windows / POSIX に対応したプロセス優先度設定 (`set_process_priority`) と CPU affinity 固定 (`set_cpu_affinity`) を提供。
    - 権限不足・未実装環境では警告を出して安全にスキップ。

- DB 初期化ユーティリティ（監視用）
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用する呼び出し箇所を run_monitoring/run_execution に追加（監視テーブルの存在保証、冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

Notes / 補足
--------------
- run_execution は paper_trading 環境で本番 DB と完全に分離された SQLite を用いるため、ペーパートレード検証に安全に利用できます。
- .env の自動読み込みはプロジェクトルートの検出に成功した場合のみ行われます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- YAML ファイルの検証は PyYAML の有無に依存します。PyYAML がない場合は内容検証をスキップし警告を出力します。
- 本 CHANGELOG はコードベースから機能を推測して作成しています。実装の詳細や追加の内部モジュール（例: monitoring.system_monitor, execution.* の内部実装等）は本リリースノートには概略として含めています。