# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

現行バージョン: 0.1.0

## [Unreleased]

- 研究系ファイル（kabusys.research.factor_research）のモメンタム計算関数が途中（実装継続中）
  - calc_momentum の実装が未完（リファクタ／補完予定）。WIP。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成・初期リリース。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する。
    - エンジンはデーモンスレッドで実行し、data/stop_requested.flag による停止検知、実行中 PID 管理（data/execution.pid）をサポート。
    - BrokerClientFactory によるブローカークライアントの抽象化を導入。
    - RiskManager の初期設定（デフォルトの制限値）を組み込んだ。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックする。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - 停止フラグ（data/stop_requested.flag）によるループ終了をサポート。
- 設定管理
  - kabusys.config
    - .env 自動読み込み（.env, .env.local）機能を実装。OS 環境変数は保護・上書き制御を行う。
    - .env パーサを独自実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントルール）。
    - Settings クラスで環境変数をラップ（J-Quants、kabu API、DB パス、監視閾値、環境判定等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 設定関連 CLI
  - kabusys.config_setup
    - 対話式の .env 設定ウィザードを追加。シークレット項目はマスク表示、既存 .env の読み込みと上書きが可能。
    - 書き込み時に .env へヘッダコメントを付与（.git へのコミット注意を明記）。
  - kabusys.validate_config
    - 起動前の静的チェック CLI を追加。必須環境変数、KABUSYS_ENV 値、ファイルパスの親ディレクトリの存在、config/*.yaml の有無（および PyYAML がある場合はパース検証）などを検査。
    - --strict オプションで警告を失敗扱いにするモードを提供。
- ロギングユーティリティ
  - kabusys.utils.logging_setup
    - 統一的なロギング初期化関数 setup_logging を追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定する。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数対応および引数からの上書きに対応。
- プロセス優先度ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level) を追加。Windows / POSIX を吸収して優先度（high/normal/low）を設定。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を設定（利用可能なコアより大きい指定は全コア使用にフォールバック）。
    - 権限不足などの失敗は警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分。全スコア 0 の場合は等配分へフォールバック。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補フィルタリング。unknown セクターは除外しない。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームはフォールバック 1.0）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算。損切り幅・リスク率・単元（lot_size）丸め、position と aggregate のキャップ調整、cost_buffer を考慮した縮小ロジック（スケールダウンと端数再配分）を実装。
  - 上記をまとめたパッケージエクスポート（kabusys.portfolio.__all__）を追加。
- Paper Trading 検証ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用 SQLite（data/paper_trading.db）を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等の指標レポートを生成する CLI を追加。
    - --from/--to/--db オプションで期間・DB を指定可能。
    - デフォルトの合格基準（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を実装し、PASS/FAIL を判定。
    - P95 計算および欠測データの扱い（N/A 表示）を実装。
- 監視 DB 初期化ヘルパー呼び出し
  - 複数の起動スクリプトで init_monitoring_db(sqlite_conn) を呼び出し、監視テーブルが存在することを冪等に保証。

### Changed
- 実行・監視プロセス起動時にプロセス優先度を最初に "high" に設定するように統一。
- run_execution の DB 接続ロジックを KABUSYS_ENV によって paper_trading_DB を切り替える形に変更し、本番 DB とペーパートレード DB を明確に分離。
- ログハンドラの挙動を標準化（既存ハンドラをクリーンに削除してから設定）。

### Fixed
- .env 読み込み時のパーシングにおいて以下をサポート／修正:
  - export KEY=val 形式のサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - インラインコメントの取り扱い（クォートなし・コメントの前にスペースがある場合にコメントと見なすルール）
- MONITOR_POLL_INTERVAL に 0 以下や非整数が設定された場合に time.sleep で ValueError が発生しないよう、無効値はデフォルトにフォールバックするロジックを追加。

### Security
- .env を生成する際に「絶対に Git にコミットしないこと」を明記（config_setup のヘッダ）。

### Documentation / Notes
- 各モジュール内に動作説明・設計方針（PortfolioConstruction.md / StrategyModel.md 参照）や TODO コメントを追加。
- research モジュールは DuckDB 接続を受け取り prices_daily / raw_financials のみを参照する設計（実行時に外部 API を呼ばない安全な設計）。

---

もし特定の変更点（例えばリスク設定のデフォルト値やログ設定の挙動）について詳細な追記が必要であれば、該当箇所の実装を参照のうえ CHANGELOG に追加で記載します。