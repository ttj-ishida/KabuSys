# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

最新リリース: 0.1.0

<!--
参考:
- https://keepachangelog.com/ja/1.0.0/
-->

## [Unreleased]
（現在のリポジトリ状態に対する未リリースの変更点はここに記載します）

## [0.1.0] - 2026-04-17
初回リリース。主に自動売買システム KabuSys のコア機能、運用ユーティリティ、検証ツール、および設定周りの CLI を含みます。

### Added
- コアパッケージ
  - kabusys パッケージ本体を追加。バージョンは 0.1.0。
  - モジュール構成により、strategy / execution / monitoring 等のサブパッケージと連携可能な設計。

- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行ループを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全停止。
    - RiskManager に対するデフォルト設定を実装（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。initial_portfolio_value をブローカーから取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、0 以下は無効扱いでデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視は本番データに対して動作する前提）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt を適切にハンドリング。

- 設定管理・自動読み込み
  - config.py
    - Settings クラスを導入し、環境変数からアプリケーション設定を取得する統一インターフェースを提供。
    - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込む。OS 環境変数を保護（上書き禁止）する仕組みあり。
    - .env パースの強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, kill_flag, CPU/MEM/DISK 閾値 等）を提供。
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック）を実装。
    - paper_fill_mode の検証（instant/partial/never/reject）を導入。

- 設定関連 CLI / ウィザード
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを提供。デフォルト値、選択肢、シークレット入力、保存の確認などをサポート。
    - .env 書き出しテンプレートを提供（Git にコミットしないよう注意を記載）。

  - validate_config.py
    - 起動前チェック CLI を提供。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認、config/*.yaml 存在・パースチェック（PyYAML がない場合は警告）を行う。
    - 本番（live）環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告など）。
    - --strict オプションで警告も失敗扱いにできる。

- 運用ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティ（set_process_priority）。
    - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を吸収して同一 API を提供。
    - set_cpu_affinity により最初の N コアにプロセスをピン留め可能。権限不足等の例外はログでスキップ。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（select_candidates）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等配分にフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは適用除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear にマップ、未知レジームは警告して 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）超過時のスケーリングロジック（端数分配アルゴリズム含む）を実装。
    - cost_buffer による保守的な手数料・スリッページ見積もりを考慮。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いてモメンタム・ボラティリティ等のファクターを計算する関数群（例: calc_momentum, calc_volatility）。
    - 長期移動平均、ATR、出来高指標などを計算。データ不足時は None を返す設計。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を集計して検証レポートを出力する CLI。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - デフォルトの合格基準を導入（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。判定は PASS/FAIL で表示。
    - 日付フィルタ (--from / --to) および --db オプションをサポート。

- DB・分析基盤
  - duckdb の統合: 複数モジュールで DuckDB 接続を受け取り分析用クエリを実行。
  - SQLite（sqlite3）を監視・履歴用に利用。monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）を呼び出してテーブル存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- run_monitoring は環境にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データとペーパートレードの分離が厳密に必要な場合は run_execution 側で paper_sqlite_path を利用する設計です。
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
- プロセス優先度や CPU affinity 設定は権限不足やプラットフォーム非対応時に警告を出してスキップする堅牢な実装になっています。
- position_sizing のスケーリングは lot_size（単元）単位での丸めや、残余キャッシュを利用した再配分アルゴリズムを実装しています。

---

今後のリリース案（例）
- 0.2.0: 実トレード接続の強化、戦略モジュールとの統合、詳細な監視アラート（LINE 通知）機能追加
- 0.1.x: バグ修正、パフォーマンス改善、単体テスト追加

もし特定のコミットや日付ベースの詳細な履歴が必要であれば、提供していただければより細かい CHANGELOG を作成します。