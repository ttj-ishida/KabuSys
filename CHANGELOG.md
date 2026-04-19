# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

全般:
- 本リポジトリは日本株自動売買システム「KabuSys」の初期実装を含みます。
- バージョン番号はパッケージ定義 (kabusys.__version__) に合わせて 0.1.0 としています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。主要機能とユーティリティ群を実装。

### Added
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が paper_trading の場合は paper_trading 用 DB を使用し、本番 DB と分離。停止フラグファイルの検知で安全に停止するロジックを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイルでループを終了。監視は環境に関わらず本番 sqlite_path を参照。
- 設定・環境管理
  - config.Settings: 環境変数に基づく設定クラスを実装。データベースパス、ログレベル、環境種別（development/paper_trading/live）、paper_trading 固有設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）などをプロパティで提供。値の妥当性チェックを行う。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動的に読み込む仕組みを実装。OS 環境変数を保護するオプション（KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化）。
  - config_setup: 対話式ウィザードで .env ファイルを作成・更新する CLI を追加。シークレットのマスク表示、選択肢、デフォルト値などをサポート。
  - validate_config: .env および config/*.yaml の起動前チェック CLI を追加。必須環境変数チェック、パスの存在確認、YAML パース（PyYAML が存在する場合）の検証、KABUSYS_ENV=live 時のガードなどを実装。--strict オプションを実装。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢な .env パースロジックを実装。
- ロギング/運用ユーティリティ
  - setup_logging: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定するユーティリティを追加。既存ハンドラのクリアによる二重設定防止、LOG_DIR/LOG_LEVEL の解決順をサポート。
  - process_priority: psutil を用いたプロセス優先度設定ユーティリティを追加（Windows/Linux/Mac 対応）。CPU affinity 設定関数も追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合のフォールバック警告あり。
  - portfolio.position_sizing: position size（株数）計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、最大ポジション比率・利用率制限、aggregate cap スケールダウン、cost_buffer を考慮した調整、端数配分アルゴリズムを実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap（既存保有を考慮）、市場レジームに応じた投下比率 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マッピング、未知レジームは警告してフォールバック）。
  - portfolio パッケージのエクスポートを整理して公開 API を提供。
- リサーチ/ファクター計算（初期実装）
  - research.factor_research: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、出来高などを想定）。関数シグネチャおよび定数を定義（実装は継続）。
- 運用ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を計算して PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db、期間フィルタ対応。
- 監視関連
  - monitoring.monitoring_db (参照): 監視用 DB 初期化を行う init_monitoring_db の呼び出しを run_* スクリプトに組み込み（冪等に監視テーブルを確保）。
- パッケージ管理
  - kabusys.__version__ = "0.1.0" を設定。

### Changed
- ログ出力の扱い: 標準エラーではなく標準出力 (stdout) を StreamHandler に使用（cron/task でのリダイレクト想定）。
- .env の読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定時にセット）とし、OS 環境変数を保護する動作を採用。

### Fixed
- run_monitoring のポーリング間隔取得ロジックで不正値（0 以下や非整数）を検出した際にデフォルトへフォールバックして警告を出す安全化を追加（time.sleep に無効値を渡さない）。
- position_sizing と risk_adjustment の価格欠損時のハンドリング強化（価格未取得時にスキップし debug ログを出力）。
- process_priority / set_cpu_affinity でアクセス権限やプラットフォーム差異による例外をキャッチして警告を出し、安全にフォールバックするように修正。

### Security
- .env ファイル生成時にシークレット値をマスクして確認表示する UI を実装（config_setup）。
- .env は絶対に Git にコミットしない旨の注記を .env 生成ヘッダに追加。

### Notes / Known limitations
- research.factor_research の一部実装（calc_momentum 等）は未完（ファイル末尾で未完の記述あり）。今後の実装で DuckDB クエリ／正規化処理を追加予定。
- 一部の TODO コメント（例: position_sizing の銘柄ごとの lot_size サポート、apply_sector_cap の価格フォールバック方法）が残っています。
- run_* スクリプトは内部で sqlite3 と duckdb を直接接続しているため、運用環境ではファイルパスやパーミッションに注意してください。

---

（この CHANGELOG はコードベースの内容から推測して作成したもので、実際のコミット履歴やリリースノートとは差異がある可能性があります。必要に応じて実際の変更箇所や日付を精査の上、更新してください。）