# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
ソースから推測して初期リリース相当の変更点をまとめています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（後方互換性がある場合）
- Fixed: バグ修正
- Security: セキュリティに関する注意点
- (Breaking Changes は明示的に記載します)

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - __version__ を "0.1.0" に設定。
- 起動スクリプト / ランナーを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止はプロジェクト配下 data/stop_requested.flag ファイルで制御。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用することを明示。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - 実行中の停止は data/stop_requested.flag により検知してエンジン停止を行う。
    - PID ファイル（data/execution.pid）管理に対応。
- 設定管理・ヘルパー
  - config.py
    - .env の自動読み込み機能（.env, .env.local、OS 環境変数優先）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env 行パーシング実装（export 形式、クォート、エスケープ、コメント処理）。
    - 各種設定プロパティ（DB パス、API トークン、閾値、環境判定など）を集約した Settings クラスを提供。
  - config_setup.py
    - 対話式 .env 作成ウィザードを実装（.env ファイル読み書き、シークレットマスク表示、選択肢サポート）。
  - validate_config.py
    - 起動前検証ツールを実装（必須環境変数チェック、KABUSYS_ENV 検証、YAML ファイル存在・パースチェック、live 環境向けの注意喚起など）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対する統一セットアップ関数を実装。
    - コンソール出力は stdout、ファイル出力は日次ローテート（TimedRotatingFileHandler）で 30 日分保持。
    - LOG_DIR/LOG_LEVEL の解決順をサポートし、ディレクトリ作成失敗時はファイル出力をスキップして継続する。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity 設定用の set_cpu_affinity 関数を提供。
- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py
    - position size の計算ロジック（risk_based / equal / score）、単元丸め、aggregate cap のスケーリング、および cost_buffer を考慮した調整を実装。
  - portfolio/__init__.py で各関数を再エクスポート。
- 研究・ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を使ったモメンタム等のファクター計算モジュールの骨格を追加（モジュール設計、定数、calc_momentum 等の雛形）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading の SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95）などのレポートを生成する CLI を実装。
    - 判定基準（閾値）を定義し PASS / FAIL を出力する。
- 監視 DB 初期化ユーティリティ（monitoring_db への参照はランナーで使用）と SystemMonitor の利用を示す呼び出しを追加（該当モジュールは run 系で利用）。
- duckdb / sqlite3 を用いたデータ接続を想定。DuckDB は分析用、SQLite は監視・注文履歴や paper_trading に使用。

### Changed
- なし（本バージョンは初期実装のため「追加」が中心）。

### Fixed
- なし（初期リリース）。

### Security
- .env は生成された注意書きで「絶対に Git にコミットしないこと」を明記。
- validate_config により本番環境（KABUSYS_ENV=live）での設定漏れ（LINE トークン未設定や Kill Switch 設定など）を警告するガードを追加。

### Notes / Important behaviors（破壊的変更に準ずる注意）
- run_monitoring は Monitoring の DB 接続に「環境にかかわらず本番 sqlite_path（settings.sqlite_path）を使用する」設計となっているため、開発環境で監視を分離したい場合は設定を確認してください。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する仕様。
- .env の自動読み込みはデフォルトで有効（プロジェクトルート検出に .git または pyproject.toml を使用）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority と CPU affinity の設定は権限や OS に依存し、設定失敗時は警告ログを出してスキップされます（例: psutil.AccessDenied）。
- logging_setup はログディレクトリ作成に失敗するとファイルハンドラをスキップしてコンソール出力のみ継続します。

もし追加で以下のような情報が必要であれば教えてください:
- 各モジュールの公開 API（関数シグネチャ）の一覧
- run_* スクリプトの起動例（systemd / cron など）
- .env の推奨テンプレート（.env.example 風）