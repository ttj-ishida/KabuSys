# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-22

### Added
- 起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。プロセス優先度を上げる処理、スレッドによるエンジン実行、停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理（data/execution.pid）を実装。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。BrokerClientFactory 経由で適切なブローカークライアント（モック等）を生成する想定。
    - RiskManager / Reconciler / OrderManager 等の依存コンポーネント組み立てを行い、初期ポートフォリオ値として broker.get_available_cash() を利用する設定を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）および DuckDB 接続を行い、停止フラグ検知でループを終了する仕組みを実装。Monitoring は環境に関わらず本番 sqlite_path を使用する設計。

- 設定管理と自動ロード
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml）を行い、.env / .env.local を自動読み込み（OS 環境変数優先、.env.local は override）する機能を追加。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パースを強化（export 形式対応、クォート + バックスラッシュのエスケープ、インラインコメント処理）。
    - Settings クラスを導入し、J-Quants や kabu API、DB パス、各種閾値、環境種別（development/paper_trading/live）などをプロパティ経由で取得・検証できるようにした。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject）や paper_sqlite_path 等の紙トレード向け設定を追加。

- 設定支援・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目のマスク表示、選択肢／デフォルト対応、保存の確認機能を備える。
  - validate_config.py
    - 環境変数および config/*.yaml の存在・基本整合性を事前検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV の検証、パスの親ディレクトリチェック、PyYAML がない場合の警告、--strict オプション（警告を FAIL 扱い）を提供。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計してレポートを生成する CLI を追加。期間フィルタ（--from / --to）、DB パス指定オプション、閾値に基づく PASS/FAIL 判定を実装。データ欠損やテーブル未存在時の耐性（例外ハンドリング）あり。

- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順、タイブレークに signal_rank）と上位 N 選定（select_candidates）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全銘柄スコアが 0 の場合は等金額にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用して新規候補を除外する apply_sector_cap を実装（既存ポジションのセクター別時価を計算し max_sector_pct を超えるセクターはブロック。unknown セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知の場合は警告と 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 各配分方式（risk_based / equal / score）に基づいた株数算出ロジックを実装。単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や合計投下上限（max_utilization / available_cash）を考慮。合計コストが available_cash を超える場合はスケールダウンし、残余で端数調整（fractional remainders）を行う。

- ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプト共通のログ設定ユーティリティを追加。標準出力（StreamHandler / stdout）と日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラの重複防止やログディレクトリ作成失敗時のフォールバックを実装。LOG_LEVEL / LOG_DIR の解決順をサポート。
  - utils/process_priority.py
    - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）を設定するユーティリティを追加。Windows と POSIX 系での差分を吸収し、psutil を用いて安全に実行。権限不足や未サポート環境では警告を出してスキップ。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - DuckDB を用いたファクター計算のためのモジュールを追加（モメンタム / ボラティリティ / Value 等を想定）。calc_momentum の定数とドキュメントを導入（実装の続きを想定）。

- パッケージメタ
  - パッケージ初期バージョンを設定: __version__ = "0.1.0"

### Changed
- 監視 DB の利用方針明確化
  - run_monitoring.py は KABUSYS_ENV に依存せず「本番用 sqlite_path」を監視に使用する設計にしていることを明記（監視データと paper_trading データの分離方針を明確化）。

### Fixed
- （初期リリース）各種入力/読み込みの耐性を強化
  - .env 読み込み失敗時に警告を出して続行する（config._load_env_file）。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にコンソールログのみで継続するフォールバックを追加。
  - DB/テーブル未存在時の CLI（paper_verification_report / validate_config）の例外処理を強化し、ユーザーにわかりやすいメッセージを出力するよう改善。

---

注: 上記はコードベースから推測した変更点・機能一覧です。実際のコミット履歴やチケット管理と比較して適宜調整してください。