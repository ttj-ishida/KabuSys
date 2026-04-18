# Changelog

すべての変更は「Keep a Changelog」のフォーマットに準拠しています。  
このファイルは、コードベース（src/kabusys 配下）の現状から推測して作成した初期の変更履歴です。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回リリース。システム全体のコア機能と CLI / ツール群を実装しました。

### Added

- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境変数管理
  - Settings クラス（kabusys.config）を実装。環境変数から設定値を取得し、型チェック・バリデーションを行う。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。OS 環境変数を保護する仕組みあり。
  - 必須/選択的設定・値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック等）。
  - conveniences: duckdb/sqlite のデフォルトパス、PID / kill フラグ関連の設定プロパティを提供。

- 設定ウィザード / 検証 CLI
  - .env を対話的に作成・更新するウィザード（kabusys.config_setup）。各項目の説明、既存値の取り込み、シークレットマスキング、保存確認を含む。
  - 環境設定と config/*.yaml の事前検証 CLI（kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML の存在・パース確認、live 環境向けの追加ガードを実装。`--strict` オプションで警告も失敗扱いにできる。

- 実行 / 監視ランナースクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を用いる。paper_trading と本番 DB を明確に分離。
    - BrokerClientFactory によるブローカークライアント生成（Mock 支持を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててバックグラウンドスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイルによる制御あり。
    - RiskManager に基本コンフィグ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。初期の available_cash をブローカーから取得して使用。

  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負値／不正値はデフォルトにフォールバック）。
    - 監視用 DB 初期化（monitoring テーブルの初期化）を起動時に行う。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を High に設定する呼び出し（utils.process_priority を使用）。停止フラグ検知でループ終了。

- 監視 / DB 初期化ユーティリティ
  - init_monitoring_db（監視テーブルの冪等な初期化を想定、run 系スクリプトから利用）。

- プロセス優先度・CPU affinity ユーティリティ
  - kabusys.utils.process_priority：Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度（nice/priority class）を設定する `set_process_priority` を実装。アクセス権・未対応 OS の場合は警告を出して安全にスキップする。
  - `set_cpu_affinity(cpu_count)` を実装。指定が None のとき何もしない。許可エラーや未対応環境に対して安全に失敗。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates：BUY シグナルをスコア降順（スコア同点は signal_rank によるタイブレーク）でソートして上位 N を選択。
    - calc_equal_weights：等金額配分（重み = 1/N）。
    - calc_score_weights：スコア正規化配分（総スコアが 0 の場合は等分配にフォールバックして警告）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap：既存保有のセクター別エクスポージャーに基づき、セクター上限（max_sector_pct）を超過しているセクターの新規候補を除外。unknown セクターは除外対象から除く。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes：allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。単元株（lot_size）、stop_loss、risk_pct、max_position_pct、max_utilization、cost_buffer を考慮した計算ロジックと aggregate cap（可用現金超過時のスケーリング）を実装。価格欠損時はスキップ、単元株で丸め。

- リサーチ / ファクター計算
  - kabusys.research.factor_research：DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照してモメンタム、ボラティリティ等のファクターを計算する関数を実装（calc_momentum, calc_volatility 等の骨組み／クエリ実装含む）。データ不足時の None ハンドリング、ウィンドウサイズ定義あり。

- Paper Trading 検証ツール
  - kabusys.tools.paper_verification_report：paper_trading 用 SQLite からシステム稼働率、注文成功率、送信率、レイテンシ（P95）などを集計してレポートを標準出力に出力する CLI を実装。閾値（稼働率 99% など）を定義し PASS/FAIL 判定を行う。DB が存在しない場合のエラーメッセージや日付フィルタオプション（--from, --to, --db）をサポート。

- パッケージエクスポート
  - kabusys.portfolio.__init__ で主要関数を集約して外部公開。

### Changed

- （初回リリースにつき特記する変更履歴は無し）

### Fixed

- （初回リリースにつき特記する修正は無し）

### Removed

- （初回リリースにつき特記する削除は無し）

### Security

- .env ファイルは Git にコミットしない旨を config_setup のヘッダに明記（注意喚起）。

---

注意:
- 上記はソースコードから推測して記載した変更履歴です。実際のリリースノート作成時はコミット履歴・リリース方針に基づいて調整してください。
- 各 CLI は module 実行（python -m kabusys.config_setup 等）で利用可能なことを想定しています。