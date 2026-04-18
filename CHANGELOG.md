# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

初期リリース。本リリースでは、日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、および Paper Trading 検証レポート生成機能を実装しています。

### Added
- 全体
  - パッケージのバージョンを `__version__ = "0.1.0"` として公開。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアントのファクトリ使用、OrderManager、RiskManager、Reconciler の組み立て、別スレッドで Engine を実行する制御ループ、停止フラグ（data/stop_requested.flag）での安全停止を実装。paper_trading 環境時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で終了。Monitoring 用 DB は環境にかかわらず本番 sqlite_path を使用。
- 設定管理・検証
  - config.py: .env 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml 基準）、柔軟な .env パース（コメント、export プレフィックス、シングル/ダブルクォートやエスケープ対応）、Settings クラス（環境変数ラッパ）を実装。環境判定（development/paper_trading/live）、各種パスや閾値の取得ロジックを提供。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット扱い項目のマスク表示、既存 .env 読み込み、保存前の確認プロンプトを備える。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在および（PyYAML があれば）パース検証、本番環境向けガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の注意）を実装。--strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに対する統一的セットアップを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート・30日保持）を設定。LOG_DIR/LOG_LEVEL 環境変数や引数で上書き可。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度設定（Windows の priority class / POSIX の nice 値を吸収）と CPU affinity 設定ユーティリティを追加。対応 OS を判定して安全にフォールバックし、権限不足等で失敗した場合は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み計算。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知のレジームは 1.0 でフォールバック、警告ログ）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 等配分・スコア配分・リスクベースの株数決定ロジックを実装。lot_size（単元）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ概算）考慮、残差に基づく再配分アルゴリズムを実装。
- モニタリング / データ
  - monitoring 関連（init_monitoring_db, SystemMonitor の利用箇所をスクリプトから呼出し）を起動フローに組み込んで監視テーブルの初期化を保証。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を計算・表示。閾値を定義し PASS/FAIL を判定。DB のテーブル欠如やデータ不足は適切にハンドリング（OperationalError 捕捉）して N/A 表示。
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの枠組みを実装（モメンタム、MA200、ATR、ボリューム等の計算方針と定数を定義。関数シグネチャと docstring を準備）。

### Changed
- 設定読み込みの優先度を明確化: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される（上書き抑止）。
- logging_setup: コンソール出力を stdout に統一（stderr ではなく stdout）。既存ハンドラは一度 flush/close してから削除し再構成する実装で二重登録を防止。

### Fixed / Robustness improvements
- MONITOR_POLL_INTERVAL の不正値を検出してデフォルト（60秒）にフォールバックするように実装（警告ログを出力）。
- .env パーサー:
  - export プレフィックス対応、シングル/ダブルクォート文字列のエスケープ処理、インラインコメント処理などをサポートして堅牢化。
- process_priority / set_cpu_affinity:
  - 未知の OS や権限不足時に安全にスキップし、詳細な警告をログ出力するように修正。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合は警告を出して等金額配分にフォールバック。
- position_sizing: 価格欠損・0 以下価格を検出してスキップする安全対策を実装。aggregate cap のスケーリング時に lot_size 単位での再配分ロジックを導入し、残余キャッシュで端数を補填する実装により再現性を高めた。
- paper_verification_report: テーブルやカラムが存在しない場合に sqlite3.OperationalError を捕捉してレポート生成を継続（N/A 表示）。

### Security
- .env の取り扱いに関する注意を config_setup の出力に明記（.env を絶対に Git にコミットしない旨の注記を追加）。

### Documentation / CLI UX
- config_setup による対話式ウィザードと validate_config による事前検証を提供することで、起動前に設定ミスを検出しやすくした。
- run_execution / run_monitoring は起動時に環境（KABUSYS_ENV）をログに出力し、停止フラグによる安全停止をサポート。

### Removed
- なし（初期リリース）。

---

注:
- 本 CHANGELOG はリポジトリ内のソースコードから機能・ふるまいを推測して作成しています。実際のリリースノート作成時はコミットや PR の履歴、リリース目的に合わせて適宜調整してください。