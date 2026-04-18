# Changelog

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠します。

※ 本ファイルはコードベースから推測して作成しています。実装の意図や細部はソースコードを参照してください。

---

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 実装: 基本的な日本株自動売買システム「KabuSys」の初期機能群を追加。
  - エントリポイント / 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。監視は環境に関係なく本番用 sqlite_path を使用。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録。
  - 設定管理
    - config.py: .env 自動読み込み機能（プロジェクトルートの検出、.env / .env.local の読み込み順）と Settings クラスを提供。多くの環境変数をプロパティで取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値など）。PAPER_FILL_MODE に対する妥当性チェックを実装。
    - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。既存値読み込み／シークレットマスク／デフォルト値の扱いをサポート。
    - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在確認、live 環境向けの安全ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の注意喚起）などの検査を行う。--strict オプションで警告も失敗扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコア合計が0なら等配分へフォールバック）。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリング（残差配分ロジック含む）を実装。各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, cost_buffer 等）に対応。
    - portfolio パッケージのエクスポートを整備。
  - 実行関連コンポーネント（起動スクリプトから使用）
    - ExecutionEngine 組み立て時に OrderRepository, OrderManager, RiskManager, Reconciler を接続する流れを想定（起動時に PID ファイル / stop flag の取り扱いを行う）。
    - Paper Trading 用に broker factory 経由で MockBrokerClient を生成する想定（環境分離）。
  - 監視関連
    - monitoring.monitoring_db の初期化呼び出しを行う（監視テーブルが存在することを保証）。
    - run_monitoring が停止フラグ（data/stop_requested.flag）を検知して正常終了する処理を実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定する。デフォルトの閾値を設定（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）。
  - ユーティリティ
    - utils.logging_setup: 統一的なロギングセットアップ関数を提供。stdout を StreamHandler に、ログファイルは日次ローテーション（TimedRotatingFileHandler）で保存（既定 logs/、30日保持）。既存ハンドラをクリアして二重設定を防止する。
    - utils.process_priority: クロスプラットフォーム（Windows/Linux/macOS等）でプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。psutil ベースで、権限不足や未実装の API を安全にハンドリング。
  - research.factor_research: DuckDB を使ったファクター計算モジュール（モメンタム等）を追加（実装途中の箇所あり）。
  - パッケージ管理
    - kabusys.__version__ = "0.1.0" を設定。

### Changed
- ログ出力設定の仕様を明記:
  - ログレベルの解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - ログディレクトリ解決順: 関数引数 > 環境変数 LOG_DIR > デフォルト "logs/"。
  - stdout を使用する理由（Task Scheduler/cron でのリダイレクト互換）をコメントに明記。

### Fixed
- .env 読み込みの堅牢化:
  - config._parse_env_line で export 形式およびシングル/ダブルクォート内のバックスラッシュエスケープを扱うようにし、インラインコメントの処理ルールを改善。
  - _load_env_file で既存 OS 環境変数を保護する protected 引数を導入（.env.local の上書き時に OS 環境を保持）。

### Deprecated
- なし（初期リリース）。

### Removed
- なし（初期リリース）。

### Security
- なし特記事項。ただし .env の取り扱いに関して config_setup が .env を生成する際に「絶対に Git にコミットしないこと」を明記。

---

補足メモ（実装上の注意／既知の制約）
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（非整数、0 以下など）な場合に警告を出しデフォルト 60 秒にフォールバックする。time.sleep に渡す値の検証を行っているため安全にループを継続する。
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用 SQLite）を使用する旨の実装になっている。paper_trading 環境で監視データを別 DB に隔離したい場合は注意が必要。
- run_execution は settings.is_paper をチェックして paper_sqlite_path を使用する（本番とペーパートレードが DB レベルで完全分離される）。
- process_priority と CPU affinity の設定は権限やプラットフォームに依存するため、失敗した場合は警告を出して続行する安全設計。
- portfolio.position_sizing の aggregate cap スケーリングは lot_size（単元）単位で丸めるため、極端に小さな available_cash の場合は発注株数が 0 になる可能性がある。
- research.factor_research モジュールは途中で切れている箇所があり、完全実装は未完。使用時は注意。

もし CHANGELOG に含めたい追加情報（過去のリリース分、具体的な issue/PR 番号、リリースノートの文章スタイル等）があれば教えてください。必要に応じて追記・修正します。